"""
Synthetic Training Data Generator for Keyword Spotting.

Generates large-scale training data using:
1. TTS (Text-to-Speech) synthesis for keyword utterances
2. Phoneme-based synthesis for keyword variations
3. Background noise mixing
4. Multi-speaker simulation with pitch/speed variation
5. Room acoustic simulation (reverb, echo)

Produces labeled audio samples for all platform keywords.
"""
import os
import json
import hashlib
import logging
import numpy as np
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field

from ..engine.keyword_spotter import PLATFORM_KEYWORDS

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / 'voice_training_data'


@dataclass
class GeneratorConfig:
    """Configuration for training data generation."""
    sample_rate: int = 16000
    duration_s: float = 1.0
    samples_per_keyword: int = 2000
    silence_samples: int = 5000
    noise_samples: int = 3000

    num_speakers: int = 50
    pitch_range: Tuple[float, float] = (0.7, 1.4)
    speed_range: Tuple[float, float] = (0.8, 1.3)
    volume_range: Tuple[float, float] = (0.3, 1.0)

    noise_types: List[str] = field(default_factory=lambda: [
        'white', 'pink', 'brown', 'babble', 'office', 'traffic',
        'music', 'keyboard', 'fan', 'rain',
    ])
    snr_range_db: Tuple[float, float] = (5.0, 30.0)

    reverb_levels: List[str] = field(default_factory=lambda: [
        'none', 'small_room', 'medium_room', 'large_room', 'hall'
    ])

    output_format: str = 'wav'
    bit_depth: int = 16


class TrainingDataGenerator:
    """
    Large-scale synthetic training data generator.

    Generates realistic training data by:
    1. Creating base keyword waveforms using parametric synthesis
    2. Simulating multiple speakers with voice characteristics
    3. Adding realistic background noise at various SNR levels
    4. Applying room acoustics (impulse responses)
    5. Creating positive + negative examples
    6. Generating silence and unknown-word samples

    Target: ~50K-100K samples per keyword for robust training.
    """

    def __init__(self, config: Optional[GeneratorConfig] = None,
                 output_dir: Optional[str] = None):
        self.config = config or GeneratorConfig()
        self.output_dir = Path(output_dir) if output_dir else DATA_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._speaker_profiles = self._generate_speaker_profiles()
        self._noise_generators = self._init_noise_generators()

    def generate_full_dataset(self, keywords: Optional[List[str]] = None
                              ) -> Dict[str, int]:
        """
        Generate the complete training dataset for all keywords.
        Returns dict mapping keyword -> number of samples generated.
        """
        keywords = keywords or list(PLATFORM_KEYWORDS.keys())
        stats = {}

        logger.info("Generating training data for %d keywords", len(keywords))

        for keyword in keywords:
            if keyword.startswith('_'):
                continue
            count = self._generate_keyword_samples(keyword)
            stats[keyword] = count
            logger.info("Generated %d samples for '%s'", count, keyword)

        silence_count = self._generate_silence_samples()
        stats['_silence'] = silence_count

        noise_count = self._generate_noise_only_samples()
        stats['_noise'] = noise_count

        unknown_count = self._generate_unknown_samples()
        stats['_unknown'] = unknown_count

        manifest = self._create_manifest(stats)
        logger.info("Dataset generation complete. Total samples: %d",
                     sum(stats.values()))
        return stats

    def _generate_keyword_samples(self, keyword: str) -> int:
        """Generate all variations of a single keyword."""
        keyword_dir = self.output_dir / keyword
        keyword_dir.mkdir(exist_ok=True)

        count = 0
        samples_per_speaker = self.config.samples_per_keyword // self.config.num_speakers

        for speaker_id, profile in enumerate(self._speaker_profiles):
            for variation in range(samples_per_speaker):
                base_signal = self._synthesize_keyword(keyword, profile)

                if variation % 3 == 0:
                    noise_type = np.random.choice(self.config.noise_types)
                    snr = np.random.uniform(*self.config.snr_range_db)
                    base_signal = self._add_noise(base_signal, noise_type, snr)

                if variation % 4 == 0:
                    reverb_level = np.random.choice(self.config.reverb_levels)
                    base_signal = self._add_reverb(base_signal, reverb_level)

                volume = np.random.uniform(*self.config.volume_range)
                base_signal = base_signal * volume

                base_signal = np.clip(base_signal, -1.0, 1.0)

                filename = f'{keyword}_s{speaker_id:03d}_v{variation:04d}.npy'
                np.save(str(keyword_dir / filename), base_signal.astype(np.float32))
                count += 1

        return count

    def _synthesize_keyword(self, keyword: str, speaker_profile: dict
                             ) -> np.ndarray:
        """
        Synthesize a keyword waveform using parametric voice synthesis.

        Uses a formant-based synthesis approach:
        1. Generate phoneme sequence from keyword text
        2. Synthesize each phoneme with speaker characteristics
        3. Apply coarticulation smoothing
        4. Add prosodic variation (pitch contour, duration)
        """
        num_samples = int(self.config.sample_rate * self.config.duration_s)
        t = np.linspace(0, self.config.duration_s, num_samples, dtype=np.float32)

        phonemes = self._text_to_phonemes(keyword)

        f0 = speaker_profile['f0'] * np.random.uniform(0.9, 1.1)
        pitch_contour = self._generate_pitch_contour(t, f0, len(phonemes))

        signal = np.zeros(num_samples, dtype=np.float32)
        samples_per_phoneme = num_samples // max(len(phonemes), 1)

        for i, phoneme in enumerate(phonemes):
            start = i * samples_per_phoneme
            end = min(start + samples_per_phoneme, num_samples)
            segment_t = t[start:end]

            formants = self._get_formant_frequencies(phoneme, speaker_profile)
            segment = self._formant_synthesis(
                segment_t, pitch_contour[start:end], formants, speaker_profile
            )
            signal[start:end] = segment

        signal = self._apply_coarticulation(signal, phonemes, samples_per_phoneme)

        envelope = self._generate_envelope(num_samples, attack_ms=20, decay_ms=50)
        signal *= envelope

        speed_factor = np.random.uniform(*self.config.speed_range)
        signal = self._change_speed(signal, speed_factor)

        if len(signal) > num_samples:
            signal = signal[:num_samples]
        elif len(signal) < num_samples:
            signal = np.pad(signal, (0, num_samples - len(signal)))

        peak = np.max(np.abs(signal))
        if peak > 0:
            signal /= peak

        return signal

    def _text_to_phonemes(self, text: str) -> List[str]:
        """
        Convert text to phoneme sequence using rule-based English phonemizer.
        Handles common English pronunciation patterns.
        """
        phoneme_map = {
            'a': ['AE'], 'b': ['B'], 'c': ['K'], 'd': ['D'], 'e': ['EH'],
            'f': ['F'], 'g': ['G'], 'h': ['HH'], 'i': ['IH'], 'j': ['JH'],
            'k': ['K'], 'l': ['L'], 'm': ['M'], 'n': ['N'], 'o': ['OW'],
            'p': ['P'], 'q': ['K', 'W'], 'r': ['R'], 's': ['S'], 't': ['T'],
            'u': ['UW'], 'v': ['V'], 'w': ['W'], 'x': ['K', 'S'],
            'y': ['Y'], 'z': ['Z'],
            'th': ['TH'], 'sh': ['SH'], 'ch': ['CH'], 'ng': ['NG'],
            'ee': ['IY'], 'oo': ['UW'], 'ou': ['AW'], 'oi': ['OY'],
            'ai': ['EY'], 'ea': ['IY'], 'er': ['ER'], 'ar': ['AA', 'R'],
            'or': ['AO', 'R'], 'ir': ['ER'],
        }

        text = text.lower().strip()
        phonemes = []
        i = 0

        while i < len(text):
            if i + 1 < len(text) and text[i:i+2] in phoneme_map:
                phonemes.extend(phoneme_map[text[i:i+2]])
                i += 2
            elif text[i] in phoneme_map:
                phonemes.extend(phoneme_map[text[i]])
                i += 1
            elif text[i] == ' ':
                phonemes.append('SIL')
                i += 1
            else:
                i += 1

        return phonemes if phonemes else ['SIL']

    def _get_formant_frequencies(self, phoneme: str, speaker: dict
                                  ) -> List[Tuple[float, float]]:
        """
        Get formant frequencies (F1, F2, F3) and bandwidths for a phoneme.
        Adjusted for speaker characteristics.
        """
        formant_table = {
            'AE': [(660, 60), (1720, 80), (2410, 120)],
            'EH': [(530, 60), (1840, 80), (2480, 120)],
            'IH': [(390, 50), (1990, 80), (2550, 120)],
            'IY': [(270, 40), (2290, 80), (3010, 120)],
            'AA': [(730, 70), (1090, 80), (2440, 120)],
            'AO': [(570, 60), (840, 80), (2410, 120)],
            'UW': [(300, 40), (870, 60), (2240, 120)],
            'OW': [(500, 60), (700, 60), (2360, 120)],
            'ER': [(490, 60), (1350, 80), (1690, 100)],
            'AW': [(680, 70), (1220, 80), (2600, 120)],
            'EY': [(450, 50), (2100, 80), (2800, 120)],
            'OY': [(550, 60), (860, 70), (2400, 120)],
            'SIL': [(0, 0), (0, 0), (0, 0)],
        }

        # Consonants get noise-like synthesis
        consonant_formants = [(500, 100), (1500, 200), (2500, 300)]

        base_formants = formant_table.get(phoneme, consonant_formants)

        scale = speaker.get('formant_scale', 1.0)
        return [(f * scale, bw) for f, bw in base_formants]

    def _formant_synthesis(self, t: np.ndarray, pitch: np.ndarray,
                            formants: List[Tuple[float, float]],
                            speaker: dict) -> np.ndarray:
        """
        Synthesize audio using additive formant synthesis.
        Generates voiced speech by exciting formant resonators with
        a glottal pulse train.
        """
        signal = np.zeros_like(t)

        if all(f == 0 for f, _ in formants):
            return signal

        phase = np.cumsum(pitch / self.config.sample_rate) * 2 * np.pi
        glottal = np.sin(phase)
        glottal += 0.5 * np.sin(2 * phase)
        glottal += 0.25 * np.sin(3 * phase)

        jitter = speaker.get('jitter', 0.01)
        glottal *= (1 + jitter * np.random.randn(len(t)))

        for i, (freq, bandwidth) in enumerate(formants):
            if freq <= 0:
                continue

            amplitude = 1.0 / (i + 1)
            formant_signal = amplitude * np.sin(
                2 * np.pi * freq * t + np.random.uniform(0, 2 * np.pi)
            )

            decay = np.exp(-np.pi * bandwidth * t)
            decay = np.minimum(decay, 1.0)

            signal += formant_signal * glottal * decay

        breathiness = speaker.get('breathiness', 0.05)
        signal += breathiness * np.random.randn(len(t))

        return signal.astype(np.float32)

    def _generate_pitch_contour(self, t: np.ndarray, base_f0: float,
                                  num_phonemes: int) -> np.ndarray:
        """Generate a natural-sounding pitch contour with micro-prosody."""
        contour = np.ones_like(t) * base_f0

        # Declination (pitch falls over utterance)
        declination = np.linspace(1.0, 0.85, len(t))
        contour *= declination

        # Micro-prosody: small random variations
        noise = np.random.randn(len(t)) * 2.0
        from_filt = np.convolve(noise, np.ones(50)/50, mode='same')
        contour += from_filt

        # Accent on stressed syllable (roughly in the middle)
        accent_center = len(t) // 3
        accent_width = len(t) // 6
        accent = 10 * np.exp(-((np.arange(len(t)) - accent_center) / accent_width) ** 2)
        contour += accent

        return contour.astype(np.float32)

    def _apply_coarticulation(self, signal: np.ndarray,
                               phonemes: List[str],
                               samples_per_phoneme: int) -> np.ndarray:
        """Smooth transitions between phonemes."""
        if len(phonemes) <= 1:
            return signal

        overlap = samples_per_phoneme // 8
        for i in range(1, len(phonemes)):
            center = i * samples_per_phoneme
            start = max(0, center - overlap)
            end = min(len(signal), center + overlap)
            if end - start > 0:
                window = np.hanning(end - start)
                blend = np.ones(end - start)
                blend[:len(blend)//2] = window[:len(blend)//2]
                signal[start:end] *= blend

        return signal

    def _generate_envelope(self, num_samples: int,
                            attack_ms: float = 20, decay_ms: float = 50
                            ) -> np.ndarray:
        """Generate amplitude envelope with attack, sustain, decay."""
        attack_samples = int(self.config.sample_rate * attack_ms / 1000)
        decay_samples = int(self.config.sample_rate * decay_ms / 1000)

        envelope = np.ones(num_samples, dtype=np.float32)

        if attack_samples > 0:
            envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
        if decay_samples > 0 and decay_samples < num_samples:
            envelope[-decay_samples:] = np.linspace(1, 0, decay_samples)

        return envelope

    def _change_speed(self, signal: np.ndarray, factor: float) -> np.ndarray:
        """Change playback speed by resampling."""
        if abs(factor - 1.0) < 0.01:
            return signal
        indices = np.arange(0, len(signal), factor)
        indices = indices[indices < len(signal) - 1].astype(np.int64)
        return signal[indices]

    # --- Noise generation ---

    def _init_noise_generators(self) -> Dict:
        """Initialize noise generation functions."""
        return {
            'white': self._white_noise,
            'pink': self._pink_noise,
            'brown': self._brown_noise,
            'babble': self._babble_noise,
            'office': self._office_noise,
            'traffic': self._traffic_noise,
            'music': self._music_noise,
            'keyboard': self._keyboard_noise,
            'fan': self._fan_noise,
            'rain': self._rain_noise,
        }

    def _add_noise(self, signal: np.ndarray, noise_type: str,
                    snr_db: float) -> np.ndarray:
        """Mix noise into signal at specified SNR."""
        generator = self._noise_generators.get(noise_type, self._white_noise)
        noise = generator(len(signal))

        signal_power = np.mean(signal ** 2)
        noise_power = np.mean(noise ** 2)

        if noise_power > 0:
            scale = np.sqrt(signal_power / (noise_power * 10 ** (snr_db / 10)))
            return signal + scale * noise
        return signal

    def _white_noise(self, length: int) -> np.ndarray:
        return np.random.randn(length).astype(np.float32)

    def _pink_noise(self, length: int) -> np.ndarray:
        """Pink noise (1/f) via Voss-McCartney algorithm."""
        num_rows = 16
        array = np.random.randn(num_rows, length // num_rows + 1).astype(np.float32)
        reshaped = np.cumsum(array, axis=1)
        result = np.sum(reshaped[:, :length // num_rows + 1], axis=0)
        result = np.interp(np.linspace(0, len(result)-1, length),
                           np.arange(len(result)), result)
        return (result / np.max(np.abs(result) + 1e-10)).astype(np.float32)

    def _brown_noise(self, length: int) -> np.ndarray:
        """Brownian/red noise via cumulative sum of white noise."""
        white = np.random.randn(length).astype(np.float32)
        brown = np.cumsum(white)
        brown -= np.mean(brown)
        peak = np.max(np.abs(brown))
        return (brown / (peak + 1e-10)).astype(np.float32)

    def _babble_noise(self, length: int) -> np.ndarray:
        """Simulate babble noise (multiple overlapping voices)."""
        num_voices = np.random.randint(3, 8)
        babble = np.zeros(length, dtype=np.float32)
        for _ in range(num_voices):
            freq = np.random.uniform(100, 400)
            t = np.arange(length, dtype=np.float32) / self.config.sample_rate
            voice = np.sin(2 * np.pi * freq * t)
            voice *= np.random.randn(length) * 0.3
            modulation = 0.5 + 0.5 * np.sin(2 * np.pi * np.random.uniform(1, 4) * t)
            babble += voice * modulation
        peak = np.max(np.abs(babble))
        return (babble / (peak + 1e-10)).astype(np.float32)

    def _office_noise(self, length: int) -> np.ndarray:
        """Office ambient noise (AC hum + keyboard clicks + murmur)."""
        t = np.arange(length, dtype=np.float32) / self.config.sample_rate
        hum = 0.3 * np.sin(2 * np.pi * 60 * t)
        hum += 0.1 * np.sin(2 * np.pi * 120 * t)
        murmur = 0.2 * self._babble_noise(length)
        ambient = 0.05 * np.random.randn(length).astype(np.float32)
        result = hum + murmur + ambient
        peak = np.max(np.abs(result))
        return (result / (peak + 1e-10)).astype(np.float32)

    def _traffic_noise(self, length: int) -> np.ndarray:
        """Traffic noise simulation (low frequency rumble + transients)."""
        brown = self._brown_noise(length)
        t = np.arange(length, dtype=np.float32) / self.config.sample_rate
        modulation = 0.5 + 0.5 * np.sin(2 * np.pi * 0.2 * t)
        return (brown * modulation).astype(np.float32)

    def _music_noise(self, length: int) -> np.ndarray:
        """Background music simulation (harmonic content)."""
        t = np.arange(length, dtype=np.float32) / self.config.sample_rate
        base_freq = np.random.choice([261.63, 293.66, 329.63, 349.23, 392.00])
        signal = np.zeros(length, dtype=np.float32)
        for harmonic in range(1, 6):
            amp = 1.0 / harmonic
            signal += amp * np.sin(2 * np.pi * base_freq * harmonic * t)
        modulation = 0.5 + 0.5 * np.sin(2 * np.pi * 0.5 * t)
        return (signal * modulation / np.max(np.abs(signal) + 1e-10)).astype(np.float32)

    def _keyboard_noise(self, length: int) -> np.ndarray:
        """Keyboard typing noise (impulsive transients)."""
        signal = np.zeros(length, dtype=np.float32)
        num_clicks = np.random.randint(5, 20)
        for _ in range(num_clicks):
            pos = np.random.randint(0, length - 200)
            click_len = np.random.randint(50, 200)
            click = np.random.randn(click_len).astype(np.float32)
            click *= np.exp(-np.linspace(0, 5, click_len))
            signal[pos:pos + click_len] += click * np.random.uniform(0.5, 1.0)
        return signal

    def _fan_noise(self, length: int) -> np.ndarray:
        """Fan/HVAC noise (low-frequency + broadband)."""
        pink = self._pink_noise(length)
        t = np.arange(length, dtype=np.float32) / self.config.sample_rate
        fan_tone = 0.3 * np.sin(2 * np.pi * 120 * t)
        return (0.7 * pink + fan_tone).astype(np.float32)

    def _rain_noise(self, length: int) -> np.ndarray:
        """Rain noise simulation (filtered white noise + drops)."""
        base = self._pink_noise(length) * 0.5
        num_drops = np.random.randint(20, 100)
        for _ in range(num_drops):
            pos = np.random.randint(0, length - 100)
            drop_len = np.random.randint(20, 100)
            drop = np.random.randn(drop_len).astype(np.float32)
            drop *= np.exp(-np.linspace(0, 8, drop_len))
            base[pos:pos + drop_len] += drop * np.random.uniform(0.1, 0.5)
        return base

    # --- Room acoustics ---

    def _add_reverb(self, signal: np.ndarray, level: str) -> np.ndarray:
        """Apply simulated room reverb using synthetic impulse response."""
        if level == 'none':
            return signal

        ir = self._generate_impulse_response(level)
        reverbed = np.convolve(signal, ir, mode='full')[:len(signal)]

        dry_wet = {'small_room': 0.15, 'medium_room': 0.25,
                   'large_room': 0.35, 'hall': 0.45}.get(level, 0.2)

        return ((1 - dry_wet) * signal + dry_wet * reverbed).astype(np.float32)

    def _generate_impulse_response(self, room_type: str) -> np.ndarray:
        """Generate synthetic room impulse response."""
        params = {
            'small_room': (0.2, 0.5, 800),
            'medium_room': (0.4, 0.6, 2000),
            'large_room': (0.8, 0.7, 5000),
            'hall': (1.5, 0.8, 10000),
        }
        rt60, density, length = params.get(room_type, (0.3, 0.5, 1000))

        ir = np.random.randn(length).astype(np.float32) * density
        decay = np.exp(-3.0 * np.arange(length) / (rt60 * self.config.sample_rate))
        ir *= decay

        ir[0] = 1.0

        early_reflections = [
            (int(0.01 * self.config.sample_rate), 0.5),
            (int(0.015 * self.config.sample_rate), 0.3),
            (int(0.025 * self.config.sample_rate), 0.2),
        ]
        for delay, amplitude in early_reflections:
            if delay < length:
                ir[delay] += amplitude

        return ir / np.max(np.abs(ir))

    # --- Speaker simulation ---

    def _generate_speaker_profiles(self) -> List[dict]:
        """Generate diverse speaker voice profiles."""
        profiles = []
        for i in range(self.config.num_speakers):
            gender = 'male' if i % 2 == 0 else 'female'
            base_f0 = np.random.uniform(80, 170) if gender == 'male' else np.random.uniform(160, 300)

            profiles.append({
                'id': i,
                'gender': gender,
                'f0': base_f0,
                'formant_scale': np.random.uniform(0.8, 1.2),
                'jitter': np.random.uniform(0.005, 0.03),
                'shimmer': np.random.uniform(0.01, 0.05),
                'breathiness': np.random.uniform(0.01, 0.1),
                'nasality': np.random.uniform(0.0, 0.3),
            })

        return profiles

    # --- Utility ---

    def _generate_silence_samples(self) -> int:
        """Generate silence/near-silence samples for negative class."""
        silence_dir = self.output_dir / '_silence'
        silence_dir.mkdir(exist_ok=True)
        count = 0

        for i in range(self.config.silence_samples):
            length = int(self.config.sample_rate * self.config.duration_s)
            noise_level = np.random.uniform(0.0001, 0.01)
            signal = (np.random.randn(length) * noise_level).astype(np.float32)
            np.save(str(silence_dir / f'silence_{i:05d}.npy'), signal)
            count += 1

        return count

    def _generate_noise_only_samples(self) -> int:
        """Generate noise-only samples for negative class."""
        noise_dir = self.output_dir / '_noise'
        noise_dir.mkdir(exist_ok=True)
        count = 0

        for i in range(self.config.noise_samples):
            length = int(self.config.sample_rate * self.config.duration_s)
            noise_type = np.random.choice(self.config.noise_types)
            generator = self._noise_generators.get(noise_type, self._white_noise)
            signal = generator(length)
            volume = np.random.uniform(0.1, 0.8)
            signal *= volume
            np.save(str(noise_dir / f'noise_{noise_type}_{i:05d}.npy'), signal)
            count += 1

        return count

    def _generate_unknown_samples(self) -> int:
        """Generate unknown-word samples (words not in vocabulary)."""
        unknown_dir = self.output_dir / '_unknown'
        unknown_dir.mkdir(exist_ok=True)

        unknown_words = [
            'hello', 'world', 'computer', 'phone', 'internet', 'music',
            'weather', 'time', 'search', 'help', 'stop', 'start',
            'play', 'pause', 'next', 'previous', 'volume', 'up', 'down',
            'left', 'right', 'forward', 'backward', 'navigate', 'home',
            'settings', 'profile', 'about', 'contact', 'email',
            'calendar', 'reminder', 'alarm', 'timer', 'note', 'photo',
            'document', 'file', 'folder', 'delete', 'copy', 'paste',
        ]

        count = 0
        samples_per_word = max(1, self.config.noise_samples // len(unknown_words))

        for word in unknown_words:
            for i in range(samples_per_word):
                speaker = self._speaker_profiles[i % len(self._speaker_profiles)]
                signal = self._synthesize_keyword(word, speaker)
                if np.random.random() > 0.5:
                    noise_type = np.random.choice(self.config.noise_types)
                    snr = np.random.uniform(*self.config.snr_range_db)
                    signal = self._add_noise(signal, noise_type, snr)
                np.save(str(unknown_dir / f'unknown_{word}_{i:04d}.npy'),
                        signal.astype(np.float32))
                count += 1

        return count

    def _create_manifest(self, stats: Dict[str, int]) -> Dict:
        """Create a manifest file describing the generated dataset."""
        manifest = {
            'config': {
                'sample_rate': self.config.sample_rate,
                'duration_s': self.config.duration_s,
                'num_speakers': self.config.num_speakers,
                'noise_types': self.config.noise_types,
            },
            'keywords': list(PLATFORM_KEYWORDS.keys()),
            'num_keywords': len(PLATFORM_KEYWORDS),
            'samples_per_keyword': stats,
            'total_samples': sum(stats.values()),
            'output_dir': str(self.output_dir),
        }

        with open(self.output_dir / 'manifest.json', 'w') as f:
            json.dump(manifest, f, indent=2)

        return manifest
