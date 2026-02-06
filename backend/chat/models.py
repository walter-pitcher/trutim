"""
Trutim Chat Models - Users, Rooms, Messages
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Extended user model for engineers and developers."""
    title = models.CharField(max_length=100, blank=True)  # e.g. "Senior Engineer"
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(auto_now=True)
    # Location: exact coordinates + human-readable address
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    address = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = 'trutim_users'


class Room(models.Model):
    """Chat room / collaboration space."""
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_rooms')
    created_at = models.DateTimeField(auto_now_add=True)
    members = models.ManyToManyField(User, related_name='rooms', blank=True)
    is_direct = models.BooleanField(default=False)  # 1-on-1 chat

    class Meta:
        db_table = 'trutim_rooms'
        ordering = ['-created_at']


class Message(models.Model):
    """Chat message with emoji support and reply threading."""
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    # Reactions/emojis stored as JSON: {"👍": ["user1_id"], "❤️": ["user2_id"]}
    reactions = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'trutim_messages'
        ordering = ['created_at']


class CallSession(models.Model):
    """Video call / screen share session."""
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='call_sessions')
    initiator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='initiated_calls')
    participants = models.ManyToManyField(User, related_name='active_calls', blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    is_screen_share = models.BooleanField(default=False)

    class Meta:
        db_table = 'trutim_call_sessions'
