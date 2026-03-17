"""
Audio Augmentation Pipeline for Training Data.

Applies diverse augmentations to increase training data variety
and model robustness. Implements both time-domain and frequency-domain
augmentations commonly used in speech processing.
"""
import numpy as np
from typing import Optional, List, Tuple, Callable
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class AugmentationConfig:
    """Configuration for audio augmentation pipeline."""
    time_shift_range_ms: Tuple[float, float] = (-100.0, 100.0)
    pitch_shift_range: Tuple[float, float] = (-2.0, 2.0)
    speed_perturb_range: Tuple[float, float] = (0.85, 1.15)
    gain_range_db: Tuple[float, float] = (-6.0, 6.0)

    noise_snr_range_db: Tuple[float, float] = (10.0, 30.0)
    add_noise_prob: float = 0.5
    time_stretch_prob: float = 0.3
    pitch_shift_prob: float = 0.3
    gain_aug_prob: float = 0.4

    spec_augment: bool = True
    freq_mask_max: int = 10
    time_mask_max: int = 15
    num_freq_masks: int = 2
    num_time_masks: int = 2

    mixup_alpha: float = 0.2
    mixup_prob: float = 0.2

    cutout_prob: float = 0.3
    cutout_max_size: Tuple[int, int] = (8, 15)

    sample_rate: int = 16000


class AudioAugmentor:
    """
    Comprehensive audio augmentation pipeline.

    Time-domain augmentations:
    - Time shift
    - Speed perturbation
    - Pitch shifting
    - Gain variation
    - Additive noise injection
    - Polarity inversion
    - Clipping distortion

    Frequency-domain augmentations:
    - SpecAugment (frequency masking, time masking)
    - Frequency warping
    - Spectral cutout

    Training augmentations:
    - Mixup (interpolation between samples)
    - CutMix
    """

    def __init__(self, config: Optional[AugmentationConfig] = None):
        self.config = config or AugmentationConfig()

    def augment(self, signal: np.ndarray, label: Optional[int] = None
                ) -> Tuple[np.ndarray, Optional[int]]:
        """Apply random augmentations to a signal."""
        augmented = signal.copy()

        if np.random.random() < 0.5:
            augmented = self.time_shift(augmented)

        if np.random.random() < self.config.speed_perturb_range[0]:
            augmented = self.speed_perturbation(augmented)

        if np.random.random() < self.config.pitch_shift_prob:
            augmented = self.pitch_shift(augmented)

        if np.random.random() < self.config.gain_aug_prob:
            augmented = self.gain_augmentation(augmented)

        if np.random.random() < self.config.add_noise_prob:
            augmented = self.add_noise(augmented)

        if np.random.random() < 0.1:
            augmented = self.polarity_inversion(augmented)

        if np.random.random() < 0.1:
            augmented = self.clipping_distortion(augmented)

        return augmented, label

    def augment_spectrogram(self, spectrogram: np.ndarray) -> np.ndarray:
        """Apply SpecAugment to a spectrogram."""
        augmented = spectrogram.copy()

        if self.config.spec_augment:
            augmented = self.spec_augment_freq_mask(augmented)
            augmented = self.spec_augment_time_mask(augmented)

        if np.random.random() < self.config.cutout_prob:
            augmented = self.spectral_cutout(augmented)

        return augmented

    # --- Time-domain augmentations ---

    def time_shift(self, signal: np.ndarray) -> np.ndarray:
        """Shift signal in time (circular shift)."""
        shift_range = self.config.time_shift_range_ms
        shift_samples = int(
            np.random.uniform(shift_range[0], shift_range[1])
            * self.config.sample_rate / 1000.0
        )
        return np.roll(signal, shift_samples)

    def speed_perturbation(self, signal: np.ndarray) -> np.ndarray:
        """Change speed of the signal (resampling approach)."""
        factor = np.random.uniform(*self.config.speed_perturb_range)
        indices = np.arange(0, len(signal), factor)
        indices = indices[indices < len(signal) - 1].astype(np.int64)
        resampled = signal[indices]

        if len(resampled) > len(signal):
            return resampled[:len(signal)]
        elif len(resampled) < len(signal):
            return np.pad(resampled, (0, len(signal) - len(resampled)))
        return resampled

    def pitch_shift(self, signal: np.ndarray) -> np.ndarray:
        """
        Pitch shift using phase vocoder approach (simplified).
        Combines speed perturbation + resampling.
        """
        semitones = np.random.uniform(*self.config.pitch_shift_range)
        factor = 2.0 ** (semitones / 12.0)

        stretched = self._time_stretch(signal, 1.0 / factor)
        indices = np.linspace(0, len(stretched) - 1, len(signal))
        integer_part = indices.astype(np.int64)
        integer_part = np.clip(integer_part, 0, len(stretched) - 2)
        frac = indices - integer_part
        result = stretched[integer_part] * (1 - frac) + stretched[integer_part + 1] * frac

        return result.astype(np.float32)

    def gain_augmentation(self, signal: np.ndarray) -> np.ndarray:
        """Apply random gain change in dB."""
        gain_db = np.random.uniform(*self.config.gain_range_db)
        gain_linear = 10.0 ** (gain_db / 20.0)
        return np.clip(signal * gain_linear, -1.0, 1.0).astype(np.float32)

    def add_noise(self, signal: np.ndarray) -> np.ndarray:
        """Add white noise at random SNR."""
        snr_db = np.random.uniform(*self.config.noise_snr_range_db)
        signal_power = np.mean(signal ** 2)
        noise_power = signal_power / (10 ** (snr_db / 10))
        noise = np.sqrt(noise_power) * np.random.randn(len(signal))
        return (signal + noise).astype(np.float32)

    def polarity_inversion(self, signal: np.ndarray) -> np.ndarray:
        """Invert polarity of the signal."""
        return -signal

    def clipping_distortion(self, signal: np.ndarray,
                              threshold: Optional[float] = None) -> np.ndarray:
        """Apply soft clipping distortion."""
        threshold = threshold or np.random.uniform(0.5, 0.9)
        return np.clip(signal, -threshold, threshold).astype(np.float32)

    def _time_stretch(self, signal: np.ndarray, factor: float) -> np.ndarray:
        """Time stretch using overlap-add with windowing."""
        if abs(factor - 1.0) < 0.01:
            return signal.copy()

        frame_len = 1024
        hop = frame_len // 4
        output_hop = int(hop * factor)

        num_frames = (len(signal) - frame_len) // hop + 1
        output_length = int(len(signal) * factor)
        output = np.zeros(output_length + frame_len, dtype=np.float32)
        window = np.hanning(frame_len).astype(np.float32)
        window_sum = np.zeros(output_length + frame_len, dtype=np.float32)

        for i in range(num_frames):
            input_start = i * hop
            frame = signal[input_start:input_start + frame_len]
            if len(frame) < frame_len:
                frame = np.pad(frame, (0, frame_len - len(frame)))

            output_start = int(i * output_hop)
            if output_start + frame_len <= len(output):
                output[output_start:output_start + frame_len] += frame * window
                window_sum[output_start:output_start + frame_len] += window ** 2

        nonzero = window_sum > 1e-10
        output[nonzero] /= window_sum[nonzero]

        return output[:output_length]

    # --- Frequency-domain augmentations (SpecAugment) ---

    def spec_augment_freq_mask(self, spectrogram: np.ndarray) -> np.ndarray:
        """Apply frequency masking (SpecAugment)."""
        result = spectrogram.copy()
        num_freq = spectrogram.shape[1] if spectrogram.ndim > 1 else spectrogram.shape[0]

        for _ in range(self.config.num_freq_masks):
            f = np.random.randint(0, min(self.config.freq_mask_max, num_freq))
            f0 = np.random.randint(0, max(1, num_freq - f))
            if spectrogram.ndim > 1:
                result[:, f0:f0 + f] = 0
            else:
                result[f0:f0 + f] = 0

        return result

    def spec_augment_time_mask(self, spectrogram: np.ndarray) -> np.ndarray:
        """Apply time masking (SpecAugment)."""
        result = spectrogram.copy()
        num_time = spectrogram.shape[0]

        for _ in range(self.config.num_time_masks):
            t = np.random.randint(0, min(self.config.time_mask_max, num_time))
            t0 = np.random.randint(0, max(1, num_time - t))
            result[t0:t0 + t] = 0

        return result

    def spectral_cutout(self, spectrogram: np.ndarray) -> np.ndarray:
        """Apply cutout augmentation to spectrogram."""
        result = spectrogram.copy()
        if spectrogram.ndim < 2:
            return result

        h, w = spectrogram.shape[:2]
        cut_h = np.random.randint(1, min(self.config.cutout_max_size[0], h))
        cut_w = np.random.randint(1, min(self.config.cutout_max_size[1], w))

        y = np.random.randint(0, max(1, h - cut_h))
        x = np.random.randint(0, max(1, w - cut_w))

        result[y:y + cut_h, x:x + cut_w] = 0
        return result

    # --- Training augmentations ---

    def mixup(self, signal1: np.ndarray, label1: int,
              signal2: np.ndarray, label2: int,
              num_classes: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Mixup augmentation: interpolate between two samples.
        Returns mixed signal and soft label vector.
        """
        lam = np.random.beta(self.config.mixup_alpha, self.config.mixup_alpha)

        min_len = min(len(signal1), len(signal2))
        mixed = lam * signal1[:min_len] + (1 - lam) * signal2[:min_len]

        soft_label = np.zeros(num_classes, dtype=np.float32)
        soft_label[label1] = lam
        soft_label[label2] = 1 - lam

        return mixed.astype(np.float32), soft_label

    def augment_batch(self, signals: np.ndarray,
                       labels: Optional[np.ndarray] = None
                       ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """Augment an entire batch of signals."""
        augmented_signals = np.zeros_like(signals)

        for i in range(len(signals)):
            aug_signal, _ = self.augment(signals[i])
            augmented_signals[i] = aug_signal

        return augmented_signals, labels
