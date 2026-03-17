"""
Multi-Keyword Spotter — simultaneous detection of platform command keywords.

Detects action keywords (call, message, send, video, join, leave, mute, etc.)
and maps them to platform operations. Works in conjunction with the wake word
detector to enable the full voice command pipeline.
"""
import numpy as np
import logging
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field

from ..dsp.audio_processor import AudioConfig
from ..dsp.feature_extraction import FeatureExtractor, FeatureConfig

logger = logging.getLogger(__name__)


# Master keyword vocabulary for the Trutim platform
PLATFORM_KEYWORDS = {
    # Wake word
    'trutim': 0,
    # Communication actions
    'call': 1, 'message': 2, 'send': 3, 'video': 4,
    # Room actions
    'join': 5, 'leave': 6, 'create': 7, 'room': 8,
    # Media controls
    'mute': 9, 'unmute': 10, 'camera': 11, 'screen': 12, 'share': 13,
    # Navigation
    'select': 14, 'open': 15, 'close': 16, 'back': 17,
    # User targeting
    'user': 18, 'everyone': 19,
    # Confirmation / negation
    'yes': 20, 'no': 21, 'cancel': 22, 'confirm': 23,
    # Silence / unknown
    '_silence': 24,
}

KEYWORD_LABELS = {v: k for k, v in PLATFORM_KEYWORDS.items()}


@dataclass
class SpotterConfig:
    """Configuration for multi-keyword spotting."""
    confidence_threshold: float = 0.70
    top_k: int = 3
    keyword_window_ms: float = 1000.0
    max_concurrent_keywords: int = 5
    num_mel_bins: int = 80
    target_frames: int = 98
    use_multi_head: bool = True
    command_assembly_timeout_ms: float = 3000.0
    inter_keyword_gap_ms: float = 500.0


@dataclass
class SpottedKeyword:
    """A detected keyword with metadata."""
    keyword: str
    keyword_id: int
    confidence: float
    timestamp_ms: float
    frame_index: int


class KeywordSpotter:
    """
    Multi-keyword spotting engine for platform voice commands.

    Detects multiple keywords in an audio stream and assembles them
    into command sequences. For example:
    - "call user john" -> [call, user, john]
    - "send message hello" -> [send, message]
    - "mute camera" -> [mute, camera]
    - "join room general" -> [join, room, general]

    Uses sliding window analysis with overlapping windows to catch
    keywords at any position in the audio stream.
    """

    def __init__(self, model=None,
                 config: Optional[SpotterConfig] = None,
                 audio_config: Optional[AudioConfig] = None):
        self.config = config or SpotterConfig()
        self.audio_config = audio_config or AudioConfig()
        self.model = model

        self.feature_extractor = FeatureExtractor(
            self.audio_config,
            FeatureConfig(num_mel_bins=self.config.num_mel_bins)
        )

        self._spotted_keywords: List[SpottedKeyword] = []
        self._keyword_buffer: List[SpottedKeyword] = []
        self._last_spot_time = 0.0

    @property
    def vocabulary(self) -> Dict[str, int]:
        return PLATFORM_KEYWORDS

    @property
    def num_keywords(self) -> int:
        return len(PLATFORM_KEYWORDS)

    def spot_keywords(self, signal: np.ndarray,
                      timestamp_offset_ms: float = 0.0) -> List[SpottedKeyword]:
        """
        Detect keywords in an audio signal using sliding windows.
        Returns list of spotted keywords sorted by timestamp.
        """
        features = self.feature_extractor.extract_for_keyword_spotting(signal)
        features = self.feature_extractor.pad_or_truncate_features(
            features, self.config.target_frames
        )

        predictions = self._run_inference(features)
        if predictions is None:
            return []

        spotted = self._decode_predictions(predictions, timestamp_offset_ms)
        self._spotted_keywords.extend(spotted)

        return spotted

    def spot_keywords_streaming(self, window: np.ndarray,
                                 timestamp_ms: float) -> List[SpottedKeyword]:
        """
        Spot keywords in a single streaming window.
        Adds results to the internal keyword buffer for command assembly.
        """
        features = self.feature_extractor.extract_for_keyword_spotting(window)
        features = self.feature_extractor.pad_or_truncate_features(
            features, self.config.target_frames
        )

        predictions = self._run_inference(features)
        if predictions is None:
            return []

        spotted = self._decode_predictions(predictions, timestamp_ms)

        for kw in spotted:
            if not self._is_duplicate(kw):
                self._keyword_buffer.append(kw)

        return spotted

    def assemble_command(self) -> Optional[Dict]:
        """
        Assemble spotted keywords into a command structure.
        Returns a command dict if a valid command sequence is found.
        """
        if not self._keyword_buffer:
            return None

        self._keyword_buffer.sort(key=lambda k: k.timestamp_ms)

        action = None
        target_type = None
        target_value = None
        modifiers = []

        action_keywords = {'call', 'message', 'send', 'video', 'join', 'leave',
                           'create', 'mute', 'unmute', 'select', 'open', 'close',
                           'share', 'back'}
        target_keywords = {'user', 'room', 'everyone'}
        modifier_keywords = {'camera', 'screen', 'video'}

        for kw in self._keyword_buffer:
            word = kw.keyword
            if word in action_keywords and action is None:
                action = word
            elif word in target_keywords:
                target_type = word
            elif word in modifier_keywords:
                modifiers.append(word)
            elif word in ('yes', 'no', 'cancel', 'confirm'):
                if action is None:
                    action = word

        if action is None:
            return None

        command = {
            'action': action,
            'target_type': target_type,
            'target_value': target_value,
            'modifiers': modifiers,
            'keywords': [
                {'keyword': kw.keyword, 'confidence': kw.confidence}
                for kw in self._keyword_buffer
            ],
            'avg_confidence': np.mean([kw.confidence for kw in self._keyword_buffer]),
        }

        self._keyword_buffer.clear()
        return command

    def _run_inference(self, features: np.ndarray) -> Optional[np.ndarray]:
        """Run keyword spotting model inference."""
        if self.model is None:
            return None

        input_data = features[np.newaxis, ...]

        try:
            predictions = self.model.predict(input_data, verbose=0)

            if isinstance(predictions, dict):
                if 'command' in predictions:
                    return predictions['command']
                return predictions.get('predictions', None)

            if isinstance(predictions, (list, tuple)):
                return predictions[0] if len(predictions) > 0 else None

            return predictions
        except Exception as e:
            logger.error("Keyword spotting inference error: %s", e)
            return None

    def _decode_predictions(self, predictions: np.ndarray,
                             timestamp_ms: float) -> List[SpottedKeyword]:
        """Decode model predictions into spotted keywords."""
        if predictions.ndim > 1:
            predictions = predictions[0]

        top_indices = np.argsort(predictions)[::-1][:self.config.top_k]
        spotted = []

        for idx in top_indices:
            confidence = float(predictions[idx])
            if confidence < self.config.confidence_threshold:
                continue

            keyword = KEYWORD_LABELS.get(int(idx), f'_unknown_{idx}')
            if keyword == '_silence':
                continue

            spotted.append(SpottedKeyword(
                keyword=keyword,
                keyword_id=int(idx),
                confidence=confidence,
                timestamp_ms=timestamp_ms,
                frame_index=0,
            ))

        return spotted

    def _is_duplicate(self, keyword: SpottedKeyword) -> bool:
        """Check if a keyword is a duplicate of a recent detection."""
        for existing in self._keyword_buffer[-5:]:
            if (existing.keyword == keyword.keyword and
                    abs(existing.timestamp_ms - keyword.timestamp_ms) <
                    self.config.inter_keyword_gap_ms):
                return True
        return False

    def get_recent_keywords(self, duration_ms: float = 5000.0) -> List[SpottedKeyword]:
        """Get keywords spotted in the last N milliseconds."""
        if not self._spotted_keywords:
            return []
        latest = self._spotted_keywords[-1].timestamp_ms
        cutoff = latest - duration_ms
        return [kw for kw in self._spotted_keywords if kw.timestamp_ms >= cutoff]

    def clear_buffer(self):
        """Clear the keyword assembly buffer."""
        self._keyword_buffer.clear()

    def reset(self):
        """Full reset."""
        self._spotted_keywords.clear()
        self._keyword_buffer.clear()
        self._last_spot_time = 0.0
