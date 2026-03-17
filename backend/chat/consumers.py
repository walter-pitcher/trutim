"""
Trutim WebSocket Consumers - Live Chat, Presence & WebRTC Signaling
"""
import json
from django.utils import timezone
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

User = get_user_model()

PRESENCE_GROUP = 'presence'


class PresenceConsumer(AsyncWebsocketConsumer):
    """Global presence WebSocket - tracks user status (active/idle/offline) across the app."""

    async def connect(self):
        self.user = self.scope.get('user')
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        await self.channel_layer.group_add(PRESENCE_GROUP, self.channel_name)
        await self.accept()

        status = 'active'  # Default when connecting (user is in app)
        await self.update_user_presence(online=True, status=status)
        await self.channel_layer.group_send(
            PRESENCE_GROUP,
            {'type': 'presence_update', 'user_id': self.user.id, 'status': status, 'online': True}
        )
        # Send current presence snapshot to the new user
        all_presence = await self.get_all_presence()
        await self.send(text_data=json.dumps({'type': 'presence_snapshot', 'presence': all_presence}))

    async def disconnect(self, close_code):
        if hasattr(self, 'user') and self.user and self.user.is_authenticated:
            await self.update_user_presence(online=False, status='deactive')
            await self.channel_layer.group_send(
                PRESENCE_GROUP,
                {'type': 'presence_update', 'user_id': self.user.id, 'status': 'deactive', 'online': False}
            )
        if hasattr(self, 'channel_name'):
            await self.channel_layer.group_discard(PRESENCE_GROUP, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            if data.get('type') == 'status':
                status = data.get('status', 'active')
                if status not in ('active', 'idle', 'deactive'):
                    status = 'active'
                await self.update_user_presence(online=True, status=status)
                await self.channel_layer.group_send(
                    PRESENCE_GROUP,
                    {'type': 'presence_update', 'user_id': self.user.id, 'status': status, 'online': True}
                )
        except (json.JSONDecodeError, TypeError):
            pass

    async def presence_update(self, event):
        # Broadcast to all (including sender) - each client updates their contact list
        await self.send(text_data=json.dumps({
            'type': 'presence_update',
            'user_id': event['user_id'],
            'status': event['status'],
            'online': event['online'],
        }))

    @database_sync_to_async
    def update_user_presence(self, online, status):
        User.objects.filter(id=self.user.id).update(online=online, status=status)

    @database_sync_to_async
    def get_all_presence(self):
        users = User.objects.filter(online=True).values('id', 'status', 'online')
        return {str(u['id']): {'status': u['status'], 'online': u['online']} for u in users}


class ChatConsumer(AsyncWebsocketConsumer):
    """Handles live chat messages and presence."""

    async def connect(self):
        self.user = self.scope.get('user')
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        await self.update_user_online(True)
        await self.channel_layer.group_send(
            self.room_group_name,
            {'type': 'user_joined', 'user': await self.user_data()}
        )

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.update_user_online(False)
            await self.channel_layer.group_send(
                self.room_group_name,
                {'type': 'user_left', 'user': await self.user_data()}
            )
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get('type', 'message')

        if msg_type == 'message':
            content = data.get('content', '').strip()
            if content:
                parent_id = data.get('parent')
                channel_id = data.get('channel')
                msg = await self.save_message(content, parent_id=parent_id, channel_id=channel_id)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {'type': 'chat_message', 'message': msg}
                )
        elif msg_type == 'edit':
            msg_id = data.get('id')
            content = data.get('content', '').strip()
            if msg_id and content:
                updated = await self.edit_message(msg_id, content)
                if updated:
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {'type': 'chat_message_edited', 'message': updated}
                    )
        elif msg_type == 'delete':
            msg_id = data.get('id')
            if msg_id:
                deleted = await self.delete_message(msg_id)
                if deleted:
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {'type': 'chat_message_deleted', 'message_id': msg_id}
                    )
        elif msg_type == 'typing':
            await self.channel_layer.group_send(
                self.room_group_name,
                {'type': 'user_typing', 'user': await self.user_data(), 'typing': data.get('typing', True), 'exclude_channel': self.channel_name}
            )
        elif msg_type == 'message_read':
            message_ids = data.get('message_ids', [])
            if message_ids:
                marked = await self.mark_messages_read(message_ids)
                if marked:
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {'type': 'message_read', 'message_ids': marked, 'user': await self.user_data()}
                    )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({'type': 'message', 'message': event['message']}))

    async def chat_message_edited(self, event):
        await self.send(text_data=json.dumps({'type': 'message_edited', 'message': event['message']}))

    async def chat_message_deleted(self, event):
        await self.send(text_data=json.dumps({'type': 'message_deleted', 'message_id': event['message_id']}))

    async def user_joined(self, event):
        await self.send(text_data=json.dumps({'type': 'user_joined', 'user': event['user']}))

    async def user_left(self, event):
        await self.send(text_data=json.dumps({'type': 'user_left', 'user': event['user']}))

    async def user_typing(self, event):
        if event.get('exclude_channel') == self.channel_name:
            return  # Don't send typing to sender – only receivers see it
        await self.send(text_data=json.dumps({
            'type': 'typing', 'user': event['user'], 'typing': event['typing']
        }))

    async def message_read(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_read', 'message_ids': event['message_ids'], 'user': event['user']
        }))

    async def chat_message_reacted(self, event):
        # Reactions are treated as message updates on the client side.
        await self.send(text_data=json.dumps({'type': 'message_updated', 'message': event['message']}))

    @database_sync_to_async
    def mark_messages_read(self, message_ids):
        from .models import Message, MessageRead
        marked = []
        for msg in Message.objects.filter(id__in=message_ids, room_id=self.room_id).exclude(sender=self.user):
            _, created = MessageRead.objects.get_or_create(
                message=msg, user=self.user, defaults={}
            )
            if created:
                marked.append(msg.id)
        return marked

    @database_sync_to_async
    def save_message(self, content, parent_id=None, channel_id=None):
        from .models import Message, Room, Channel
        room = Room.objects.get(id=self.room_id)
        parent = Message.objects.filter(id=parent_id, room=room).first() if parent_id else None
        channel = None
        if channel_id is not None:
            channel = Channel.objects.filter(id=channel_id, room=room).first()
        msg = Message.objects.create(
            room=room,
            channel=channel,
            sender=self.user,
            content=content,
            parent=parent,
            message_type='text',
        )
        return {
            'id': msg.id,
            'content': msg.content,
            'parent': parent_id if parent else None,
            'created_at': msg.created_at.isoformat(),
            'sender': {'id': self.user.id, 'username': self.user.username, 'title': self.user.title or ''},
            'channel': msg.channel_id,
            'reactions': msg.reactions or {},
            'read_by': []
        }

    @database_sync_to_async
    def edit_message(self, msg_id, content):
        from .models import Message
        msg = Message.objects.filter(id=msg_id, room_id=self.room_id, sender=self.user).first()
        if not msg:
            return None
        msg.content = content
        msg.edited_at = timezone.now()
        msg.save(update_fields=['content', 'edited_at'])
        return {
            'id': msg.id,
            'content': msg.content,
            'parent': msg.parent_id,
            'created_at': msg.created_at.isoformat(),
            'edited_at': msg.edited_at.isoformat() if msg.edited_at else None,
            'sender': {'id': self.user.id, 'username': self.user.username, 'title': self.user.title or ''},
            'channel': msg.channel_id,
            'reactions': msg.reactions or {},
            'read_by': list(msg.reads.values_list('user_id', flat=True))
        }

    @database_sync_to_async
    def delete_message(self, msg_id):
        from .models import Message
        msg = Message.objects.filter(id=msg_id, room_id=self.room_id, sender=self.user).first()
        if not msg:
            return False
        msg.delete()
        return True

    @database_sync_to_async
    def update_user_online(self, online):
        User.objects.filter(id=self.user.id).update(online=online)

    @database_sync_to_async
    def user_data(self):
        return {'id': self.user.id, 'username': self.user.username, 'title': self.user.title or ''}


class CallConsumer(AsyncWebsocketConsumer):
    """WebRTC signaling for video calls and screen sharing."""

    async def connect(self):
        self.user = self.scope.get('user')
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'call_{self.room_id}'

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_send(
                self.room_group_name,
                {'type': 'call_leave', 'user_id': self.user.id, 'channel': self.channel_name}
            )
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get('type')

        payload = {
            'type': msg_type,
            'from_user': await self.user_data(),
            **{k: v for k, v in data.items() if k != 'type'}
        }

        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'call_signal',
            'payload': payload,
            'exclude_channel': self.channel_name
        })

    async def call_signal(self, event):
        if event.get('exclude_channel') == self.channel_name:
            return
        await self.send(text_data=json.dumps(event['payload']))

    async def call_leave(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_left',
            'user_id': event['user_id']
        }))

    @database_sync_to_async
    def user_data(self):
        return {'id': self.user.id, 'username': self.user.username, 'title': self.user.title or ''}
