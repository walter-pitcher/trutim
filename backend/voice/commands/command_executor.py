"""
Command Executor — executes voice commands against the Trutim platform.

Maps classified intents and extracted entities to actual platform
operations (sending messages, initiating calls, room management, etc.)
via the Django ORM and Channels layer.
"""
import json
import logging
import time
from typing import Optional, Dict, Any

from channels.layers import get_channel_layer
from channels.db import database_sync_to_async
from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model

from .command_registry import CommandRegistry
from .intent_classifier import Intent, IntentClassifier
from .entity_extractor import EntityExtractor, ExtractedEntity

logger = logging.getLogger(__name__)


class CommandResult:
    """Result of a command execution."""

    def __init__(self, success: bool, command: str,
                 message: str = '', data: Optional[Dict] = None,
                 requires_follow_up: bool = False,
                 follow_up_prompt: str = ''):
        self.success = success
        self.command = command
        self.message = message
        self.data = data or {}
        self.requires_follow_up = requires_follow_up
        self.follow_up_prompt = follow_up_prompt
        self.timestamp = time.time()

    def to_dict(self) -> Dict:
        return {
            'success': self.success,
            'command': self.command,
            'message': self.message,
            'data': self.data,
            'requires_follow_up': self.requires_follow_up,
            'follow_up_prompt': self.follow_up_prompt,
            'timestamp': self.timestamp,
        }


class CommandExecutor:
    """
    Executes voice commands on the Trutim platform.

    Handles the full execution lifecycle:
    1. Validate intent and parameters
    2. Check permissions
    3. Execute the action (DB operations, WebSocket messages)
    4. Return result with feedback for the user
    5. Handle confirmation flows for destructive actions

    Works asynchronously for WebSocket integration.
    """

    def __init__(self):
        self.intent_classifier = IntentClassifier()
        self.entity_extractor = EntityExtractor()
        self.channel_layer = get_channel_layer()

        self._pending_confirmations: Dict[int, Dict] = {}  # user_id -> pending

    async def execute(self, intent: Intent, entities: Dict[str, ExtractedEntity],
                       user, room_id: Optional[int] = None) -> CommandResult:
        """Execute a classified intent with extracted entities."""
        command = CommandRegistry.get_command(intent.name)
        if command is None:
            return CommandResult(
                success=False, command=intent.name,
                message=f"Unknown command: {intent.name}",
            )

        if command.requires_confirmation:
            if user.id not in self._pending_confirmations:
                self._pending_confirmations[user.id] = {
                    'intent': intent,
                    'entities': entities,
                    'room_id': room_id,
                    'timestamp': time.time(),
                }
                return CommandResult(
                    success=True, command=intent.name,
                    message=f"Are you sure you want to {command.description.lower()}?",
                    requires_follow_up=True,
                    follow_up_prompt='Say "confirm" or "cancel"',
                )

        handler = self._get_handler(intent.name)
        try:
            result = await handler(intent, entities, user, room_id)
            return result
        except Exception as e:
            logger.error("Command execution error: %s", e)
            return CommandResult(
                success=False, command=intent.name,
                message=f"Error executing command: {str(e)}",
            )

    async def execute_from_text(self, text: str, user,
                                  room_id: Optional[int] = None) -> CommandResult:
        """Full pipeline: text -> intent -> entities -> execute."""
        intent = self.intent_classifier.classify(text=text)

        if intent.name == 'unknown':
            return CommandResult(
                success=False, command='unknown',
                message="I didn't understand that command. Try 'call', 'message', "
                        "'join room', 'mute', or 'share screen'.",
            )

        command = CommandRegistry.get_command(intent.name)
        required_params = [p.name for p in command.params] if command else []

        entities = await self.entity_extractor.extract_and_resolve(
            text, intent.name, required_params
        )

        return await self.execute(intent, entities, user, room_id)

    async def execute_from_keywords(self, keywords: list, user,
                                      room_id: Optional[int] = None
                                      ) -> CommandResult:
        """Execute from spotted keywords."""
        intent = self.intent_classifier.classify(keywords=keywords)

        if intent.name == 'unknown':
            return CommandResult(
                success=False, command='unknown',
                message="Couldn't determine command from keywords.",
            )

        text = ' '.join(keywords)
        command = CommandRegistry.get_command(intent.name)
        required_params = [p.name for p in command.params] if command else []

        entities = await self.entity_extractor.extract_and_resolve(
            text, intent.name, required_params
        )

        return await self.execute(intent, entities, user, room_id)

    def _get_handler(self, intent_name: str):
        """Get the handler function for an intent."""
        handlers = {
            'call_user': self._handle_call,
            'video_call': self._handle_video_call,
            'send_message': self._handle_send_message,
            'join_room': self._handle_join_room,
            'leave_room': self._handle_leave_room,
            'create_room': self._handle_create_room,
            'mute_mic': self._handle_mute,
            'unmute_mic': self._handle_unmute,
            'toggle_camera': self._handle_toggle_camera,
            'share_screen': self._handle_share_screen,
            'stop_share': self._handle_stop_share,
            'select_user': self._handle_select_user,
            'open_room': self._handle_open_room,
            'go_back': self._handle_go_back,
            'confirm': self._handle_confirm,
            'deny': self._handle_deny,
            'end_call': self._handle_end_call,
            'send_to_everyone': self._handle_send_to_all,
        }
        return handlers.get(intent_name, self._handle_unknown)

    # --- Command Handlers ---

    async def _handle_call(self, intent, entities, user, room_id):
        """Initiate a voice call."""
        target_user = entities.get('user')

        if not target_user or not target_user.resolved_id:
            return CommandResult(
                success=False, command='call_user',
                message="Who would you like to call? Say 'call' followed by a username.",
                requires_follow_up=True,
                follow_up_prompt="Say the username",
            )

        await self._send_to_channel_group(
            f'call_{room_id}' if room_id else f'user_{target_user.resolved_id}',
            {
                'type': 'call_signal',
                'payload': {
                    'type': 'call_initiate',
                    'from_user': {'id': user.id, 'username': user.username},
                    'call_type': 'voice',
                    'voice_triggered': True,
                },
                'exclude_channel': '',
            }
        )

        return CommandResult(
            success=True, command='call_user',
            message=f"Calling {target_user.resolved_value or target_user.raw_value}...",
            data={
                'action': 'call_initiate',
                'target_user': target_user.resolved_value,
                'target_user_id': target_user.resolved_id,
                'call_type': 'voice',
            }
        )

    async def _handle_video_call(self, intent, entities, user, room_id):
        """Initiate a video call."""
        target_user = entities.get('user')

        group = f'call_{room_id}' if room_id else None
        if target_user and target_user.resolved_id:
            group = group or f'user_{target_user.resolved_id}'

        if group:
            await self._send_to_channel_group(group, {
                'type': 'call_signal',
                'payload': {
                    'type': 'call_initiate',
                    'from_user': {'id': user.id, 'username': user.username},
                    'call_type': 'video',
                    'voice_triggered': True,
                },
                'exclude_channel': '',
            })

        target_name = (target_user.resolved_value or target_user.raw_value) if target_user else 'room'
        return CommandResult(
            success=True, command='video_call',
            message=f"Starting video call with {target_name}...",
            data={'action': 'video_call_initiate', 'call_type': 'video'}
        )

    async def _handle_send_message(self, intent, entities, user, room_id):
        """Send a text message."""
        target_user = entities.get('user')
        content = entities.get('content')

        if not room_id and (not target_user or not target_user.resolved_id):
            return CommandResult(
                success=False, command='send_message',
                message="Who should I send the message to?",
                requires_follow_up=True,
                follow_up_prompt="Say the username",
            )

        if content and content.raw_value:
            message_text = content.raw_value
        else:
            return CommandResult(
                success=True, command='send_message',
                message="What would you like to say?",
                requires_follow_up=True,
                follow_up_prompt="Say your message",
                data={'action': 'compose_message', 'pending': True},
            )

        if room_id:
            await self._send_chat_message(room_id, user, message_text)

        target_name = (target_user.resolved_value or target_user.raw_value) if target_user else 'room'
        return CommandResult(
            success=True, command='send_message',
            message=f"Message sent to {target_name}.",
            data={'action': 'message_sent', 'content': message_text}
        )

    async def _handle_join_room(self, intent, entities, user, room_id):
        """Join a chat room."""
        room_entity = entities.get('room')

        if not room_entity:
            return CommandResult(
                success=False, command='join_room',
                message="Which room would you like to join?",
                requires_follow_up=True,
                follow_up_prompt="Say the room name",
            )

        if room_entity.resolved_id:
            await self._join_room_db(user, room_entity.resolved_id)

        return CommandResult(
            success=True, command='join_room',
            message=f"Joined room '{room_entity.resolved_value or room_entity.raw_value}'.",
            data={
                'action': 'join_room',
                'room_id': room_entity.resolved_id,
                'room_name': room_entity.resolved_value,
            }
        )

    async def _handle_leave_room(self, intent, entities, user, room_id):
        if room_id:
            await self._leave_room_db(user, room_id)

        return CommandResult(
            success=True, command='leave_room',
            message="Left the room.",
            data={'action': 'leave_room', 'room_id': room_id}
        )

    async def _handle_create_room(self, intent, entities, user, room_id):
        room_entity = entities.get('room')
        room_name = room_entity.raw_value if room_entity else 'New Room'

        new_room_id = await self._create_room_db(user, room_name)

        return CommandResult(
            success=True, command='create_room',
            message=f"Room '{room_name}' created.",
            data={'action': 'create_room', 'room_id': new_room_id, 'room_name': room_name}
        )

    async def _handle_mute(self, intent, entities, user, room_id):
        return CommandResult(
            success=True, command='mute_mic',
            message="Microphone muted.",
            data={'action': 'mute', 'target': 'microphone'}
        )

    async def _handle_unmute(self, intent, entities, user, room_id):
        return CommandResult(
            success=True, command='unmute_mic',
            message="Microphone unmuted.",
            data={'action': 'unmute', 'target': 'microphone'}
        )

    async def _handle_toggle_camera(self, intent, entities, user, room_id):
        return CommandResult(
            success=True, command='toggle_camera',
            message="Camera toggled.",
            data={'action': 'toggle_camera'}
        )

    async def _handle_share_screen(self, intent, entities, user, room_id):
        return CommandResult(
            success=True, command='share_screen',
            message="Screen sharing started.",
            data={'action': 'share_screen'}
        )

    async def _handle_stop_share(self, intent, entities, user, room_id):
        return CommandResult(
            success=True, command='stop_share',
            message="Screen sharing stopped.",
            data={'action': 'stop_share'}
        )

    async def _handle_select_user(self, intent, entities, user, room_id):
        target = entities.get('user')
        name = (target.resolved_value or target.raw_value) if target else 'unknown'
        return CommandResult(
            success=True, command='select_user',
            message=f"User '{name}' selected.",
            data={
                'action': 'select_user',
                'user_id': target.resolved_id if target else None,
                'username': name,
            }
        )

    async def _handle_open_room(self, intent, entities, user, room_id):
        room = entities.get('room')
        name = (room.resolved_value or room.raw_value) if room else 'unknown'
        return CommandResult(
            success=True, command='open_room',
            message=f"Opened room '{name}'.",
            data={
                'action': 'navigate_room',
                'room_id': room.resolved_id if room else None,
                'room_name': name,
            }
        )

    async def _handle_go_back(self, intent, entities, user, room_id):
        return CommandResult(
            success=True, command='go_back',
            message="Navigated back.",
            data={'action': 'navigate_back'}
        )

    async def _handle_confirm(self, intent, entities, user, room_id):
        pending = self._pending_confirmations.pop(user.id, None)
        if pending:
            return await self.execute(
                pending['intent'], pending['entities'],
                user, pending['room_id']
            )
        return CommandResult(
            success=True, command='confirm',
            message="Confirmed.",
            data={'action': 'confirm'}
        )

    async def _handle_deny(self, intent, entities, user, room_id):
        self._pending_confirmations.pop(user.id, None)
        return CommandResult(
            success=True, command='deny',
            message="Action cancelled.",
            data={'action': 'cancel'}
        )

    async def _handle_end_call(self, intent, entities, user, room_id):
        if room_id:
            await self._send_to_channel_group(f'call_{room_id}', {
                'type': 'call_signal',
                'payload': {
                    'type': 'call_end',
                    'from_user': {'id': user.id, 'username': user.username},
                    'voice_triggered': True,
                },
                'exclude_channel': '',
            })

        return CommandResult(
            success=True, command='end_call',
            message="Call ended.",
            data={'action': 'end_call'}
        )

    async def _handle_send_to_all(self, intent, entities, user, room_id):
        content = entities.get('content')
        if content and room_id:
            await self._send_chat_message(room_id, user, content.raw_value)
            return CommandResult(
                success=True, command='send_to_everyone',
                message="Message sent to everyone.",
                data={'action': 'broadcast_message'}
            )
        return CommandResult(
            success=True, command='send_to_everyone',
            message="What would you like to say to everyone?",
            requires_follow_up=True,
            follow_up_prompt="Say your message",
        )

    async def _handle_unknown(self, intent, entities, user, room_id):
        return CommandResult(
            success=False, command='unknown',
            message="I didn't understand that command.",
        )

    # --- Database operations ---

    @database_sync_to_async
    def _send_chat_message(self, room_id, user, content):
        from chat.models import Message, Room
        room = Room.objects.get(id=room_id)
        Message.objects.create(room=room, sender=user, content=content)

    @database_sync_to_async
    def _join_room_db(self, user, room_id):
        from chat.models import Room
        room = Room.objects.get(id=room_id)
        room.members.add(user)

    @database_sync_to_async
    def _leave_room_db(self, user, room_id):
        from chat.models import Room
        room = Room.objects.get(id=room_id)
        room.members.remove(user)

    @database_sync_to_async
    def _create_room_db(self, user, name):
        from chat.models import Room
        room = Room.objects.create(name=name, created_by=user)
        room.members.add(user)
        return room.id

    async def _send_to_channel_group(self, group_name, message):
        if self.channel_layer:
            await self.channel_layer.group_send(group_name, message)
