"""
Dataset Builder — prepares training/validation/test datasets.

Loads generated audio samples, extracts features, creates TensorFlow
datasets with proper batching, shuffling, and augmentation.
"""
import os
import json
import logging
import numpy as np
from pathlib import Path
from typing import Optional, Dict, List, Tuple

try:
    import tensorflow as tf
    HAS_TF = True
except ImportError:
    HAS_TF = False

from ..dsp.audio_processor import AudioConfig, AudioProcessor
from ..dsp.feature_extraction import FeatureExtractor, FeatureConfig
from ..engine.keyword_spotter import PLATFORM_KEYWORDS
from .augmentation import AudioAugmentor, AugmentationConfig

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / 'voice_training_data'


class DatasetBuilder:
    """
    Build TensorFlow datasets from generated training data.

    Pipeline:
    1. Scan data directory for audio samples
    2. Split into train/validation/test sets
    3. Extract features (MFCC or mel spectrogram)
    4. Apply augmentation (training set only)
    5. Create tf.data.Dataset with batching and prefetching
    """

    def __init__(self, data_dir: Optional[str] = None,
                 audio_config: Optional[AudioConfig] = None,
                 feature_config: Optional[FeatureConfig] = None):
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR
        self.audio_config = audio_config or AudioConfig()
        self.feature_config = feature_config or FeatureConfig(num_mel_bins=80)
        self.processor = AudioProcessor(self.audio_config)
        self.feature_extractor = FeatureExtractor(self.audio_config, self.feature_config)
        self.augmentor = AudioAugmentor()

        self._file_list: List[Tuple[str, int]] = []  # (filepath, label)
        self._label_map = PLATFORM_KEYWORDS.copy()

    def scan_dataset(self) -> Dict[str, int]:
        """Scan data directory and build file index."""
        self._file_list.clear()
        stats = {}

        for keyword_dir in sorted(self.data_dir.iterdir()):
            if not keyword_dir.is_dir():
                continue

            keyword = keyword_dir.name
            label = self._label_map.get(keyword)

            if label is None:
                if keyword in ('_noise', '_unknown'):
                    label = self._label_map.get('_silence', len(self._label_map))
                else:
                    continue

            files = list(keyword_dir.glob('*.npy'))
            for f in files:
                self._file_list.append((str(f), label))

            stats[keyword] = len(files)

        np.random.shuffle(self._file_list)
        logger.info("Scanned %d files across %d classes",
                     len(self._file_list), len(stats))
        return stats

    def split_dataset(self, train_ratio: float = 0.8,
                       val_ratio: float = 0.1,
                       test_ratio: float = 0.1
                       ) -> Tuple[List, List, List]:
        """Split dataset into train/val/test."""
        total = len(self._file_list)
        if total == 0:
            self.scan_dataset()
            total = len(self._file_list)

        train_end = int(total * train_ratio)
        val_end = train_end + int(total * val_ratio)

        train = self._file_list[:train_end]
        val = self._file_list[train_end:val_end]
        test = self._file_list[val_end:]

        logger.info("Split: train=%d, val=%d, test=%d",
                     len(train), len(val), len(test))
        return train, val, test

    def build_tf_dataset(self, file_list: List[Tuple[str, int]],
                          batch_size: int = 64,
                          augment: bool = False,
                          target_frames: int = 98,
                          feature_type: str = 'log_filterbank',
                          shuffle: bool = True) -> 'tf.data.Dataset':
        """
        Build a tf.data.Dataset from file list.
        Returns batched, prefetched dataset ready for training.
        """
        if not HAS_TF:
            raise ImportError("TensorFlow required for tf.data.Dataset")

        files = [f for f, _ in file_list]
        labels = [l for _, l in file_list]
        num_classes = len(self._label_map)

        def load_and_process(idx):
            idx = idx.numpy()
            filepath = files[idx]
            label = labels[idx]

            signal = np.load(filepath).astype(np.float32)
            signal = self.processor.process(signal)

            if augment:
                signal, _ = self.augmentor.augment(signal)

            features = self.feature_extractor.extract_for_keyword_spotting(signal)
            features = self.feature_extractor.pad_or_truncate_features(
                features, target_frames
            )

            if augment and self.augmentor.config.spec_augment:
                if features.ndim == 3:
                    features_2d = features[:, :, 0]
                    features_2d = self.augmentor.augment_spectrogram(features_2d)
                    features = features_2d[:, :, np.newaxis]
                else:
                    features = self.augmentor.augment_spectrogram(features)

            label_one_hot = np.zeros(num_classes, dtype=np.float32)
            label_one_hot[label] = 1.0

            return features.astype(np.float32), label_one_hot

        def tf_load(idx):
            features, label = tf.py_function(
                load_and_process,
                [idx],
                [tf.float32, tf.float32]
            )
            mel_bins = self.feature_config.num_mel_bins
            features.set_shape([target_frames, mel_bins, 1])
            label.set_shape([num_classes])
            return features, label

        indices = tf.data.Dataset.range(len(file_list))

        if shuffle:
            indices = indices.shuffle(buffer_size=min(len(file_list), 10000))

        dataset = indices.map(tf_load, num_parallel_calls=tf.data.AUTOTUNE)
        dataset = dataset.batch(batch_size)
        dataset = dataset.prefetch(tf.data.AUTOTUNE)

        return dataset

    def build_all_datasets(self, batch_size: int = 64,
                            target_frames: int = 98
                            ) -> Tuple['tf.data.Dataset', 'tf.data.Dataset', 'tf.data.Dataset']:
        """Build train, validation, and test datasets."""
        train_files, val_files, test_files = self.split_dataset()

        train_ds = self.build_tf_dataset(
            train_files, batch_size=batch_size, augment=True,
            target_frames=target_frames, shuffle=True
        )
        val_ds = self.build_tf_dataset(
            val_files, batch_size=batch_size, augment=False,
            target_frames=target_frames, shuffle=False
        )
        test_ds = self.build_tf_dataset(
            test_files, batch_size=batch_size, augment=False,
            target_frames=target_frames, shuffle=False
        )

        return train_ds, val_ds, test_ds

    def build_numpy_dataset(self, file_list: List[Tuple[str, int]],
                             target_frames: int = 98,
                             augment: bool = False
                             ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Build numpy arrays (for smaller datasets that fit in memory).
        Returns (features, labels) arrays.
        """
        num_classes = len(self._label_map)
        mel_bins = self.feature_config.num_mel_bins

        features_list = []
        labels_list = []

        for filepath, label in file_list:
            try:
                signal = np.load(filepath).astype(np.float32)
                signal = self.processor.process(signal)

                if augment:
                    signal, _ = self.augmentor.augment(signal)

                feat = self.feature_extractor.extract_for_keyword_spotting(signal)
                feat = self.feature_extractor.pad_or_truncate_features(feat, target_frames)

                features_list.append(feat)

                one_hot = np.zeros(num_classes, dtype=np.float32)
                one_hot[label] = 1.0
                labels_list.append(one_hot)

            except Exception as e:
                logger.warning("Error processing %s: %s", filepath, e)
                continue

        features = np.array(features_list, dtype=np.float32)
        labels = np.array(labels_list, dtype=np.float32)

        logger.info("Built numpy dataset: features=%s, labels=%s",
                     features.shape, labels.shape)
        return features, labels

    def get_class_weights(self) -> Dict[int, float]:
        """Compute class weights for imbalanced dataset handling."""
        if not self._file_list:
            self.scan_dataset()

        label_counts = {}
        for _, label in self._file_list:
            label_counts[label] = label_counts.get(label, 0) + 1

        total = sum(label_counts.values())
        num_classes = len(label_counts)
        weights = {}

        for label, count in label_counts.items():
            weights[label] = total / (num_classes * count)

        return weights

    @property
    def num_classes(self) -> int:
        return len(self._label_map)

    @property
    def label_map(self) -> Dict[str, int]:
        return self._label_map.copy()
