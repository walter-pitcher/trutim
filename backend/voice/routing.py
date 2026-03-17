"""
WebSocket URL routing for Voice Control.
"""
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/voice/(?P<room_id>\d+)/$', consumers.VoiceControlConsumer.as_asgi()),
    re_path(r'ws/voice/$', consumers.VoiceControlConsumer.as_asgi()),
]
