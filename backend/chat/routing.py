"""
WebSocket URL routing for Trutim
"""
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'^/?ws/presence/?$', consumers.PresenceConsumer.as_asgi()),
    re_path(r'^/?ws/chat/(?P<room_id>\d+)/?$', consumers.ChatConsumer.as_asgi()),
    re_path(r'^/?ws/call/(?P<room_id>\d+)/?$', consumers.CallConsumer.as_asgi()),
]
