"""
Feature Extraction - MFCC, Mel Spectrograms, and advanced audio features.

Implements a complete feature extraction pipeline for keyword spotting
and speech recognition using TensorFlow for GPU-accelerated computation
and numpy as fallback for CPU-only environments.
"""
import numpy as np
from typing import Optional, Tuple
from dataclasses import dataclass

try:
    import tensorflow as tf
    HAS_TF = True
except ImportError:
    HAS_TF = False

from .audio_processor import AudioConfig, AudioProcessor


@dataclass
class FeatureConfig:
    """Configuration for feature extraction."""
    num_mel_bins: int = 80
    num_mfcc: int = 40
    num_cepstral: int = 13
    fft_size: int = 512
    low_freq: float = 20.0
    high_freq: float = 8000.0
    use_energy: bool = True
    use_delta: bool = True
    use_delta_delta: bool = True
    cepstral_lifter: float = 22.0
    log_offset: float = 1e-6
    mean_normalize: bool = True
    variance_normalize: bool = True


class FeatureExtractor:
    """
    Comprehensive audio feature extractor for keyword spotting.

    Extracts:
    - Mel-frequency spectrograms
    - MFCCs (Mel-Frequency Cepstral Coefficients)
    - Delta and delta-delta (acceleration) features
    - Spectral features (centroid, bandwidth, rolloff, flux)
    - Chroma features
    - Log filterbank energies

    Uses TensorFlow signal processing when available for GPU acceleration,
    falls back to numpy for CPU-only environments.
    """

    def __init__(self, audio_config: Optional[AudioConfig] = None,
                 feature_config: Optional[FeatureConfig] = None):
        self.audio_config = audio_config or AudioConfig()
        self.feature_config = feature_config or FeatureConfig()
        self.processor = AudioProcessor(self.audio_config)

        self._mel_filterbank = None
        self._dct_matrix = None

    def extract_features(self, signal: np.ndarray, feature_type: str = 'mfcc'
                         ) -> np.ndarray:
        """
        Extract features from a preprocessed audio signal.
        feature_type: 'mfcc', 'mel_spectrogram', 'log_filterbank', 'full'
        """
        extractors = {
            'mfcc': self.extract_mfcc,
            'mel_spectrogram': self.extract_mel_spectrogram,
            'log_filterbank': self.extract_log_filterbank,
            'full': self.extract_full_features,
        }
        extractor = extractors.get(feature_type, self.extract_mfcc)
        return extractor(signal)

    def extract_mel_spectrogram(self, signal: np.ndarray) -> np.ndarray:
        """
        Compute mel-scaled spectrogram.
        Returns shape (num_frames, num_mel_bins).
        """
        if HAS_TF:
            return self._tf_mel_spectrogram(signal)
        return self._np_mel_spectrogram(signal)

    def extract_mfcc(self, signal: np.ndarray) -> np.ndarray:
        """
        Extract MFCCs with optional delta and delta-delta features.
        Returns shape (num_frames, num_features) where num_features depends
        on configuration (13-39 typically).
        """
        log_mel = self.extract_log_filterbank(signal)

        dct = self._get_dct_matrix()
        mfcc = np.dot(log_mel, dct.T)[:, :self.feature_config.num_cepstral]

        if self.feature_config.cepstral_lifter > 0:
            lifter = self.feature_config.cepstral_lifter
            n = np.arange(self.feature_config.num_cepstral)
            lift = 1 + (lifter / 2.0) * np.sin(np.pi * n / lifter)
            mfcc *= lift

        features = [mfcc]

        if self.feature_config.use_delta:
            delta = self._compute_deltas(mfcc)
            features.append(delta)

        if self.feature_config.use_delta_delta:
            delta2 = self._compute_deltas(self._compute_deltas(mfcc))
            features.append(delta2)

        result = np.concatenate(features, axis=1)

        if self.feature_config.mean_normalize:
            result = result - np.mean(result, axis=0, keepdims=True)
        if self.feature_config.variance_normalize:
            std = np.std(result, axis=0, keepdims=True)
            std = np.maximum(std, 1e-10)
            result = result / std

        return result.astype(np.float32)

    def extract_log_filterbank(self, signal: np.ndarray) -> np.ndarray:
        """
        Compute log mel-filterbank energies.
        Returns shape (num_frames, num_mel_bins).
        """
        mel_spec = self.extract_mel_spectrogram(signal)
        return np.log(mel_spec + self.feature_config.log_offset).astype(np.float32)

    def extract_full_features(self, signal: np.ndarray) -> np.ndarray:
        """
        Extract comprehensive feature set:
        MFCC + log filterbank + spectral features concatenated.
        Returns shape (num_frames, total_features).
        """
        mfcc = self.extract_mfcc(signal)
        log_fb = self.extract_log_filterbank(signal)
        spectral = self._extract_spectral_features(signal)

        min_frames = min(mfcc.shape[0], log_fb.shape[0], spectral.shape[0])
        return np.concatenate([
            mfcc[:min_frames],
            log_fb[:min_frames],
            spectral[:min_frames],
        ], axis=1).astype(np.float32)

    def extract_for_keyword_spotting(self, signal: np.ndarray) -> np.ndarray:
        """
        Optimized feature extraction for keyword spotting models.
        Returns a fixed-size feature map suitable for CNN input.
        Shape: (num_frames, num_mel_bins, 1) — single-channel image-like.
        """
        log_mel = self.extract_log_filterbank(signal)

        if self.feature_config.mean_normalize:
            log_mel = log_mel - np.mean(log_mel, axis=0, keepdims=True)
        if self.feature_config.variance_normalize:
            std = np.std(log_mel, axis=0, keepdims=True)
            std = np.maximum(std, 1e-10)
            log_mel = log_mel / std

        return log_mel[:, :, np.newaxis].astype(np.float32)

    def pad_or_truncate_features(self, features: np.ndarray,
                                  target_frames: int) -> np.ndarray:
        """Pad with zeros or truncate features to fixed number of frames."""
        if features.shape[0] >= target_frames:
            return features[:target_frames]
        pad_width = [(0, target_frames - features.shape[0])]
        pad_width += [(0, 0)] * (features.ndim - 1)
        return np.pad(features, pad_width, mode='constant')

    # --- TensorFlow-accelerated implementations ---

    def _tf_mel_spectrogram(self, signal: np.ndarray) -> np.ndarray:
        """TensorFlow-based mel spectrogram computation."""
        signal_tensor = tf.constant(signal, dtype=tf.float32)

        stft = tf.signal.stft(
            signal_tensor,
            frame_length=self.audio_config.frame_length,
            frame_step=self.audio_config.frame_step,
            fft_length=self.feature_config.fft_size,
            window_fn=tf.signal.hann_window,
        )
        magnitude = tf.abs(stft)
        power = tf.square(magnitude)

        mel_filterbank = tf.signal.linear_to_mel_weight_matrix(
            num_mel_bins=self.feature_config.num_mel_bins,
            num_spectrogram_bins=power.shape[-1],
            sample_rate=self.audio_config.target_sample_rate,
            lower_edge_hertz=self.feature_config.low_freq,
            upper_edge_hertz=min(
                self.feature_config.high_freq,
                self.audio_config.target_sample_rate / 2.0
            ),
        )

        mel_spectrogram = tf.matmul(power, mel_filterbank)
        return mel_spectrogram.numpy()

    def _tf_mfcc(self, signal: np.ndarray) -> np.ndarray:
        """TensorFlow-based MFCC extraction."""
        log_mel = self.extract_log_filterbank(signal)
        log_mel_tensor = tf.constant(log_mel, dtype=tf.float32)
        mfccs = tf.signal.mfccs_from_log_mel_spectrograms(log_mel_tensor)
        return mfccs[:, :self.feature_config.num_cepstral].numpy()

    # --- Numpy fallback implementations ---

    def _np_mel_spectrogram(self, signal: np.ndarray) -> np.ndarray:
        """Pure numpy mel spectrogram computation."""
        frames = self.processor.frame_signal(signal)

        fft_size = self.feature_config.fft_size
        spectra = np.fft.rfft(frames, n=fft_size)
        power_spectra = np.abs(spectra) ** 2 / fft_size

        mel_fb = self._get_mel_filterbank(fft_size)
        mel_spectrogram = np.dot(power_spectra, mel_fb.T)

        return mel_spectrogram.astype(np.float32)

    def _get_mel_filterbank(self, fft_size: int) -> np.ndarray:
        """Compute mel-spaced triangular filterbank."""
        if self._mel_filterbank is not None:
            return self._mel_filterbank

        num_bins = self.feature_config.num_mel_bins
        sample_rate = self.audio_config.target_sample_rate
        low_freq = self.feature_config.low_freq
        high_freq = min(self.feature_config.high_freq, sample_rate / 2.0)

        low_mel = self._hz_to_mel(low_freq)
        high_mel = self._hz_to_mel(high_freq)
        mel_points = np.linspace(low_mel, high_mel, num_bins + 2)
        hz_points = self._mel_to_hz(mel_points)

        freq_bins = np.floor((fft_size + 1) * hz_points / sample_rate).astype(int)
        num_fft_bins = fft_size // 2 + 1

        filterbank = np.zeros((num_bins, num_fft_bins), dtype=np.float32)
        for i in range(num_bins):
            left = freq_bins[i]
            center = freq_bins[i + 1]
            right = freq_bins[i + 2]

            for j in range(left, center):
                if center > left:
                    filterbank[i, j] = (j - left) / (center - left)
            for j in range(center, right):
                if right > center:
                    filterbank[i, j] = (right - j) / (right - center)

        self._mel_filterbank = filterbank
        return filterbank

    def _get_dct_matrix(self) -> np.ndarray:
        """Compute DCT-II matrix for MFCC computation."""
        if self._dct_matrix is not None:
            return self._dct_matrix

        N = self.feature_config.num_mel_bins
        M = self.feature_config.num_mfcc
        dct = np.zeros((M, N), dtype=np.float32)
        for k in range(M):
            for n in range(N):
                dct[k, n] = np.cos(np.pi * k * (2 * n + 1) / (2 * N))
        dct *= np.sqrt(2.0 / N)

        self._dct_matrix = dct
        return dct

    def _compute_deltas(self, features: np.ndarray, width: int = 2) -> np.ndarray:
        """
        Compute delta (derivative) features using regression formula.
        delta[t] = sum_{n=1}^{N} n * (c[t+n] - c[t-n]) / (2 * sum_{n=1}^{N} n^2)
        """
        num_frames, num_features = features.shape
        denominator = 2 * sum(n ** 2 for n in range(1, width + 1))

        padded = np.pad(features, ((width, width), (0, 0)), mode='edge')
        deltas = np.zeros_like(features)
        for t in range(num_frames):
            for n in range(1, width + 1):
                deltas[t] += n * (padded[t + width + n] - padded[t + width - n])
            deltas[t] /= denominator

        return deltas

    def _extract_spectral_features(self, signal: np.ndarray) -> np.ndarray:
        """
        Extract spectral features per frame:
        - Spectral centroid
        - Spectral bandwidth
        - Spectral rolloff (85%)
        - Spectral flux
        """
        frames = self.processor.frame_signal(signal)
        fft_size = self.feature_config.fft_size
        spectra = np.abs(np.fft.rfft(frames, n=fft_size))

        num_frames = spectra.shape[0]
        freq_bins = np.fft.rfftfreq(fft_size, d=1.0 / self.audio_config.target_sample_rate)

        features = np.zeros((num_frames, 4), dtype=np.float32)

        for i in range(num_frames):
            mag = spectra[i]
            total_energy = np.sum(mag)

            if total_energy > 0:
                centroid = np.sum(freq_bins * mag) / total_energy
                bandwidth = np.sqrt(np.sum(((freq_bins - centroid) ** 2) * mag) / total_energy)

                cumsum = np.cumsum(mag)
                rolloff_idx = np.searchsorted(cumsum, 0.85 * total_energy)
                rolloff = freq_bins[min(rolloff_idx, len(freq_bins) - 1)]

                if i > 0:
                    prev_mag = spectra[i - 1]
                    flux = np.sum((mag - prev_mag) ** 2)
                else:
                    flux = 0.0

                features[i] = [centroid, bandwidth, rolloff, flux]

        max_vals = np.max(np.abs(features), axis=0, keepdims=True)
        max_vals = np.maximum(max_vals, 1e-10)
        features = features / max_vals

        return features

    @staticmethod
    def _hz_to_mel(hz: np.ndarray) -> np.ndarray:
        """Convert frequency in Hz to mel scale."""
        return 2595.0 * np.log10(1.0 + hz / 700.0)

    @staticmethod
    def _mel_to_hz(mel: np.ndarray) -> np.ndarray:
        """Convert mel scale to frequency in Hz."""
        return 700.0 * (10.0 ** (mel / 2595.0) - 1.0)
