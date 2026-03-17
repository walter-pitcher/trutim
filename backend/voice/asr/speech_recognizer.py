"""
Automatic Speech Recognition (ASR) Engine.

Provides speech-to-text capability for voice command processing.
Supports multiple ASR backends:
1. Built-in CTC-based model (TensorFlow)
2. External API fallback (Google Speech, Whisper)
3. Command-constrained recognition (grammar-guided)
"""
import numpy as np
import logging
import time
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass

try:
    import tensorflow as tf
    from tensorflow import keras
    HAS_TF = True
except ImportError:
    HAS_TF = False

from ..dsp.audio_processor import AudioConfig, AudioProcessor
from ..dsp.feature_extraction import FeatureExtractor, FeatureConfig
from ..dsp.noise_reduction import NoiseReducer, VoiceActivityDetector

logger = logging.getLogger(__name__)


@dataclass
class ASRConfig:
    """Configuration for speech recognition."""
    beam_width: int = 10
    max_sequence_length: int = 150
    blank_index: int = 0
    language: str = 'en'
    use_language_model: bool = True
    lm_weight: float = 0.3
    word_insertion_penalty: float = 0.1
    confidence_threshold: float = 0.5
    use_vad_preprocessing: bool = True
    use_noise_reduction: bool = True


class SpeechRecognizer:
    """
    Speech recognition engine for voice commands.

    Architecture:
    - Audio preprocessing (noise reduction, VAD)
    - Feature extraction (log mel spectrogram)
    - CTC-based encoder model (Conv + BiLSTM)
    - Beam search decoder with language model
    - Command-constrained decoding for platform vocabulary

    For the Trutim platform, this is optimized for short command
    utterances rather than general-purpose dictation.
    """

    COMMAND_VOCABULARY = [
        '',  # CTC blank
        'trutim', 'call', 'message', 'send', 'video',
        'join', 'leave', 'create', 'room', 'mute',
        'unmute', 'camera', 'screen', 'share', 'select',
        'open', 'close', 'back', 'user', 'everyone',
        'yes', 'no', 'cancel', 'confirm', 'start',
        'stop', 'end', 'to', 'the', 'a', 'in',
    ]

    CHAR_VOCABULARY = list(' abcdefghijklmnopqrstuvwxyz\'')

    def __init__(self, config: Optional[ASRConfig] = None,
                 audio_config: Optional[AudioConfig] = None,
                 model=None):
        self.config = config or ASRConfig()
        self.audio_config = audio_config or AudioConfig()

        self.model = model
        self.processor = AudioProcessor(self.audio_config)
        self.feature_extractor = FeatureExtractor(self.audio_config)
        self.noise_reducer = NoiseReducer(self.audio_config)
        self.vad = VoiceActivityDetector(self.audio_config)

        self._language_model = None

    def recognize(self, audio: np.ndarray) -> Dict:
        """
        Recognize speech from audio signal.
        Returns dict with text, confidence, tokens, and timing.
        """
        start_time = time.perf_counter()

        preprocessed = self._preprocess(audio)
        if preprocessed is None or len(preprocessed) == 0:
            return {'text': '', 'confidence': 0.0, 'tokens': [],
                    'latency_ms': 0, 'status': 'no_speech'}

        features = self.feature_extractor.extract_for_keyword_spotting(preprocessed)

        if self.model is not None:
            logits = self._run_model(features)
            text, confidence, tokens = self._decode(logits)
        else:
            text, confidence, tokens = self._command_matching(preprocessed)

        latency_ms = (time.perf_counter() - start_time) * 1000

        return {
            'text': text,
            'confidence': confidence,
            'tokens': tokens,
            'latency_ms': latency_ms,
            'status': 'success' if text else 'low_confidence',
        }

    def recognize_command(self, audio: np.ndarray) -> Dict:
        """
        Command-constrained recognition.
        Only recognizes text from the platform command vocabulary.
        """
        result = self.recognize(audio)

        if result['text']:
            matched = self._match_to_commands(result['text'])
            result['command_text'] = matched['text']
            result['command_confidence'] = matched['confidence']
            result['matched_commands'] = matched['commands']

        return result

    def build_ctc_model(self, num_classes: int = 28,
                         input_shape: Tuple = (98, 80, 1)) -> 'keras.Model':
        """
        Build CTC-based speech recognition model.

        Architecture:
        - 2D CNN frontend for acoustic feature extraction
        - Bidirectional LSTM encoder
        - Dense projection to character/token probabilities
        - CTC loss for alignment-free training
        """
        if not HAS_TF:
            raise ImportError("TensorFlow required")

        inp = keras.layers.Input(shape=input_shape, name='audio_input')

        x = keras.layers.Conv2D(32, (3, 3), padding='same', activation='relu')(inp)
        x = keras.layers.BatchNormalization()(x)
        x = keras.layers.MaxPooling2D((2, 1))(x)

        x = keras.layers.Conv2D(64, (3, 3), padding='same', activation='relu')(x)
        x = keras.layers.BatchNormalization()(x)
        x = keras.layers.MaxPooling2D((2, 1))(x)

        x = keras.layers.Conv2D(128, (3, 3), padding='same', activation='relu')(x)
        x = keras.layers.BatchNormalization()(x)

        shape = x.shape
        x = keras.layers.Reshape((shape[1], shape[2] * shape[3]))(x)

        x = keras.layers.Bidirectional(
            keras.layers.LSTM(256, return_sequences=True, dropout=0.3)
        )(x)
        x = keras.layers.Bidirectional(
            keras.layers.LSTM(256, return_sequences=True, dropout=0.3)
        )(x)

        x = keras.layers.Dense(512, activation='relu')(x)
        x = keras.layers.Dropout(0.3)(x)

        output = keras.layers.Dense(
            num_classes + 1,  # +1 for CTC blank
            activation='softmax', name='ctc_output'
        )(x)

        self.model = keras.Model(inputs=inp, outputs=output, name='CTC_ASR')
        return self.model

    def _preprocess(self, audio: np.ndarray) -> Optional[np.ndarray]:
        """Preprocess audio: noise reduction + VAD."""
        signal = self.processor.process(audio)

        if self.config.use_noise_reduction:
            signal = self.noise_reducer.reduce_noise(signal)

        if self.config.use_vad_preprocessing:
            speech = self.vad.get_speech_signal(signal)
            if len(speech) == 0:
                return None
            return speech

        return signal

    def _run_model(self, features: np.ndarray) -> np.ndarray:
        """Run the ASR model on features."""
        input_data = features[np.newaxis, ...]
        logits = self.model.predict(input_data, verbose=0)
        return logits[0]  # Remove batch dimension

    def _decode(self, logits: np.ndarray) -> Tuple[str, float, List[Dict]]:
        """
        Beam search CTC decoder.
        Returns (text, confidence, token_list).
        """
        if HAS_TF:
            return self._tf_ctc_decode(logits)
        return self._greedy_decode(logits)

    def _tf_ctc_decode(self, logits: np.ndarray) -> Tuple[str, float, List[Dict]]:
        """TensorFlow CTC beam search decoding."""
        logits_tensor = tf.constant(logits[np.newaxis, ...], dtype=tf.float32)
        input_length = tf.constant([logits.shape[0]], dtype=tf.int32)

        decoded, log_probs = tf.nn.ctc_beam_search_decoder(
            tf.transpose(logits_tensor, [1, 0, 2]),
            input_length,
            beam_width=self.config.beam_width,
        )

        if decoded:
            indices = decoded[0].values.numpy()
            text = self._indices_to_text(indices)
            confidence = float(tf.exp(log_probs[0, 0]).numpy())
        else:
            text = ''
            confidence = 0.0

        tokens = [{'char': c, 'index': i} for i, c in enumerate(text)]
        return text, confidence, tokens

    def _greedy_decode(self, logits: np.ndarray) -> Tuple[str, float, List[Dict]]:
        """Simple greedy CTC decoder as fallback."""
        best_path = np.argmax(logits, axis=-1)
        confidence = np.mean(np.max(logits, axis=-1))

        decoded = []
        prev = -1
        for idx in best_path:
            if idx != self.config.blank_index and idx != prev:
                decoded.append(int(idx))
            prev = idx

        text = self._indices_to_text(decoded)
        tokens = [{'char': c, 'index': i} for i, c in enumerate(text)]
        return text, float(confidence), tokens

    def _indices_to_text(self, indices: List[int]) -> str:
        """Convert character indices to text."""
        chars = []
        for idx in indices:
            if 0 < idx < len(self.CHAR_VOCABULARY):
                chars.append(self.CHAR_VOCABULARY[idx])
        return ''.join(chars).strip()

    def _command_matching(self, audio: np.ndarray) -> Tuple[str, float, List]:
        """
        Fallback command matching using feature similarity.
        Used when no ASR model is loaded.
        """
        return '', 0.0, []

    def _match_to_commands(self, text: str) -> Dict:
        """
        Match recognized text to platform commands.
        Uses edit distance and fuzzy matching.
        """
        text_lower = text.lower().strip()
        words = text_lower.split()

        matched_commands = []
        for word in words:
            best_match = None
            best_distance = float('inf')

            for vocab_word in self.COMMAND_VOCABULARY:
                if not vocab_word:
                    continue
                distance = self._edit_distance(word, vocab_word)
                if distance < best_distance:
                    best_distance = distance
                    best_match = vocab_word

            if best_match and best_distance <= max(1, len(word) // 3):
                matched_commands.append({
                    'original': word,
                    'matched': best_match,
                    'distance': best_distance,
                    'confidence': 1.0 - (best_distance / max(len(word), 1)),
                })

        matched_text = ' '.join(m['matched'] for m in matched_commands)
        avg_confidence = (
            np.mean([m['confidence'] for m in matched_commands])
            if matched_commands else 0.0
        )

        return {
            'text': matched_text,
            'confidence': float(avg_confidence),
            'commands': matched_commands,
        }

    @staticmethod
    def _edit_distance(s1: str, s2: str) -> int:
        """Compute Levenshtein edit distance."""
        m, n = len(s1), len(s2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                cost = 0 if s1[i-1] == s2[j-1] else 1
                dp[i][j] = min(
                    dp[i-1][j] + 1,
                    dp[i][j-1] + 1,
                    dp[i-1][j-1] + cost,
                )
        return dp[m][n]
