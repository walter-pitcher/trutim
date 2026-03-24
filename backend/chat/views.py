"""
Trutim REST API Views
"""
import os
import uuid
import json
import urllib.parse
import urllib.request
from urllib.error import HTTPError, URLError
from typing import Optional
from collections import defaultdict
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import get_object_or_404
from django.core.files.storage import default_storage
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import Room, Message, MessageRead, CallSession, Channel
from .serializers import UserSerializer, RoomSerializer, RoomDetailSerializer, RoomCreateSerializer, MessageSerializer, CallSessionSerializer

User = get_user_model()


def _generate_unique_username(base_username: str) -> str:
    base = (base_username or 'user').strip().replace(' ', '').lower()
    if not base:
        base = 'user'
    candidate = base[:150]
    suffix = 1
    while User.objects.filter(username=candidate).exists():
        suffix_str = str(suffix)
        candidate = f"{base[:150 - len(suffix_str)]}{suffix_str}"
        suffix += 1
    return candidate


def _auto_join_company_rooms(user):
    # Auto-join the new user to existing company rooms or create a default one.
    company_rooms = Room.objects.filter(is_direct=False)
    if not company_rooms.exists():
        # Bootstrap a default company room for new installs so the sidebar isn't empty.
        room = Room.objects.create(
            name='Trutim HQ',
            description='Default company room for new members',
            created_by=user,
        )
        room.members.add(user)
        Channel.objects.get_or_create(
            room=room,
            name='general',
            defaults={
                'description': 'General discussion',
                'is_default': True,
                'created_by': user,
            },
        )
    else:
        # Add the new user as a member of all existing company rooms.
        for room in company_rooms:
            room.members.add(user)


def _jwt_auth_response_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
        'user': UserSerializer(user).data,
    }


def _http_post_form(url: str, payload: dict, headers: Optional[dict] = None) -> dict:
    body = urllib.parse.urlencode(payload).encode('utf-8')
    req_headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, data=body, headers=req_headers, method='POST')
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.loads(response.read().decode('utf-8'))


def _http_get_json(url: str, headers: Optional[dict] = None) -> dict:
    req = urllib.request.Request(url, headers=headers or {}, method='GET')
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.loads(response.read().decode('utf-8'))


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = UserSerializer(self.user).data
        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        title = request.data.get('title', '')

        if not username or not password:
            return Response({'error': 'Username and password required'}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return Response({'error': 'Username already exists'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(
            username=username, email=email, password=password,
            first_name=first_name, last_name=last_name, title=title
        )
        _auto_join_company_rooms(user)

        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class OAuthLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, provider):
        provider = (provider or '').lower()
        code = request.data.get('code')
        redirect_uri = request.data.get('redirect_uri')

        if not code or not redirect_uri:
            return Response(
                {'error': 'code and redirect_uri are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            if provider == 'google':
                identity = self._exchange_google_code(code, redirect_uri)
            elif provider == 'github':
                identity = self._exchange_github_code(code, redirect_uri)
            else:
                return Response({'error': 'Unsupported provider'}, status=status.HTTP_400_BAD_REQUEST)
        except (HTTPError, URLError, TimeoutError):
            return Response(
                {'error': f'{provider.capitalize()} OAuth request failed'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        email = identity.get('email', '').strip().lower()
        first_name = identity.get('first_name', '').strip()
        last_name = identity.get('last_name', '').strip()
        preferred_username = identity.get('username', '').strip()

        user = None
        created = False
        if email:
            user = User.objects.filter(email__iexact=email).first()

        if user is None and preferred_username:
            # Only match by username for existing OAuth-only accounts to avoid
            # accidental takeover of password-based users with the same username.
            username_match = User.objects.filter(username=preferred_username).first()
            if username_match and not username_match.has_usable_password():
                user = username_match

        if user is None:
            username_base = preferred_username or (email.split('@')[0] if email else provider)
            username = _generate_unique_username(username_base)
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
            )
            user.set_unusable_password()
            user.save(update_fields=['password'])
            created = True

        # Backfill profile info if the account existed without these fields.
        updates = []
        if email and not user.email:
            user.email = email
            updates.append('email')
        if first_name and not user.first_name:
            user.first_name = first_name
            updates.append('first_name')
        if last_name and not user.last_name:
            user.last_name = last_name
            updates.append('last_name')
        if updates:
            user.save(update_fields=updates)

        if created:
            _auto_join_company_rooms(user)

        return Response(_jwt_auth_response_for_user(user), status=status.HTTP_200_OK)

    def _exchange_google_code(self, code, redirect_uri):
        client_id = os.environ.get('GOOGLE_OAUTH_CLIENT_ID')
        client_secret = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET')
        if not client_id or not client_secret:
            raise ValueError('Google OAuth is not configured')

        token_data = _http_post_form(
            'https://oauth2.googleapis.com/token',
            {
                'client_id': client_id,
                'client_secret': client_secret,
                'code': code,
                'redirect_uri': redirect_uri,
                'grant_type': 'authorization_code',
            },
        )

        id_token = token_data.get('id_token')
        if not id_token:
            raise ValueError('Missing Google id_token')

        token_info_url = f"https://oauth2.googleapis.com/tokeninfo?id_token={urllib.parse.quote(id_token)}"
        info = _http_get_json(token_info_url)

        if info.get('aud') != client_id:
            raise ValueError('Google token audience mismatch')

        return {
            'email': info.get('email', ''),
            'first_name': info.get('given_name', ''),
            'last_name': info.get('family_name', ''),
            'username': info.get('email', '').split('@')[0] if info.get('email') else '',
        }

    def _exchange_github_code(self, code, redirect_uri):
        client_id = os.environ.get('GITHUB_OAUTH_CLIENT_ID')
        client_secret = os.environ.get('GITHUB_OAUTH_CLIENT_SECRET')
        if not client_id or not client_secret:
            raise ValueError('GitHub OAuth is not configured')

        token_data = _http_post_form(
            'https://github.com/login/oauth/access_token',
            {
                'client_id': client_id,
                'client_secret': client_secret,
                'code': code,
                'redirect_uri': redirect_uri,
            },
            headers={'Accept': 'application/json'},
        )
        access_token = token_data.get('access_token')
        if not access_token:
            raise ValueError('Failed to obtain GitHub access token')

        auth_headers = {
            'Accept': 'application/vnd.github+json',
            'Authorization': f'Bearer {access_token}',
            'User-Agent': 'trutim-oauth',
        }
        profile = _http_get_json('https://api.github.com/user', headers=auth_headers)
        emails = _http_get_json('https://api.github.com/user/emails', headers=auth_headers)

        selected_email = ''
        if isinstance(emails, list):
            verified_primary = next((e for e in emails if e.get('verified') and e.get('primary')), None)
            verified_any = next((e for e in emails if e.get('verified')), None)
            selected = verified_primary or verified_any
            if selected:
                selected_email = selected.get('email') or ''

        full_name = (profile.get('name') or '').strip()
        parts = full_name.split(' ', 1) if full_name else ['', '']
        first_name = parts[0] if parts[0] else ''
        last_name = parts[1] if len(parts) > 1 else ''

        return {
            'email': selected_email or (profile.get('email') or ''),
            'first_name': first_name,
            'last_name': last_name,
            'username': profile.get('login', ''),
        }


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_queryset(self):
        return User.objects.exclude(id=self.request.user.id)

    @action(detail=False, methods=['get', 'patch'])
    def me(self, request):
        if request.method == 'PATCH':
            serializer = UserSerializer(
                request.user, data=request.data, partial=True, context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        return Response(UserSerializer(request.user, context={'request': request}).data)

    @action(detail=False, methods=['get'], url_path='location-stats')
    def location_stats(self, request):
        """Aggregated user counts by geographic area for the world map."""
        users_with_location = User.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False
        )
        buckets = defaultdict(int)
        for u in users_with_location:
            lat = float(u.latitude)
            lng = float(u.longitude)
            key = (round(lat, 2), round(lng, 2))
            buckets[key] += 1
        data = [
            {'lat': lat, 'lng': lng, 'count': count}
            for (lat, lng), count in buckets.items()
        ]
        return Response({'regions': data, 'total': sum(buckets.values())})


class RoomViewSet(viewsets.ModelViewSet):
    serializer_class = RoomSerializer

    def get_serializer_class(self):
        if self.action == 'create':
            return RoomCreateSerializer
        if self.action in ('update', 'partial_update'):
            return RoomCreateSerializer
        if self.action == 'retrieve':
            return RoomDetailSerializer
        return RoomSerializer

    def get_queryset(self):
        return Room.objects.filter(members=self.request.user).distinct()

    def perform_create(self, serializer):
        room = serializer.save(created_by=self.request.user)
        room.members.add(self.request.user)
        # Ensure each company room starts with a default "#general" channel.
        if not room.is_direct:
            Channel.objects.get_or_create(
                room=room,
                name='general',
                defaults={
                    'description': 'General discussion',
                    'is_default': True,
                    'created_by': self.request.user,
                },
            )

    def update(self, request, *args, **kwargs):
        """Only allow company (non-direct) room updates by the owner."""
        instance = self.get_object()
        if not instance.is_direct and instance.created_by_id != request.user.id:
            return Response({'detail': 'Only the company owner can edit.'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        """Only allow company (non-direct) room updates by the owner."""
        instance = self.get_object()
        if not instance.is_direct and instance.created_by_id != request.user.id:
            return Response({'detail': 'Only the company owner can edit.'}, status=status.HTTP_403_FORBIDDEN)
        return super().partial_update(request, *args, **kwargs)

    @action(detail=False, methods=['post'])
    def dm(self, request):
        """Get or create a direct message room with another user."""
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'error': 'user_id required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            other = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        if other.id == request.user.id:
            return Response({'error': 'Cannot create DM with yourself'}, status=status.HTTP_400_BAD_REQUEST)
        room = Room.objects.filter(
            is_direct=True,
            members=request.user
        ).filter(members=other).first()
        if not room:
            room = Room.objects.create(
                name=f'{request.user.username} & {other.username}',
                is_direct=True,
                created_by=request.user
            )
            room.members.add(request.user, other)
        return Response(RoomSerializer(room).data)

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        room = self.get_object()
        room.members.add(request.user)
        return Response({'status': 'joined'})

    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        room = self.get_object()
        room.members.remove(request.user)
        return Response({'status': 'left'})

    @action(detail=True, methods=['post'], url_path='invite')
    def invite(self, request, pk=None):
        """
        Invite one or more users into a room (company or group).
        Body: { "user_ids": [1, 2, 3] }
        """
        room = self.get_object()
        if room.is_direct:
            return Response({'detail': 'Cannot invite users to a direct message room.'}, status=status.HTTP_400_BAD_REQUEST)

        user_ids = request.data.get('user_ids', [])
        if not isinstance(user_ids, list) or not user_ids:
            return Response({'detail': 'user_ids must be a non-empty list.'}, status=status.HTTP_400_BAD_REQUEST)

        valid_ids = [uid for uid in user_ids if isinstance(uid, int) or (isinstance(uid, str) and uid.isdigit())]
        if not valid_ids:
            return Response({'detail': 'No valid user ids provided.'}, status=status.HTTP_400_BAD_REQUEST)

        # Normalize to ints
        valid_ids = [int(uid) for uid in valid_ids if int(uid) != request.user.id]
        if not valid_ids:
            return Response({'detail': 'No users to invite.'}, status=status.HTTP_400_BAD_REQUEST)

        added = []
        for u in User.objects.filter(id__in=valid_ids).exclude(id__in=room.members.values_list('id', flat=True)):
            room.members.add(u)
            added.append(u.id)

        serializer = RoomDetailSerializer(room, context={'request': request})
        return Response({'added': added, 'room': serializer.data})

    @action(detail=True, methods=['get', 'post'], url_path='channels')
    def channels(self, request, pk=None):
        """
        List or create channels within a company room.

        GET: return all channels for this room. If none exist for a non-direct room,
        automatically create a default "#general" channel.
        POST: create a new channel: { "name": "...", "description": "..." }.
        """
        room = self.get_object()
        if room.is_direct:
            return Response({'detail': 'Channels are only available for company rooms.'}, status=status.HTTP_400_BAD_REQUEST)

        if request.method == 'GET':
            # Auto-bootstrap a default channel if the company has none.
            if not room.channels.exists():
                Channel.objects.create(
                    room=room,
                    name='general',
                    description='General discussion',
                    is_default=True,
                    created_by=request.user,
                )
            channels = room.channels.all().order_by('created_at')
            data = [
                {
                    'id': ch.id,
                    'name': ch.name,
                    'description': ch.description,
                    'is_default': ch.is_default,
                }
                for ch in channels
            ]
            return Response(data)

        # POST – create a new channel
        name = (request.data.get('name') or '').strip()
        description = (request.data.get('description') or '').strip()
        if not name:
            return Response({'error': 'Channel name is required'}, status=status.HTTP_400_BAD_REQUEST)
        if room.channels.filter(name__iexact=name).exists():
            return Response({'error': 'Channel with this name already exists'}, status=status.HTTP_400_BAD_REQUEST)
        ch = Channel.objects.create(
            room=room,
            name=name,
            description=description,
            created_by=request.user,
        )
        return Response(
            {
                'id': ch.id,
                'name': ch.name,
                'description': ch.description,
                'is_default': ch.is_default,
            },
            status=status.HTTP_201_CREATED,
        )


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer

    def get_queryset(self):
        """
        For list views, optionally filter by ?room=<id> and ?channel=<id>.
        For detail / actions (e.g. react), allow lookup by pk as long as the
        current user is a member of the room.
        """
        base_qs = Message.objects.filter(room__members=self.request.user)
        room_id = self.request.query_params.get('room')
        channel_id = self.request.query_params.get('channel')
        if room_id:
            base_qs = base_qs.filter(room_id=room_id)
        if channel_id:
            base_qs = base_qs.filter(channel_id=channel_id)
        return base_qs

    def get_object(self):
        """
        Ensure that detail routes like /messages/<id>/react/ always look up the
        message by primary key within rooms the current user is a member of,
        regardless of any missing ?room=<id> filter in the query params.
        This avoids 404s for actions such as `react` that operate on an
        individual message.
        """
        lookup_value = self.kwargs.get(self.lookup_field or 'pk')
        return get_object_or_404(
            Message,
            pk=lookup_value,
            room__members=self.request.user,
        )

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)

    @action(detail=False, methods=['post'], url_path='upload')
    def upload(self, request):
        """Upload a file for use in messages. Returns the public URL."""
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
        ext = os.path.splitext(file.name)[1] or '.bin'
        path = default_storage.save(f'message_uploads/{uuid.uuid4().hex}{ext}', file)
        url = default_storage.url(path)
        if url.startswith('/'):
            url = request.build_absolute_uri(url)
        return Response({'url': url, 'filename': file.name})

    @action(detail=True, methods=['post'])
    def react(self, request, pk=None):
        msg = self.get_object()
        emoji = request.data.get('emoji')
        if not emoji:
            return Response({'error': 'Emoji required'}, status=status.HTTP_400_BAD_REQUEST)
        reactions = msg.reactions or {}
        user_id = str(request.user.id)
        if emoji not in reactions:
            reactions[emoji] = []
        if user_id in reactions[emoji]:
            reactions[emoji].remove(user_id)
        else:
            reactions[emoji].append(user_id)
        if not reactions[emoji]:
            del reactions[emoji]
        msg.reactions = reactions
        msg.save()
        serialized = MessageSerializer(msg, context={'request': request}).data

        # Broadcast reaction updates to all WebSocket clients in this room.
        try:
            channel_layer = get_channel_layer()
            if channel_layer is not None:
                async_to_sync(channel_layer.group_send)(
                    f'chat_{msg.room_id}',
                    {
                        'type': 'chat_message_reacted',
                        'message': serialized,
                    },
                )
        except Exception:
            # WebSocket broadcast failures should not break the HTTP request.
            pass

        return Response(serialized)

    @action(detail=False, methods=['post'], url_path='mark-read')
    def mark_read(self, request):
        """Mark messages as read by the current user. Body: { message_ids: [1, 2, 3] }"""
        message_ids = request.data.get('message_ids', [])
        if not message_ids:
            return Response({'marked': []})
        room_id = request.data.get('room_id')
        if not room_id:
            return Response({'error': 'room_id required'}, status=status.HTTP_400_BAD_REQUEST)
        if not Room.objects.filter(id=room_id, members=request.user).exists():
            return Response({'error': 'Not a member of this room'}, status=status.HTTP_403_FORBIDDEN)
        created = []
        for msg in Message.objects.filter(id__in=message_ids, room_id=room_id).exclude(sender=request.user):
            _, created_flag = MessageRead.objects.get_or_create(
                message=msg, user=request.user, defaults={}
            )
            if created_flag:
                created.append(msg.id)
        return Response({'marked': created})
