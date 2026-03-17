"""
Intent Classifier — maps recognized speech to platform intents.

Uses a combination of keyword matching, pattern matching, and
neural classification to determine user intent from voice commands.
"""
import numpy as np
import logging
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass

from .command_registry import CommandRegistry, CommandCategory, VoiceCommand
from ..asr.language_model import CommandLanguageModel

logger = logging.getLogger(__name__)


class Intent:
    """Represents a classified intent with confidence and parameters."""

    def __init__(self, name: str, confidence: float,
                 category: str = '', params: Optional[Dict] = None,
                 raw_text: str = '', keywords: Optional[List[str]] = None):
        self.name = name
        self.confidence = confidence
        self.category = category
        self.params = params or {}
        self.raw_text = raw_text
        self.keywords = keywords or []

    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'confidence': self.confidence,
            'category': self.category,
            'params': self.params,
            'raw_text': self.raw_text,
            'keywords': self.keywords,
        }


class IntentClassifier:
    """
    Multi-strategy intent classifier for voice commands.

    Classification strategies (used in priority order):
    1. Exact trigger phrase match — highest confidence
    2. Keyword-based match — from keyword spotter output
    3. Pattern matching — regex-like command pattern matching
    4. Language model scoring — re-rank candidates
    5. Fuzzy match — fallback for noisy recognition

    Returns the best matching intent with confidence score.
    """

    def __init__(self, language_model: Optional[CommandLanguageModel] = None):
        self.language_model = language_model or CommandLanguageModel()
        CommandRegistry.auto_discover()

    def classify(self, text: str = '',
                 keywords: Optional[List[str]] = None,
                 keyword_confidences: Optional[List[float]] = None
                 ) -> Intent:
        """
        Classify intent from text and/or keywords.
        Returns the most likely Intent.
        """
        candidates = []

        if text:
            candidates.extend(self._classify_from_text(text))

        if keywords:
            candidates.extend(self._classify_from_keywords(
                keywords, keyword_confidences
            ))

        if not candidates:
            return Intent(
                name='unknown', confidence=0.0,
                raw_text=text, keywords=keywords or [],
            )

        candidates.sort(key=lambda c: c.confidence, reverse=True)

        if self.language_model and text:
            candidates = self._rescore_with_lm(candidates, text)

        best = candidates[0]
        logger.debug("Classified intent: %s (%.3f) from '%s'",
                      best.name, best.confidence, text or keywords)
        return best

    def classify_top_k(self, text: str = '',
                        keywords: Optional[List[str]] = None,
                        k: int = 3) -> List[Intent]:
        """Return top-k intent candidates."""
        candidates = []

        if text:
            candidates.extend(self._classify_from_text(text))
        if keywords:
            candidates.extend(self._classify_from_keywords(keywords))

        candidates.sort(key=lambda c: c.confidence, reverse=True)

        seen = set()
        unique = []
        for c in candidates:
            if c.name not in seen:
                seen.add(c.name)
                unique.append(c)

        return unique[:k]

    def _classify_from_text(self, text: str) -> List[Intent]:
        """Classify intent from recognized text."""
        candidates = []
        text_lower = text.lower().strip()
        words = text_lower.split()

        # Strategy 1: Exact trigger match
        command = CommandRegistry.find_by_trigger(text_lower)
        if command:
            candidates.append(Intent(
                name=command.name,
                confidence=0.95,
                category=command.category.value,
                raw_text=text,
            ))

        # Strategy 2: Partial word matching
        for cmd in CommandRegistry.get_all_commands():
            for phrase in cmd.trigger_phrases:
                phrase_words = phrase.lower().split()
                matched = sum(1 for w in phrase_words if w in words)
                if matched > 0:
                    score = matched / max(len(phrase_words), 1)
                    score *= (cmd.priority / 10.0)
                    if score > 0.3:
                        candidates.append(Intent(
                            name=cmd.name,
                            confidence=min(score, 0.9),
                            category=cmd.category.value,
                            raw_text=text,
                        ))

        # Strategy 3: Fuzzy matching
        if not candidates:
            candidates.extend(self._fuzzy_match(text_lower))

        return candidates

    def _classify_from_keywords(self, keywords: List[str],
                                  confidences: Optional[List[float]] = None
                                  ) -> List[Intent]:
        """Classify intent from spotted keywords."""
        candidates = []

        command = CommandRegistry.find_by_keywords(keywords)
        if command:
            avg_conf = np.mean(confidences) if confidences else 0.8
            candidates.append(Intent(
                name=command.name,
                confidence=float(avg_conf * 0.9),
                category=command.category.value,
                keywords=keywords,
            ))

        action_map = {
            'call': 'call_user',
            'video': 'video_call',
            'message': 'send_message',
            'send': 'send_message',
            'join': 'join_room',
            'leave': 'leave_room',
            'create': 'create_room',
            'mute': 'mute_mic',
            'unmute': 'unmute_mic',
            'camera': 'toggle_camera',
            'share': 'share_screen',
            'screen': 'share_screen',
            'select': 'select_user',
            'open': 'open_room',
            'back': 'go_back',
            'yes': 'confirm',
            'no': 'deny',
            'cancel': 'deny',
            'confirm': 'confirm',
        }

        for i, kw in enumerate(keywords):
            kw_lower = kw.lower()
            if kw_lower in action_map:
                cmd_name = action_map[kw_lower]
                conf = confidences[i] if confidences and i < len(confidences) else 0.7
                candidates.append(Intent(
                    name=cmd_name,
                    confidence=float(conf * 0.85),
                    category='',
                    keywords=keywords,
                ))

        return candidates

    def _fuzzy_match(self, text: str) -> List[Intent]:
        """Fuzzy matching fallback for noisy recognition."""
        candidates = []
        text_words = set(text.split())

        for cmd in CommandRegistry.get_all_commands():
            all_phrases = cmd.trigger_phrases + cmd.aliases
            for phrase in all_phrases:
                phrase_words = set(phrase.lower().split())
                overlap = len(text_words & phrase_words)
                if overlap > 0:
                    score = overlap / max(len(phrase_words | text_words), 1)
                    if score > 0.2:
                        candidates.append(Intent(
                            name=cmd.name,
                            confidence=score * 0.7,
                            category=cmd.category.value,
                            raw_text=text,
                        ))

        return candidates

    def _rescore_with_lm(self, candidates: List[Intent],
                          text: str) -> List[Intent]:
        """Re-score intent candidates using language model."""
        for intent in candidates:
            validation = self.language_model.validate_command(text.split())
            if validation['valid']:
                intent.confidence = min(
                    intent.confidence * 1.1,
                    0.99,
                )
            else:
                intent.confidence *= 0.9

        candidates.sort(key=lambda c: c.confidence, reverse=True)
        return candidates
