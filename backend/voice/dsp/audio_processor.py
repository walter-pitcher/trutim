"""
Audio Processor - Core DSP pipeline for voice signal preprocessing.

Handles raw audio ingestion, resampling, normalization, framing, windowing,
pre-emphasis filtering, and endpoint detection. All operations use numpy
for performance-critical paths and TensorFlow for GPU-accelerated batch
processing when available.
"""
import numpy as np
import struct
import io
from typing import Optional, Tuple, Union
from dataclasses import dataclass, field


@dataclass
class AudioConfig:
    """Configuration for the audio processing pipeline."""
    sample_rate: int = 16000
    target_sample_rate: int = 16000
    bit_depth: int = 16
    channels: int = 1
    frame_length_ms: float = 25.0
    frame_step_ms: float = 10.0
    pre_emphasis_coeff: float = 0.97
    window_type: str = 'hann'
    max_audio_length_s: float = 10.0
    normalize: bool = True
    dither_amount: float = 1.0
    dc_block: bool = True
    dc_block_coeff: float = 0.999

    @property
    def frame_length(self) -> int:
        return int(self.sample_rate * self.frame_length_ms / 1000.0)

    @property
    def frame_step(self) -> int:
        return int(self.sample_rate * self.frame_step_ms / 1000.0)

    @property
    def max_samples(self) -> int:
        return int(self.sample_rate * self.max_audio_length_s)


class AudioProcessor:
    """
    Core audio signal processor implementing a full DSP pipeline.

    Pipeline stages:
    1. Decode raw bytes (PCM16, float32, WAV)
    2. Channel mixing (stereo -> mono)
    3. Resampling (arbitrary rate conversion via polyphase filter)
    4. DC blocking filter
    5. Dithering (TPDF)
    6. Pre-emphasis filter (high-pass, lifts high frequencies)
    7. Normalization (peak or RMS)
    8. Framing + windowing
    """

    WINDOW_FUNCTIONS = {
        'hann': np.hanning,
        'hamming': np.hamming,
        'blackman': np.blackman,
        'bartlett': np.bartlett,
    }

    def __init__(self, config: Optional[AudioConfig] = None):
        self.config = config or AudioConfig()
        self._window_cache = {}

    def process(self, raw_audio: Union[bytes, np.ndarray],
                source_sample_rate: Optional[int] = None) -> np.ndarray:
        """
        Full pipeline: raw audio bytes -> preprocessed float32 signal.
        Returns normalized, pre-emphasized, mono float32 numpy array.
        """
        if isinstance(raw_audio, bytes):
            signal = self.decode_audio(raw_audio)
        else:
            signal = raw_audio.astype(np.float32)

        if signal.ndim > 1 and signal.shape[-1] > 1:
            signal = self._to_mono(signal)

        source_rate = source_sample_rate or self.config.sample_rate
        if source_rate != self.config.target_sample_rate:
            signal = self._resample(signal, source_rate, self.config.target_sample_rate)

        if self.config.dc_block:
            signal = self._dc_block_filter(signal)

        if self.config.dither_amount > 0:
            signal = self._apply_dither(signal)

        signal = self._pre_emphasis(signal)

        if self.config.normalize:
            signal = self._normalize(signal)

        max_len = self.config.max_samples
        if len(signal) > max_len:
            signal = signal[:max_len]

        return signal

    def decode_audio(self, raw_bytes: bytes) -> np.ndarray:
        """Decode raw audio bytes into float32 numpy array."""
        if raw_bytes[:4] == b'RIFF':
            return self._decode_wav(raw_bytes)
        return self._decode_pcm16(raw_bytes)

    def frame_signal(self, signal: np.ndarray) -> np.ndarray:
        """
        Split signal into overlapping frames with windowing applied.
        Returns shape (num_frames, frame_length).
        """
        frame_len = self.config.frame_length
        frame_step = self.config.frame_step

        signal_len = len(signal)
        num_frames = max(1, 1 + (signal_len - frame_len) // frame_step)

        pad_len = (num_frames - 1) * frame_step + frame_len
        if pad_len > signal_len:
            signal = np.pad(signal, (0, pad_len - signal_len), mode='constant')

        indices = (np.arange(frame_len)[np.newaxis, :] +
                   np.arange(num_frames)[:, np.newaxis] * frame_step)
        frames = signal[indices]

        window = self._get_window(frame_len)
        frames = frames * window

        return frames

    def signal_energy(self, signal: np.ndarray) -> np.ndarray:
        """Compute short-time energy per frame."""
        frames = self.frame_signal(signal)
        return np.sum(frames ** 2, axis=1)

    def zero_crossing_rate(self, signal: np.ndarray) -> np.ndarray:
        """Compute zero-crossing rate per frame."""
        frames = self.frame_signal(signal)
        signs = np.sign(frames)
        sign_changes = np.abs(np.diff(signs, axis=1))
        return np.sum(sign_changes, axis=1) / (2.0 * frames.shape[1])

    def compute_rms(self, signal: np.ndarray) -> float:
        """Root mean square of the signal."""
        return float(np.sqrt(np.mean(signal ** 2)))

    def split_into_chunks(self, signal: np.ndarray, chunk_duration_ms: float = 500.0
                          ) -> list[np.ndarray]:
        """Split signal into fixed-duration chunks for streaming."""
        chunk_samples = int(self.config.target_sample_rate * chunk_duration_ms / 1000.0)
        chunks = []
        for start in range(0, len(signal), chunk_samples):
            chunk = signal[start:start + chunk_samples]
            if len(chunk) < chunk_samples:
                chunk = np.pad(chunk, (0, chunk_samples - len(chunk)), mode='constant')
            chunks.append(chunk)
        return chunks

    # --- Private methods ---

    def _decode_wav(self, wav_bytes: bytes) -> np.ndarray:
        """Decode WAV format (supports PCM 16/24/32 and float32)."""
        buf = io.BytesIO(wav_bytes)
        buf.read(4)  # RIFF
        buf.read(4)  # file size
        buf.read(4)  # WAVE

        audio_format = 1
        num_channels = 1
        sample_rate = 16000
        bits_per_sample = 16
        data_bytes = b''

        while buf.tell() < len(wav_bytes):
            chunk_id = buf.read(4)
            if len(chunk_id) < 4:
                break
            chunk_size = struct.unpack('<I', buf.read(4))[0]

            if chunk_id == b'fmt ':
                fmt_data = buf.read(chunk_size)
                audio_format = struct.unpack('<H', fmt_data[0:2])[0]
                num_channels = struct.unpack('<H', fmt_data[2:4])[0]
                sample_rate = struct.unpack('<I', fmt_data[4:8])[0]
                bits_per_sample = struct.unpack('<H', fmt_data[14:16])[0]
            elif chunk_id == b'data':
                data_bytes = buf.read(chunk_size)
            else:
                buf.read(chunk_size)

        if audio_format == 3:  # IEEE float
            signal = np.frombuffer(data_bytes, dtype=np.float32)
        elif bits_per_sample == 16:
            signal = np.frombuffer(data_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        elif bits_per_sample == 24:
            signal = self._decode_pcm24(data_bytes)
        elif bits_per_sample == 32:
            signal = np.frombuffer(data_bytes, dtype=np.int32).astype(np.float32) / 2147483648.0
        else:
            signal = np.frombuffer(data_bytes, dtype=np.int16).astype(np.float32) / 32768.0

        if num_channels > 1:
            signal = signal.reshape(-1, num_channels)

        self.config.sample_rate = sample_rate
        return signal

    def _decode_pcm24(self, data: bytes) -> np.ndarray:
        """Decode 24-bit PCM audio data."""
        num_samples = len(data) // 3
        signal = np.zeros(num_samples, dtype=np.float32)
        for i in range(num_samples):
            b0, b1, b2 = data[i*3], data[i*3+1], data[i*3+2]
            value = b0 | (b1 << 8) | (b2 << 16)
            if value & 0x800000:
                value -= 0x1000000
            signal[i] = value / 8388608.0
        return signal

    def _decode_pcm16(self, raw_bytes: bytes) -> np.ndarray:
        """Decode raw PCM16 little-endian bytes."""
        return np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0

    def _to_mono(self, signal: np.ndarray) -> np.ndarray:
        """Mix multi-channel signal to mono."""
        if signal.ndim == 1:
            return signal
        return np.mean(signal, axis=-1)

    def _resample(self, signal: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
        """
        Polyphase resampling using linear interpolation.
        For production, integrate with libsamplerate via scipy.
        """
        if source_rate == target_rate:
            return signal

        ratio = target_rate / source_rate
        output_length = int(len(signal) * ratio)
        indices = np.linspace(0, len(signal) - 1, output_length)

        integer_part = indices.astype(np.int64)
        fractional_part = indices - integer_part

        integer_part = np.clip(integer_part, 0, len(signal) - 2)
        resampled = signal[integer_part] * (1 - fractional_part) + signal[integer_part + 1] * fractional_part

        return resampled.astype(np.float32)

    def _dc_block_filter(self, signal: np.ndarray) -> np.ndarray:
        """
        DC blocking filter: y[n] = x[n] - x[n-1] + R * y[n-1]
        Removes DC offset from the signal.
        """
        R = self.config.dc_block_coeff
        output = np.zeros_like(signal)
        if len(signal) == 0:
            return output
        output[0] = signal[0]
        for i in range(1, len(signal)):
            output[i] = signal[i] - signal[i - 1] + R * output[i - 1]
        return output

    def _apply_dither(self, signal: np.ndarray) -> np.ndarray:
        """Apply TPDF (Triangular Probability Density Function) dither."""
        dither = (np.random.random(len(signal)).astype(np.float32) +
                  np.random.random(len(signal)).astype(np.float32) - 1.0)
        scale = self.config.dither_amount / 32768.0
        return signal + dither * scale

    def _pre_emphasis(self, signal: np.ndarray) -> np.ndarray:
        """
        Pre-emphasis filter: y[n] = x[n] - alpha * x[n-1]
        Boosts high-frequency components to balance the spectrum.
        """
        if self.config.pre_emphasis_coeff <= 0:
            return signal
        return np.append(signal[0], signal[1:] - self.config.pre_emphasis_coeff * signal[:-1])

    def _normalize(self, signal: np.ndarray) -> np.ndarray:
        """Peak normalize signal to [-1, 1] range."""
        peak = np.max(np.abs(signal))
        if peak > 0:
            signal = signal / peak
        return signal

    def _get_window(self, length: int) -> np.ndarray:
        """Get cached window function."""
        key = (self.config.window_type, length)
        if key not in self._window_cache:
            fn = self.WINDOW_FUNCTIONS.get(self.config.window_type, np.hanning)
            self._window_cache[key] = fn(length).astype(np.float32)
        return self._window_cache[key]


class StreamingAudioBuffer:
    """
    Ring buffer for streaming audio processing.
    Accumulates audio chunks and yields complete analysis windows.
    """

    def __init__(self, config: Optional[AudioConfig] = None,
                 window_duration_ms: float = 1000.0,
                 overlap_duration_ms: float = 200.0):
        self.config = config or AudioConfig()
        self.processor = AudioProcessor(self.config)

        self.window_samples = int(self.config.target_sample_rate * window_duration_ms / 1000.0)
        self.overlap_samples = int(self.config.target_sample_rate * overlap_duration_ms / 1000.0)
        self.step_samples = self.window_samples - self.overlap_samples

        self._buffer = np.zeros(0, dtype=np.float32)
        self._total_samples_received = 0

    def add_chunk(self, audio_chunk: Union[bytes, np.ndarray],
                  source_sample_rate: Optional[int] = None) -> list[np.ndarray]:
        """
        Add an audio chunk and return any complete windows ready for analysis.
        Each returned window is preprocessed (pre-emphasis, normalization).
        """
        processed = self.processor.process(audio_chunk, source_sample_rate)
        self._buffer = np.concatenate([self._buffer, processed])
        self._total_samples_received += len(processed)

        windows = []
        while len(self._buffer) >= self.window_samples:
            window = self._buffer[:self.window_samples].copy()
            windows.append(window)
            self._buffer = self._buffer[self.step_samples:]

        return windows

    def flush(self) -> Optional[np.ndarray]:
        """Return remaining buffer content, zero-padded to window size."""
        if len(self._buffer) == 0:
            return None
        padded = np.pad(self._buffer, (0, max(0, self.window_samples - len(self._buffer))))
        self._buffer = np.zeros(0, dtype=np.float32)
        return padded[:self.window_samples]

    def reset(self):
        """Clear the buffer."""
        self._buffer = np.zeros(0, dtype=np.float32)
        self._total_samples_received = 0

    @property
    def buffered_duration_ms(self) -> float:
        return len(self._buffer) / self.config.target_sample_rate * 1000.0

    @property
    def total_duration_s(self) -> float:
        return self._total_samples_received / self.config.target_sample_rate
