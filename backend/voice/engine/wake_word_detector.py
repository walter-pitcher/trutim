"""
Wake Word Detector — real-time "Trutim" wake word detection.

Implements a streaming detection pipeline that continuously monitors
audio for the wake word "Trutim" using a trained deep learning model.
Includes smoothing, debouncing, and confidence thresholding.
"""
import numpy as np
import time
import logging
from typing import Optional, Callable, Tuple, List
from dataclasses import dataclass, field
from enum import IntEnum

from ..dsp.audio_processor import AudioConfig, StreamingAudioBuffer
from ..dsp.feature_extraction import FeatureExtractor, FeatureConfig
from ..dsp.noise_reduction import VoiceActivityDetector, VADState

logger = logging.getLogger(__name__)


class DetectorState(IntEnum):
    IDLE = 0
    LISTENING = 1
    WAKE_WORD_DETECTED = 2
    COMMAND_LISTENING = 3


@dataclass
class WakeWordConfig:
    """Configuration for wake word detection."""
    wake_word: str = 'trutim'
    confidence_threshold: float = 0.85
    smoothing_window: int = 3
    debounce_ms: float = 2000.0
    detection_window_ms: float = 1500.0
    command_timeout_ms: float = 5000.0
    max_false_triggers_per_min: int = 3
    use_vad_gating: bool = True
    min_audio_energy: float = 0.001
    num_mel_bins: int = 80
    target_frames: int = 98


class WakeWordDetector:
    """
    Real-time wake word detection engine.

    Pipeline:
    1. Stream audio through ring buffer
    2. Voice Activity Detection gates processing
    3. Feature extraction (log mel spectrogram)
    4. Model inference (DS-CNN or chosen architecture)
    5. Smoothing + confidence thresholding
    6. Debouncing to prevent rapid re-triggering
    7. Callback invocation on detection

    Supports both streaming (frame-by-frame) and batch modes.
    """

    def __init__(self, model=None,
                 wake_config: Optional[WakeWordConfig] = None,
                 audio_config: Optional[AudioConfig] = None):
        self.wake_config = wake_config or WakeWordConfig()
        self.audio_config = audio_config or AudioConfig()

        self.model = model
        self.feature_extractor = FeatureExtractor(
            self.audio_config,
            FeatureConfig(num_mel_bins=self.wake_config.num_mel_bins)
        )
        self.vad = VoiceActivityDetector(self.audio_config)
        self.audio_buffer = StreamingAudioBuffer(
            self.audio_config,
            window_duration_ms=self.wake_config.detection_window_ms,
            overlap_duration_ms=200.0,
        )

        self._state = DetectorState.IDLE
        self._confidence_history: List[float] = []
        self._last_detection_time = 0.0
        self._detection_count_window: List[float] = []
        self._callbacks: List[Callable] = []
        self._command_start_time = 0.0

    @property
    def state(self) -> DetectorState:
        return self._state

    def start(self):
        """Start the detector — transitions to LISTENING state."""
        self._state = DetectorState.LISTENING
        self.audio_buffer.reset()
        self.vad.reset()
        self._confidence_history.clear()
        logger.info("Wake word detector started, listening for '%s'",
                     self.wake_config.wake_word)

    def stop(self):
        """Stop the detector."""
        self._state = DetectorState.IDLE
        logger.info("Wake word detector stopped")

    def register_callback(self, callback: Callable):
        """Register a callback for wake word detection events."""
        self._callbacks.append(callback)

    def process_audio_chunk(self, audio_chunk: bytes,
                             source_sample_rate: Optional[int] = None
                             ) -> Optional[dict]:
        """
        Process an audio chunk in streaming mode.
        Returns detection result dict if wake word is detected, else None.
        """
        if self._state == DetectorState.IDLE:
            return None

        windows = self.audio_buffer.add_chunk(audio_chunk, source_sample_rate)
        if not windows:
            return None

        for window in windows:
            result = self._analyze_window(window)
            if result is not None:
                return result

        return None

    def process_audio_batch(self, signal: np.ndarray) -> List[dict]:
        """
        Process a complete audio signal in batch mode.
        Returns list of all detections with timestamps.
        """
        detections = []
        chunks = self.audio_buffer.processor.split_into_chunks(
            signal, chunk_duration_ms=500.0
        )

        self.start()
        for i, chunk in enumerate(chunks):
            windows = self.audio_buffer.add_chunk(chunk)
            for window in windows:
                result = self._analyze_window(window)
                if result:
                    result['chunk_index'] = i
                    detections.append(result)

        return detections

    def _analyze_window(self, window: np.ndarray) -> Optional[dict]:
        """Analyze a single audio window for wake word presence."""
        if self.wake_config.use_vad_gating:
            energy = np.mean(window ** 2)
            if energy < self.wake_config.min_audio_energy:
                return None

            speech_segments = self.vad.detect(window)
            if not speech_segments:
                return None

        features = self.feature_extractor.extract_for_keyword_spotting(window)
        features = self.feature_extractor.pad_or_truncate_features(
            features, self.wake_config.target_frames
        )

        confidence = self._run_inference(features)

        self._confidence_history.append(confidence)
        if len(self._confidence_history) > self.wake_config.smoothing_window:
            self._confidence_history.pop(0)

        smoothed_confidence = np.mean(self._confidence_history)

        if smoothed_confidence >= self.wake_config.confidence_threshold:
            return self._handle_detection(smoothed_confidence)

        return None

    def _run_inference(self, features: np.ndarray) -> float:
        """Run model inference on extracted features."""
        if self.model is None:
            return 0.0

        input_data = features[np.newaxis, ...]  # Add batch dimension

        try:
            predictions = self.model.predict(input_data, verbose=0)

            if isinstance(predictions, dict):
                wake_word_prob = float(predictions['wake_word'][0, 0])
            elif isinstance(predictions, (list, tuple)):
                wake_word_prob = float(predictions[0][0, 0])
            else:
                wake_word_prob = float(predictions[0, 0])

            return wake_word_prob
        except Exception as e:
            logger.error("Inference error: %s", e)
            return 0.0

    def _handle_detection(self, confidence: float) -> Optional[dict]:
        """Handle a wake word detection event with debouncing."""
        now = time.time() * 1000.0

        if now - self._last_detection_time < self.wake_config.debounce_ms:
            return None

        self._detection_count_window = [
            t for t in self._detection_count_window if now - t < 60000.0
        ]
        if len(self._detection_count_window) >= self.wake_config.max_false_triggers_per_min:
            logger.warning("Too many detections — possible false trigger loop")
            return None

        self._last_detection_time = now
        self._detection_count_window.append(now)
        self._state = DetectorState.WAKE_WORD_DETECTED
        self._command_start_time = now
        self._confidence_history.clear()

        result = {
            'event': 'wake_word_detected',
            'wake_word': self.wake_config.wake_word,
            'confidence': confidence,
            'timestamp': now,
            'state': 'command_listening',
        }

        for callback in self._callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.error("Callback error: %s", e)

        self._state = DetectorState.COMMAND_LISTENING
        logger.info("Wake word '%s' detected (confidence: %.3f)",
                     self.wake_config.wake_word, confidence)
        return result

    def check_command_timeout(self) -> bool:
        """Check if command listening has timed out."""
        if self._state != DetectorState.COMMAND_LISTENING:
            return False

        now = time.time() * 1000.0
        if now - self._command_start_time > self.wake_config.command_timeout_ms:
            self._state = DetectorState.LISTENING
            logger.info("Command timeout — returning to listening mode")
            return True
        return False

    def return_to_listening(self):
        """Return to listening state after command processing."""
        self._state = DetectorState.LISTENING
        self._confidence_history.clear()
        self.vad.reset()

    def get_status(self) -> dict:
        return {
            'state': self._state.name,
            'wake_word': self.wake_config.wake_word,
            'confidence_threshold': self.wake_config.confidence_threshold,
            'total_audio_processed_s': self.audio_buffer.total_duration_s,
            'detections_last_minute': len(self._detection_count_window),
        }
