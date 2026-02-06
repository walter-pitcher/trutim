"""
Trutim REST API Views
"""
import os
import uuid
from collections import defaultdict
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.files.storage import default_storage
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from .models import Room, Message, CallSession
from .serializers import UserSerializer, RoomSerializer, RoomDetailSerializer, RoomCreateSerializer, MessageSerializer, CallSessionSerializer

User = get_user_model()


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
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


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
        if self.action == 'retrieve':
            return RoomDetailSerializer
        return RoomSerializer

    def get_queryset(self):
        return Room.objects.filter(members=self.request.user).distinct()

    def perform_create(self, serializer):
        room = serializer.save(created_by=self.request.user)
        room.members.add(self.request.user)

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


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer

    def get_queryset(self):
        room_id = self.request.query_params.get('room')
        if room_id:
            return Message.objects.filter(room_id=room_id, room__members=self.request.user)
        return Message.objects.none()

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
        return Response(MessageSerializer(msg).data)
