from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Room, Message, CallSession


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'title', 'online', 'last_seen']


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_by', 'created_at', 'is_direct']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['room', 'sender', 'content', 'created_at']


@admin.register(CallSession)
class CallSessionAdmin(admin.ModelAdmin):
    list_display = ['room', 'initiator', 'started_at', 'is_screen_share']
