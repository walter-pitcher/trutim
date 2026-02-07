"""
Trutim API Serializers
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Room, Message, MessageRead, CallSession

User = get_user_model()

# Avatar constraints
AVATAR_MAX_SIZE = 2 * 1024 * 1024  # 2MB
AVATAR_ALLOWED_TYPES = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}


# Resume constraints
RESUME_MAX_SIZE = 5 * 1024 * 1024  # 5MB
RESUME_ALLOWED_TYPES = {'application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'}


class UserSerializer(serializers.ModelSerializer):
    avatar = serializers.ImageField(required=False, allow_null=True)
    resume = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'title', 'avatar', 'online', 'last_seen',
                  'latitude', 'longitude', 'address',
                  'github', 'facebook', 'twitter', 'instagram', 'youtube',
                  'gmail', 'telegram', 'discord', 'whatsapp', 'resume']
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

    def validate_resume(self, value):
        if value is None:
            return value
        if value.size > RESUME_MAX_SIZE:
            raise serializers.ValidationError('Resume must be under 5MB.')
        if value.content_type not in RESUME_ALLOWED_TYPES:
            raise serializers.ValidationError(
                'Invalid file type. Use PDF or Word document.'
            )
        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Return relative avatar URL so it works through Vite proxy
        if data.get('avatar') and isinstance(data['avatar'], str) and data['avatar'].startswith('http'):
            data['avatar'] = f"/media/{instance.avatar.name}"
        # Return relative resume URL
        if data.get('resume') and isinstance(data['resume'], str) and data['resume'].startswith('http'):
            data['resume'] = f"/media/{instance.resume.name}"
        return data


class UserMinimalSerializer(serializers.ModelSerializer):
    avatar = serializers.ImageField(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'title', 'avatar', 'online']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data.get('avatar') and isinstance(data['avatar'], str) and data['avatar'].startswith('http'):
            data['avatar'] = f"/media/{instance.avatar.name}"
        return data


class RoomCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating rooms - accepts name, description, and optional avatar."""
    avatar = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Room
        fields = ['id', 'name', 'description', 'avatar']
        read_only_fields = ['id']
        extra_kwargs = {'description': {'required': False, 'allow_blank': True}}

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


class RoomSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    dm_user = serializers.SerializerMethodField()
    created_by = UserMinimalSerializer(read_only=True)

    class Meta:
        model = Room
        fields = ['id', 'name', 'description', 'avatar', 'created_by', 'created_at', 'is_direct', 'member_count', 'last_message', 'dm_user']
        read_only_fields = ['created_by', 'created_at']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data.get('avatar') and isinstance(data['avatar'], str) and data['avatar'].startswith('http'):
            data['avatar'] = f"/media/{instance.avatar.name}"
        return data

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


class RoomDetailSerializer(RoomSerializer):
    """Room serializer with members list for detail view."""
    members = UserMinimalSerializer(many=True, read_only=True)

    class Meta(RoomSerializer.Meta):
        fields = RoomSerializer.Meta.fields + ['members']


class MessageSerializer(serializers.ModelSerializer):
    sender = UserMinimalSerializer(read_only=True)
    read_by = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['id', 'room', 'sender', 'parent', 'content', 'created_at', 'edited_at', 'reactions', 'read_by']

    def get_read_by(self, obj):
        """List of user IDs who have read this message."""
        return list(obj.reads.values_list('user_id', flat=True))


class CallSessionSerializer(serializers.ModelSerializer):
    initiator = UserMinimalSerializer(read_only=True)

    class Meta:
        model = CallSession
        fields = ['id', 'room', 'initiator', 'participants', 'started_at', 'ended_at', 'is_screen_share']
