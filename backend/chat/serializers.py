"""
Trutim API Serializers
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Room, Message, CallSession

User = get_user_model()

# Avatar constraints
AVATAR_MAX_SIZE = 2 * 1024 * 1024  # 2MB
AVATAR_ALLOWED_TYPES = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}


class UserSerializer(serializers.ModelSerializer):
    avatar = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'title', 'avatar', 'online', 'last_seen',
                  'latitude', 'longitude', 'address']
        read_only_fields = ['id', 'online', 'last_seen']

    def validate_avatar(self, value):
        if value is None:
            return value
        if value.size > AVATAR_MAX_SIZE:
            raise serializers.ValidationError('Image must be under 2MB.')
        if value.content_type not in AVATAR_ALLOWED_TYPES:
            raise serializers.ValidationError(
                'Invalid image type. Use JPEG, PNG, GIF, or WebP.'
            )
        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Return relative avatar URL so it works through Vite proxy
        if data.get('avatar') and isinstance(data['avatar'], str) and data['avatar'].startswith('http'):
            data['avatar'] = f"/media/{instance.avatar.name}"
        return data


class UserMinimalSerializer(serializers.ModelSerializer):
    avatar = serializers.ImageField(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'title', 'avatar', 'online']


class RoomCreateSerializer(serializers.ModelSerializer):
    """Minimal serializer for creating rooms - only accepts name and description."""
    class Meta:
        model = Room
        fields = ['id', 'name', 'description']
        read_only_fields = ['id']
        extra_kwargs = {'description': {'required': False, 'allow_blank': True}}


class RoomSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    dm_user = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = ['id', 'name', 'description', 'created_by', 'created_at', 'is_direct', 'member_count', 'last_message', 'dm_user']
        read_only_fields = ['created_by', 'created_at']

    def get_member_count(self, obj):
        return obj.members.count()

    def get_dm_user(self, obj):
        """For DM rooms, return the other user (not the current user)."""
        if not obj.is_direct:
            return None
        request = self.context.get('request')
        if not request or not request.user:
            return None
        other = obj.members.exclude(id=request.user.id).first()
        if other:
            return {'id': other.id, 'username': other.username}
        return None

    def get_last_message(self, obj):
        last = obj.messages.order_by('-created_at').first()
        if last:
            return {'content': last.content[:50], 'sender': last.sender.username, 'created_at': last.created_at}
        return None


class MessageSerializer(serializers.ModelSerializer):
    sender = UserMinimalSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'room', 'sender', 'parent', 'content', 'created_at', 'edited_at', 'reactions']


class CallSessionSerializer(serializers.ModelSerializer):
    initiator = UserMinimalSerializer(read_only=True)

    class Meta:
        model = CallSession
        fields = ['id', 'room', 'initiator', 'participants', 'started_at', 'ended_at', 'is_screen_share']
