"""
Entity Extractor — extracts parameters (users, rooms, etc.) from voice commands.

Identifies and resolves entity references in voice commands:
- User mentions ("call John", "message Sarah")
- Room references ("join room general")
- Text content for messages
- Numeric parameters
"""
import re
import logging
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass

from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)


@dataclass
class ExtractedEntity:
    """An extracted entity with type, value, and resolution info."""
    entity_type: str  # 'user', 'room', 'text', 'number'
    raw_value: str
    resolved_value: Optional[str] = None
    resolved_id: Optional[int] = None
    confidence: float = 1.0
    start_pos: int = 0
    end_pos: int = 0


class EntityExtractor:
    """
    Extract and resolve entities from voice command text.

    Entity types:
    - User: resolves against User model (username, first_name, last_name)
    - Room: resolves against Room model (name)
    - Text: free-form text content (for messages)
    - Number: numeric values

    Uses multiple strategies:
    1. Positional extraction (based on command pattern)
    2. Named entity patterns (prepositions: "to <user>", "in <room>")
    3. Database fuzzy matching
    """

    PREPOSITION_PATTERNS = {
        'user': [
            r'\b(?:to|with|for)\s+(\w+)',
            r'\buser\s+(\w+)',
            r'\bcall\s+(\w+)',
            r'\bselect\s+(\w+)',
            r'\bmessage\s+(\w+)',
        ],
        'room': [
            r'\broom\s+(\w+)',
            r'\bin\s+(\w+)',
            r'\bjoin\s+(\w+)',
            r'\bopen\s+(\w+)',
        ],
        'text': [
            r'\bsay(?:ing)?\s+"([^"]+)"',
            r'\bsay(?:ing)?\s+(.+)$',
            r'\bmessage\s+\w+\s+(.+)$',
        ],
    }

    STOP_WORDS = {
        'the', 'a', 'an', 'to', 'in', 'for', 'with', 'from',
        'call', 'message', 'send', 'video', 'join', 'leave',
        'create', 'room', 'user', 'mute', 'unmute', 'select',
        'open', 'close', 'back', 'start', 'stop', 'share',
        'screen', 'camera', 'yes', 'no', 'cancel', 'confirm',
        'please', 'can', 'you', 'i', 'want', 'would', 'like',
        'trutim', 'hey', 'okay', 'ok',
    }

    def __init__(self):
        self._user_cache: Dict[str, List[Dict]] = {}
        self._room_cache: Dict[str, List[Dict]] = {}

    def extract(self, text: str, intent_name: str,
                required_params: Optional[List[str]] = None
                ) -> Dict[str, ExtractedEntity]:
        """
        Extract entities from command text based on intent.
        Returns dict mapping param_name -> ExtractedEntity.
        """
        text_lower = text.lower().strip()
        entities = {}

        required_params = required_params or []

        for param in required_params:
            if param == 'user':
                entity = self._extract_user(text_lower, intent_name)
                if entity:
                    entities['user'] = entity
            elif param == 'room':
                entity = self._extract_room(text_lower, intent_name)
                if entity:
                    entities['room'] = entity
            elif param == 'content' or param == 'text':
                entity = self._extract_text(text_lower, intent_name)
                if entity:
                    entities['content'] = entity

        if 'user' not in entities and self._might_contain_user(text_lower, intent_name):
            entity = self._extract_user(text_lower, intent_name)
            if entity:
                entities['user'] = entity

        if 'room' not in entities and self._might_contain_room(text_lower, intent_name):
            entity = self._extract_room(text_lower, intent_name)
            if entity:
                entities['room'] = entity

        return entities

    async def extract_and_resolve(self, text: str, intent_name: str,
                                    required_params: Optional[List[str]] = None
                                    ) -> Dict[str, ExtractedEntity]:
        """Extract entities and resolve them against the database."""
        entities = self.extract(text, intent_name, required_params)

        if 'user' in entities:
            resolved = await self._resolve_user(entities['user'].raw_value)
            if resolved:
                entities['user'].resolved_value = resolved['username']
                entities['user'].resolved_id = resolved['id']
                entities['user'].confidence = resolved['confidence']

        if 'room' in entities:
            resolved = await self._resolve_room(entities['room'].raw_value)
            if resolved:
                entities['room'].resolved_value = resolved['name']
                entities['room'].resolved_id = resolved['id']
                entities['room'].confidence = resolved['confidence']

        return entities

    def _extract_user(self, text: str, intent_name: str
                       ) -> Optional[ExtractedEntity]:
        """Extract user reference from text."""
        for pattern in self.PREPOSITION_PATTERNS['user']:
            match = re.search(pattern, text)
            if match:
                raw = match.group(1)
                if raw.lower() not in self.STOP_WORDS:
                    return ExtractedEntity(
                        entity_type='user',
                        raw_value=raw,
                        start_pos=match.start(1),
                        end_pos=match.end(1),
                    )

        words = text.split()
        for word in reversed(words):
            if word not in self.STOP_WORDS and len(word) > 1:
                return ExtractedEntity(
                    entity_type='user',
                    raw_value=word,
                    confidence=0.6,
                )

        return None

    def _extract_room(self, text: str, intent_name: str
                       ) -> Optional[ExtractedEntity]:
        """Extract room reference from text."""
        for pattern in self.PREPOSITION_PATTERNS['room']:
            match = re.search(pattern, text)
            if match:
                raw = match.group(1)
                if raw.lower() not in self.STOP_WORDS:
                    return ExtractedEntity(
                        entity_type='room',
                        raw_value=raw,
                        start_pos=match.start(1),
                        end_pos=match.end(1),
                    )

        return None

    def _extract_text(self, text: str, intent_name: str
                       ) -> Optional[ExtractedEntity]:
        """Extract free-form text content."""
        for pattern in self.PREPOSITION_PATTERNS['text']:
            match = re.search(pattern, text)
            if match:
                return ExtractedEntity(
                    entity_type='text',
                    raw_value=match.group(1),
                    resolved_value=match.group(1),
                    start_pos=match.start(1),
                    end_pos=match.end(1),
                )
        return None

    def _might_contain_user(self, text: str, intent_name: str) -> bool:
        user_intents = {'call_user', 'video_call', 'send_message',
                        'select_user', 'send_to_everyone'}
        return intent_name in user_intents

    def _might_contain_room(self, text: str, intent_name: str) -> bool:
        room_intents = {'join_room', 'create_room', 'open_room'}
        return intent_name in room_intents

    @database_sync_to_async
    def _resolve_user(self, raw_name: str) -> Optional[Dict]:
        """Resolve a user name against the database."""
        User = get_user_model()

        try:
            user = User.objects.get(username__iexact=raw_name)
            return {'id': user.id, 'username': user.username, 'confidence': 1.0}
        except User.DoesNotExist:
            pass

        candidates = User.objects.filter(
            first_name__icontains=raw_name
        ) | User.objects.filter(
            last_name__icontains=raw_name
        ) | User.objects.filter(
            username__icontains=raw_name
        )

        candidates = candidates[:5]
        if candidates.exists():
            best = candidates.first()
            confidence = 0.8
            if best.username.lower() == raw_name.lower():
                confidence = 1.0
            elif raw_name.lower() in best.first_name.lower():
                confidence = 0.9

            return {
                'id': best.id,
                'username': best.username,
                'confidence': confidence,
            }

        return None

    @database_sync_to_async
    def _resolve_room(self, raw_name: str) -> Optional[Dict]:
        """Resolve a room name against the database."""
        from chat.models import Room

        try:
            room = Room.objects.get(name__iexact=raw_name)
            return {'id': room.id, 'name': room.name, 'confidence': 1.0}
        except Room.DoesNotExist:
            pass

        candidates = Room.objects.filter(name__icontains=raw_name)[:5]
        if candidates.exists():
            best = candidates.first()
            confidence = 0.8 if raw_name.lower() in best.name.lower() else 0.6
            return {'id': best.id, 'name': best.name, 'confidence': confidence}

        return None
