"""
Noise Reduction & Voice Activity Detection (VAD).

Implements spectral subtraction noise reduction, Wiener filtering,
and energy/zero-crossing based VAD with adaptive thresholds.
"""
import numpy as np
from typing import Optional, Tuple, List
from dataclasses import dataclass
from enum import IntEnum

from .audio_processor import AudioConfig, AudioProcessor


class VADState(IntEnum):
    SILENCE = 0
    SPEECH_START = 1
    SPEECH = 2
    SPEECH_END = 3


@dataclass
class NoiseConfig:
    """Configuration for noise reduction."""
    spectral_floor: float = 0.002
    oversubtraction: float = 1.5
    noise_estimation_frames: int = 30
    smoothing_alpha: float = 0.98
    wiener_beta: float = 0.02


@dataclass
class VADConfig:
    """Configuration for Voice Activity Detection."""
    energy_threshold_db: float = -35.0
    zcr_threshold: float = 0.15
    min_speech_duration_ms: float = 200.0
    min_silence_duration_ms: float = 300.0
    speech_pad_ms: float = 100.0
    adaptive_threshold: bool = True
    adaptive_alpha: float = 0.95
    hangover_frames: int = 10


class NoiseReducer:
    """
    Multi-stage noise reduction pipeline.

    1. Noise profile estimation from initial silence
    2. Spectral subtraction (power spectrum domain)
    3. Wiener filtering for residual noise
    4. Spectral smoothing to reduce musical noise artifacts
    """

    def __init__(self, audio_config: Optional[AudioConfig] = None,
                 noise_config: Optional[NoiseConfig] = None):
        self.audio_config = audio_config or AudioConfig()
        self.noise_config = noise_config or NoiseConfig()
        self.processor = AudioProcessor(self.audio_config)

        self._noise_profile = None
        self._prev_magnitude = None

    def reduce_noise(self, signal: np.ndarray,
                     noise_sample: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Full noise reduction pipeline.
        If noise_sample is provided, uses it to estimate noise profile.
        Otherwise estimates from the first N frames of the signal.
        """
        frames = self.processor.frame_signal(signal)
        fft_size = max(512, 2 ** int(np.ceil(np.log2(frames.shape[1]))))

        spectra = np.fft.rfft(frames, n=fft_size)
        magnitude = np.abs(spectra)
        phase = np.angle(spectra)

        if noise_sample is not None:
            self._estimate_noise_profile(noise_sample, fft_size)
        elif self._noise_profile is None:
            n_est = min(self.noise_config.noise_estimation_frames, len(frames))
            noise_mag = np.mean(magnitude[:n_est], axis=0)
            self._noise_profile = noise_mag ** 2

        cleaned_magnitude = self._spectral_subtraction(magnitude)
        cleaned_magnitude = self._wiener_filter(cleaned_magnitude, magnitude)
        cleaned_magnitude = self._spectral_smoothing(cleaned_magnitude)

        cleaned_spectra = cleaned_magnitude * np.exp(1j * phase)
        cleaned_frames = np.fft.irfft(cleaned_spectra, n=fft_size)[:, :frames.shape[1]]

        return self._overlap_add(cleaned_frames, len(signal))

    def _estimate_noise_profile(self, noise_sample: np.ndarray, fft_size: int):
        """Estimate noise power spectrum from a noise-only sample."""
        frames = self.processor.frame_signal(noise_sample)
        spectra = np.fft.rfft(frames, n=fft_size)
        self._noise_profile = np.mean(np.abs(spectra) ** 2, axis=0)

    def _spectral_subtraction(self, magnitude: np.ndarray) -> np.ndarray:
        """
        Power spectral subtraction:
        |Y(f)|^2 = max(|X(f)|^2 - alpha * |N(f)|^2, beta * |N(f)|^2)
        """
        if self._noise_profile is None:
            return magnitude

        power = magnitude ** 2
        noise_power = self._noise_profile
        alpha = self.noise_config.oversubtraction

        min_bins = min(power.shape[1], noise_power.shape[0])
        noise_power = noise_power[:min_bins]

        cleaned_power = np.maximum(
            power[:, :min_bins] - alpha * noise_power,
            self.noise_config.spectral_floor * noise_power,
        )

        result = np.zeros_like(magnitude)
        result[:, :min_bins] = np.sqrt(cleaned_power)
        return result

    def _wiener_filter(self, cleaned_magnitude: np.ndarray,
                       original_magnitude: np.ndarray) -> np.ndarray:
        """
        Wiener filter for residual noise suppression.
        H(f) = |S(f)|^2 / (|S(f)|^2 + beta * |N(f)|^2)
        """
        if self._noise_profile is None:
            return cleaned_magnitude

        noise_power = self._noise_profile
        min_bins = min(cleaned_magnitude.shape[1], noise_power.shape[0])

        signal_power = cleaned_magnitude[:, :min_bins] ** 2
        wiener_gain = signal_power / (
            signal_power + self.noise_config.wiener_beta * noise_power[:min_bins] + 1e-10
        )

        result = np.zeros_like(cleaned_magnitude)
        result[:, :min_bins] = cleaned_magnitude[:, :min_bins] * wiener_gain
        return result

    def _spectral_smoothing(self, magnitude: np.ndarray) -> np.ndarray:
        """Temporal smoothing to reduce musical noise."""
        alpha = self.noise_config.smoothing_alpha
        smoothed = np.copy(magnitude)
        for i in range(1, len(smoothed)):
            smoothed[i] = alpha * smoothed[i - 1] + (1 - alpha) * smoothed[i]
        return smoothed

    def _overlap_add(self, frames: np.ndarray, target_length: int) -> np.ndarray:
        """Reconstruct signal from overlapping frames via overlap-add."""
        frame_step = self.audio_config.frame_step
        frame_len = frames.shape[1]

        output_length = (len(frames) - 1) * frame_step + frame_len
        output = np.zeros(output_length, dtype=np.float32)
        window_sum = np.zeros(output_length, dtype=np.float32)

        window = np.hanning(frame_len).astype(np.float32)

        for i, frame in enumerate(frames):
            start = i * frame_step
            end = start + frame_len
            output[start:end] += frame * window
            window_sum[start:end] += window ** 2

        nonzero = window_sum > 1e-10
        output[nonzero] /= window_sum[nonzero]

        return output[:target_length]

    def reset(self):
        """Reset noise profile for new audio stream."""
        self._noise_profile = None
        self._prev_magnitude = None


class VoiceActivityDetector:
    """
    Voice Activity Detection using multiple features.

    Combines energy-based detection, zero-crossing rate analysis,
    and spectral features with adaptive thresholds and hangover
    logic for robust speech boundary detection.
    """

    def __init__(self, audio_config: Optional[AudioConfig] = None,
                 vad_config: Optional[VADConfig] = None):
        self.audio_config = audio_config or AudioConfig()
        self.vad_config = vad_config or VADConfig()
        self.processor = AudioProcessor(self.audio_config)

        self._energy_threshold = 10 ** (self.vad_config.energy_threshold_db / 10.0)
        self._state = VADState.SILENCE
        self._hangover_counter = 0
        self._speech_counter = 0
        self._silence_counter = 0
        self._running_mean_energy = 0.0
        self._frame_count = 0

    def detect(self, signal: np.ndarray) -> List[Tuple[int, int]]:
        """
        Detect speech segments in the signal.
        Returns list of (start_sample, end_sample) tuples.
        """
        frame_energies = self.processor.signal_energy(signal)
        frame_zcrs = self.processor.zero_crossing_rate(signal)

        frame_step = self.audio_config.frame_step
        min_speech_frames = int(
            self.vad_config.min_speech_duration_ms / self.audio_config.frame_step_ms
        )
        min_silence_frames = int(
            self.vad_config.min_silence_duration_ms / self.audio_config.frame_step_ms
        )
        pad_frames = int(
            self.vad_config.speech_pad_ms / self.audio_config.frame_step_ms
        )

        speech_flags = np.zeros(len(frame_energies), dtype=bool)

        for i in range(len(frame_energies)):
            energy = frame_energies[i]
            zcr = frame_zcrs[i]

            if self.vad_config.adaptive_threshold:
                self._update_threshold(energy)

            is_speech_frame = (
                energy > self._energy_threshold and
                zcr < self.vad_config.zcr_threshold
            )

            new_state = self._state_machine(is_speech_frame, min_speech_frames, min_silence_frames)
            speech_flags[i] = new_state in (VADState.SPEECH_START, VADState.SPEECH)

        segments = self._extract_segments(speech_flags, frame_step, pad_frames, len(signal))
        return segments

    def detect_streaming(self, frame_energy: float, frame_zcr: float) -> VADState:
        """
        Single-frame VAD for streaming mode.
        Returns current VAD state.
        """
        if self.vad_config.adaptive_threshold:
            self._update_threshold(frame_energy)

        is_speech = (
            frame_energy > self._energy_threshold and
            frame_zcr < self.vad_config.zcr_threshold
        )

        min_speech_frames = int(
            self.vad_config.min_speech_duration_ms / self.audio_config.frame_step_ms
        )
        min_silence_frames = int(
            self.vad_config.min_silence_duration_ms / self.audio_config.frame_step_ms
        )

        return self._state_machine(is_speech, min_speech_frames, min_silence_frames)

    def get_speech_signal(self, signal: np.ndarray) -> np.ndarray:
        """Extract only the speech portions of the signal, concatenated."""
        segments = self.detect(signal)
        if not segments:
            return np.array([], dtype=np.float32)
        return np.concatenate([signal[start:end] for start, end in segments])

    def _state_machine(self, is_speech_frame: bool,
                       min_speech: int, min_silence: int) -> VADState:
        """Finite state machine for VAD with hangover logic."""
        if self._state == VADState.SILENCE:
            if is_speech_frame:
                self._speech_counter += 1
                if self._speech_counter >= min_speech:
                    self._state = VADState.SPEECH_START
                    self._hangover_counter = self.vad_config.hangover_frames
                    self._silence_counter = 0
            else:
                self._speech_counter = 0

        elif self._state in (VADState.SPEECH_START, VADState.SPEECH):
            self._state = VADState.SPEECH
            if is_speech_frame:
                self._hangover_counter = self.vad_config.hangover_frames
                self._silence_counter = 0
            else:
                self._hangover_counter -= 1
                self._silence_counter += 1
                if self._hangover_counter <= 0 and self._silence_counter >= min_silence:
                    self._state = VADState.SPEECH_END
                    self._speech_counter = 0

        elif self._state == VADState.SPEECH_END:
            self._state = VADState.SILENCE
            self._speech_counter = 0

        return self._state

    def _update_threshold(self, energy: float):
        """Adaptive threshold using exponential moving average."""
        self._frame_count += 1
        alpha = self.vad_config.adaptive_alpha
        self._running_mean_energy = alpha * self._running_mean_energy + (1 - alpha) * energy

        noise_floor = self._running_mean_energy
        self._energy_threshold = max(
            noise_floor * 10.0,
            10 ** (self.vad_config.energy_threshold_db / 10.0)
        )

    def _extract_segments(self, speech_flags: np.ndarray, frame_step: int,
                          pad_frames: int, signal_length: int
                          ) -> List[Tuple[int, int]]:
        """Convert frame-level speech flags to sample-level segments."""
        segments = []
        in_speech = False
        start = 0

        for i in range(len(speech_flags)):
            if speech_flags[i] and not in_speech:
                start = max(0, (i - pad_frames) * frame_step)
                in_speech = True
            elif not speech_flags[i] and in_speech:
                end = min(signal_length, (i + pad_frames) * frame_step)
                segments.append((start, end))
                in_speech = False

        if in_speech:
            segments.append((start, signal_length))

        return self._merge_close_segments(segments, frame_step * pad_frames * 2)

    def _merge_close_segments(self, segments: List[Tuple[int, int]],
                               min_gap: int) -> List[Tuple[int, int]]:
        """Merge segments that are closer together than min_gap."""
        if len(segments) <= 1:
            return segments

        merged = [segments[0]]
        for start, end in segments[1:]:
            prev_start, prev_end = merged[-1]
            if start - prev_end < min_gap:
                merged[-1] = (prev_start, end)
            else:
                merged.append((start, end))

        return merged

    def reset(self):
        """Reset VAD state for new stream."""
        self._state = VADState.SILENCE
        self._hangover_counter = 0
        self._speech_counter = 0
        self._silence_counter = 0
        self._frame_count = 0
