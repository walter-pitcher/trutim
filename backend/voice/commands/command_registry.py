"""
Command Registry — central registry of all voice commands.

Defines the complete vocabulary of voice commands supported by the
Trutim platform, including their triggers, parameters, and handlers.
"""
import logging
from typing import Callable, Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class CommandCategory(str, Enum):
    COMMUNICATION = 'communication'
    ROOM = 'room'
    MEDIA = 'media'
    NAVIGATION = 'navigation'
    CONFIRMATION = 'confirmation'
    SYSTEM = 'system'


class ParamType(str, Enum):
    USER = 'user'
    ROOM = 'room'
    TEXT = 'text'
    BOOLEAN = 'boolean'
    NUMBER = 'number'


@dataclass
class CommandParam:
    """Definition of a command parameter."""
    name: str
    param_type: ParamType
    required: bool = True
    default: Any = None
    description: str = ''


@dataclass
class VoiceCommand:
    """Definition of a voice command."""
    name: str
    category: CommandCategory
    trigger_phrases: List[str]
    params: List[CommandParam] = field(default_factory=list)
    description: str = ''
    handler: Optional[str] = None  # dotted path to handler function
    requires_confirmation: bool = False
    aliases: List[str] = field(default_factory=list)
    priority: int = 0  # higher = checked first


class CommandRegistry:
    """
    Central registry for all platform voice commands.

    Provides:
    - Command registration and discovery
    - Trigger phrase matching
    - Parameter validation
    - Command serialization for API responses
    """

    _commands: Dict[str, VoiceCommand] = {}
    _trigger_index: Dict[str, str] = {}  # trigger_phrase -> command_name
    _initialized = False

    @classmethod
    def register(cls, command: VoiceCommand):
        """Register a voice command."""
        cls._commands[command.name] = command
        for phrase in command.trigger_phrases:
            cls._trigger_index[phrase.lower()] = command.name
        for alias in command.aliases:
            cls._trigger_index[alias.lower()] = command.name
        logger.debug("Registered voice command: %s", command.name)

    @classmethod
    def get_command(cls, name: str) -> Optional[VoiceCommand]:
        return cls._commands.get(name)

    @classmethod
    def find_by_trigger(cls, phrase: str) -> Optional[VoiceCommand]:
        """Find a command matching a trigger phrase."""
        phrase_lower = phrase.lower().strip()

        if phrase_lower in cls._trigger_index:
            return cls._commands[cls._trigger_index[phrase_lower]]

        best_match = None
        best_score = 0

        for trigger, cmd_name in cls._trigger_index.items():
            if trigger in phrase_lower or phrase_lower in trigger:
                score = len(trigger) if trigger in phrase_lower else len(phrase_lower) * 0.8
                if score > best_score:
                    best_score = score
                    best_match = cls._commands[cmd_name]

        return best_match

    @classmethod
    def find_by_keywords(cls, keywords: List[str]) -> Optional[VoiceCommand]:
        """Find a command matching a list of spotted keywords."""
        keywords_lower = [k.lower() for k in keywords]
        phrase = ' '.join(keywords_lower)

        direct = cls.find_by_trigger(phrase)
        if direct:
            return direct

        best_match = None
        best_score = 0

        for cmd in cls._commands.values():
            score = 0
            for trigger in cmd.trigger_phrases:
                trigger_words = trigger.lower().split()
                matched = sum(1 for w in trigger_words if w in keywords_lower)
                trigger_score = matched / max(len(trigger_words), 1)
                score = max(score, trigger_score)

            if score > best_score and score > 0.3:
                best_score = score
                best_match = cmd

        return best_match

    @classmethod
    def get_all_commands(cls) -> List[VoiceCommand]:
        return list(cls._commands.values())

    @classmethod
    def get_commands_by_category(cls, category: CommandCategory) -> List[VoiceCommand]:
        return [c for c in cls._commands.values() if c.category == category]

    @classmethod
    def get_all_triggers(cls) -> List[str]:
        return list(cls._trigger_index.keys())

    @classmethod
    def serialize_commands(cls) -> List[Dict]:
        """Serialize all commands for API response."""
        return [
            {
                'name': cmd.name,
                'category': cmd.category.value,
                'trigger_phrases': cmd.trigger_phrases,
                'params': [
                    {
                        'name': p.name,
                        'type': p.param_type.value,
                        'required': p.required,
                        'description': p.description,
                    }
                    for p in cmd.params
                ],
                'description': cmd.description,
                'requires_confirmation': cmd.requires_confirmation,
                'aliases': cmd.aliases,
            }
            for cmd in cls._commands.values()
        ]

    @classmethod
    def auto_discover(cls):
        """Auto-register all built-in platform commands."""
        if cls._initialized:
            return
        cls._initialized = True
        _register_platform_commands()
        logger.info("Registered %d voice commands", len(cls._commands))


def _register_platform_commands():
    """Register all built-in Trutim platform voice commands."""

    # --- Communication ---

    CommandRegistry.register(VoiceCommand(
        name='call_user',
        category=CommandCategory.COMMUNICATION,
        trigger_phrases=['call', 'call user', 'phone call'],
        params=[CommandParam('user', ParamType.USER, description='User to call')],
        description='Start a voice call with a user',
        handler='voice.commands.command_executor.execute_call',
        aliases=['ring', 'dial'],
        priority=10,
    ))

    CommandRegistry.register(VoiceCommand(
        name='video_call',
        category=CommandCategory.COMMUNICATION,
        trigger_phrases=['video call', 'start video call', 'video', 'start video'],
        params=[CommandParam('user', ParamType.USER, required=False,
                             description='User to video call')],
        description='Start a video call',
        handler='voice.commands.command_executor.execute_video_call',
        aliases=['face call', 'facetime'],
        priority=10,
    ))

    CommandRegistry.register(VoiceCommand(
        name='send_message',
        category=CommandCategory.COMMUNICATION,
        trigger_phrases=['send message', 'message', 'send message to', 'text'],
        params=[
            CommandParam('user', ParamType.USER, description='Recipient'),
            CommandParam('content', ParamType.TEXT, required=False,
                         description='Message content'),
        ],
        description='Send a text message to a user',
        handler='voice.commands.command_executor.execute_send_message',
        aliases=['msg', 'dm'],
        priority=10,
    ))

    # --- Room Management ---

    CommandRegistry.register(VoiceCommand(
        name='join_room',
        category=CommandCategory.ROOM,
        trigger_phrases=['join room', 'join', 'enter room'],
        params=[CommandParam('room', ParamType.ROOM, description='Room to join')],
        description='Join a chat room',
        handler='voice.commands.command_executor.execute_join_room',
        aliases=['go to room'],
        priority=8,
    ))

    CommandRegistry.register(VoiceCommand(
        name='leave_room',
        category=CommandCategory.ROOM,
        trigger_phrases=['leave room', 'leave', 'exit room'],
        description='Leave current room',
        handler='voice.commands.command_executor.execute_leave_room',
        aliases=['exit'],
        priority=8,
    ))

    CommandRegistry.register(VoiceCommand(
        name='create_room',
        category=CommandCategory.ROOM,
        trigger_phrases=['create room', 'new room', 'create'],
        params=[CommandParam('room', ParamType.ROOM, description='Room name')],
        description='Create a new room',
        handler='voice.commands.command_executor.execute_create_room',
        requires_confirmation=True,
        priority=7,
    ))

    # --- Media Controls ---

    CommandRegistry.register(VoiceCommand(
        name='mute_mic',
        category=CommandCategory.MEDIA,
        trigger_phrases=['mute', 'mute microphone', 'mute mic'],
        description='Mute microphone',
        handler='voice.commands.command_executor.execute_mute',
        priority=9,
    ))

    CommandRegistry.register(VoiceCommand(
        name='unmute_mic',
        category=CommandCategory.MEDIA,
        trigger_phrases=['unmute', 'unmute microphone', 'unmute mic'],
        description='Unmute microphone',
        handler='voice.commands.command_executor.execute_unmute',
        priority=9,
    ))

    CommandRegistry.register(VoiceCommand(
        name='toggle_camera',
        category=CommandCategory.MEDIA,
        trigger_phrases=['camera', 'toggle camera', 'mute camera', 'unmute camera'],
        description='Toggle camera on/off',
        handler='voice.commands.command_executor.execute_toggle_camera',
        priority=9,
    ))

    CommandRegistry.register(VoiceCommand(
        name='share_screen',
        category=CommandCategory.MEDIA,
        trigger_phrases=['share screen', 'screen share', 'share'],
        description='Start screen sharing',
        handler='voice.commands.command_executor.execute_share_screen',
        priority=8,
    ))

    CommandRegistry.register(VoiceCommand(
        name='stop_share',
        category=CommandCategory.MEDIA,
        trigger_phrases=['stop share', 'stop screen share', 'stop sharing'],
        description='Stop screen sharing',
        handler='voice.commands.command_executor.execute_stop_share',
        priority=8,
    ))

    # --- Navigation ---

    CommandRegistry.register(VoiceCommand(
        name='select_user',
        category=CommandCategory.NAVIGATION,
        trigger_phrases=['select user', 'select', 'choose user'],
        params=[CommandParam('user', ParamType.USER, description='User to select')],
        description='Select a user for interaction',
        handler='voice.commands.command_executor.execute_select_user',
        priority=7,
    ))

    CommandRegistry.register(VoiceCommand(
        name='open_room',
        category=CommandCategory.NAVIGATION,
        trigger_phrases=['open room', 'open', 'go to'],
        params=[CommandParam('room', ParamType.ROOM, description='Room to open')],
        description='Open/navigate to a room',
        handler='voice.commands.command_executor.execute_open_room',
        priority=7,
    ))

    CommandRegistry.register(VoiceCommand(
        name='go_back',
        category=CommandCategory.NAVIGATION,
        trigger_phrases=['go back', 'back', 'previous'],
        description='Navigate back',
        handler='voice.commands.command_executor.execute_go_back',
        priority=6,
    ))

    # --- Confirmation ---

    CommandRegistry.register(VoiceCommand(
        name='confirm',
        category=CommandCategory.CONFIRMATION,
        trigger_phrases=['yes', 'confirm', 'okay', 'ok'],
        description='Confirm an action',
        handler='voice.commands.command_executor.execute_confirm',
        priority=5,
    ))

    CommandRegistry.register(VoiceCommand(
        name='deny',
        category=CommandCategory.CONFIRMATION,
        trigger_phrases=['no', 'cancel', 'deny', 'stop'],
        description='Cancel/deny an action',
        handler='voice.commands.command_executor.execute_deny',
        priority=5,
    ))

    # --- System ---

    CommandRegistry.register(VoiceCommand(
        name='end_call',
        category=CommandCategory.SYSTEM,
        trigger_phrases=['end call', 'hang up', 'end', 'disconnect'],
        description='End the current call',
        handler='voice.commands.command_executor.execute_end_call',
        priority=10,
    ))

    CommandRegistry.register(VoiceCommand(
        name='send_to_everyone',
        category=CommandCategory.COMMUNICATION,
        trigger_phrases=['send to everyone', 'message everyone', 'broadcast'],
        params=[CommandParam('content', ParamType.TEXT, required=False)],
        description='Send message to everyone in room',
        handler='voice.commands.command_executor.execute_send_to_all',
        priority=8,
    ))
