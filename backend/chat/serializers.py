"""
Trutim API Serializers
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Room, Message, CallSession

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'title', 'online', 'last_seen']
        read_only_fields = ['id', 'online', 'last_seen']


class UserMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'title', 'online']


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

    class Meta:
        model = Room
        fields = ['id', 'name', 'description', 'created_by', 'created_at', 'is_direct', 'member_count', 'last_message']
        read_only_fields = ['created_by', 'created_at']

    def get_member_count(self, obj):
        return obj.members.count()

    def get_last_message(self, obj):
        last = obj.messages.order_by('-created_at').first()
        if last:
            return {'content': last.content[:50], 'sender': last.sender.username, 'created_at': last.created_at}
        return None


class MessageSerializer(serializers.ModelSerializer):
    sender = UserMinimalSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'room', 'sender', 'content', 'created_at', 'edited_at', 'reactions']


class CallSessionSerializer(serializers.ModelSerializer):
    initiator = UserMinimalSerializer(read_only=True)

    class Meta:
        model = CallSession
        fields = ['id', 'room', 'initiator', 'participants', 'started_at', 'ended_at', 'is_screen_share']
