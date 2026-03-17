"""
Model Trainer — complete training pipeline for keyword spotting models.

Handles model compilation, training with callbacks, learning rate scheduling,
early stopping, checkpointing, and evaluation.
"""
import os
import json
import time
import logging
import numpy as np
from pathlib import Path
from typing import Optional, Dict, List, Tuple

try:
    import tensorflow as tf
    from tensorflow import keras
    HAS_TF = True
except ImportError:
    HAS_TF = False

from ..engine.model_architecture import build_model, ModelConfig
from ..engine.inference_engine import InferenceEngine
from .dataset_builder import DatasetBuilder

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).resolve().parent.parent.parent / 'voice_models'


class TrainingConfig:
    """Configuration for model training."""

    def __init__(self,
                 architecture: str = 'ds_cnn',
                 epochs: int = 100,
                 batch_size: int = 64,
                 learning_rate: float = 0.001,
                 lr_schedule: str = 'cosine',
                 warmup_epochs: int = 5,
                 weight_decay: float = 1e-4,
                 label_smoothing: float = 0.1,
                 early_stopping_patience: int = 15,
                 reduce_lr_patience: int = 5,
                 min_lr: float = 1e-6,
                 use_class_weights: bool = True,
                 mixed_precision: bool = False,
                 target_frames: int = 98,
                 num_mel_bins: int = 80,
                 checkpoint_dir: Optional[str] = None):
        self.architecture = architecture
        self.epochs = epochs
        self.batch_size = batch_size
        self.learning_rate = learning_rate
        self.lr_schedule = lr_schedule
        self.warmup_epochs = warmup_epochs
        self.weight_decay = weight_decay
        self.label_smoothing = label_smoothing
        self.early_stopping_patience = early_stopping_patience
        self.reduce_lr_patience = reduce_lr_patience
        self.min_lr = min_lr
        self.use_class_weights = use_class_weights
        self.mixed_precision = mixed_precision
        self.target_frames = target_frames
        self.num_mel_bins = num_mel_bins
        self.checkpoint_dir = checkpoint_dir or str(MODEL_DIR / 'checkpoints')


class ModelTrainer:
    """
    Complete training pipeline for keyword spotting models.

    Features:
    - Multi-architecture support (DS-CNN, Attention-RNN, TC-ResNet, Conformer)
    - Cosine annealing with warm restarts learning rate schedule
    - Label smoothing for better generalization
    - Mixed precision training for faster GPU training
    - Class-weighted loss for imbalanced datasets
    - Comprehensive callbacks (checkpointing, early stopping, TensorBoard)
    - Post-training quantization and TF Lite export
    - Evaluation with per-class metrics
    """

    def __init__(self, config: Optional[TrainingConfig] = None,
                 dataset_builder: Optional[DatasetBuilder] = None):
        self.config = config or TrainingConfig()
        self.dataset_builder = dataset_builder or DatasetBuilder()

        self.model: Optional[keras.Model] = None
        self.history = None
        self.inference_engine = InferenceEngine()

        self._model_dir = MODEL_DIR
        self._model_dir.mkdir(parents=True, exist_ok=True)

        if self.config.mixed_precision and HAS_TF:
            tf.keras.mixed_precision.set_global_policy('mixed_float16')

    def build_model(self, num_keywords: Optional[int] = None) -> keras.Model:
        """Build the model architecture."""
        if not HAS_TF:
            raise ImportError("TensorFlow required for training")

        num_keywords = num_keywords or self.dataset_builder.num_classes

        model_config = ModelConfig(
            input_shape=(self.config.target_frames, self.config.num_mel_bins, 1),
            num_keywords=num_keywords,
            dropout_rate=0.3,
        )

        self.model = build_model(self.config.architecture, model_config)
        logger.info("Built %s model with %d params",
                     self.config.architecture, self.model.count_params())
        return self.model

    def compile_model(self, model: Optional[keras.Model] = None):
        """Compile model with optimizer, loss, and metrics."""
        model = model or self.model
        if model is None:
            raise ValueError("No model to compile")

        optimizer = self._build_optimizer()

        if self.config.architecture == 'multi_head':
            model.compile(
                optimizer=optimizer,
                loss={
                    'wake_word': keras.losses.BinaryCrossentropy(),
                    'command': keras.losses.CategoricalCrossentropy(
                        label_smoothing=self.config.label_smoothing
                    ),
                    'confidence': keras.losses.BinaryCrossentropy(),
                },
                loss_weights={'wake_word': 2.0, 'command': 1.0, 'confidence': 0.5},
                metrics={
                    'wake_word': ['accuracy', keras.metrics.AUC(name='auc')],
                    'command': ['accuracy'],
                    'confidence': ['accuracy'],
                },
            )
        else:
            model.compile(
                optimizer=optimizer,
                loss=keras.losses.CategoricalCrossentropy(
                    label_smoothing=self.config.label_smoothing
                ),
                metrics=[
                    'accuracy',
                    keras.metrics.TopKCategoricalAccuracy(k=3, name='top3_acc'),
                    keras.metrics.AUC(name='auc', multi_label=True),
                ],
            )

        self.model = model

    def train(self, train_data=None, val_data=None) -> Dict:
        """
        Execute the full training pipeline.
        Returns training history and evaluation results.
        """
        if self.model is None:
            self.build_model()
            self.compile_model()

        if train_data is None or val_data is None:
            train_data, val_data, _ = self.dataset_builder.build_all_datasets(
                batch_size=self.config.batch_size,
                target_frames=self.config.target_frames,
            )

        callbacks = self._build_callbacks()

        class_weights = None
        if self.config.use_class_weights:
            class_weights = self.dataset_builder.get_class_weights()

        logger.info("Starting training: %s, %d epochs, batch_size=%d",
                     self.config.architecture, self.config.epochs, self.config.batch_size)
        start_time = time.time()

        self.history = self.model.fit(
            train_data,
            validation_data=val_data,
            epochs=self.config.epochs,
            callbacks=callbacks,
            class_weight=class_weights,
            verbose=1,
        )

        training_time = time.time() - start_time
        logger.info("Training complete in %.1f seconds", training_time)

        results = {
            'architecture': self.config.architecture,
            'epochs_completed': len(self.history.history.get('loss', [])),
            'training_time_s': training_time,
            'final_train_loss': float(self.history.history['loss'][-1]),
            'final_val_loss': float(self.history.history.get('val_loss', [0])[-1]),
            'final_train_acc': float(self.history.history.get('accuracy', [0])[-1]),
            'final_val_acc': float(self.history.history.get('val_accuracy', [0])[-1]),
            'best_val_acc': float(max(self.history.history.get('val_accuracy', [0]))),
            'num_params': self.model.count_params(),
        }

        self._save_training_results(results)
        return results

    def evaluate(self, test_data=None) -> Dict:
        """Evaluate model on test data with per-class metrics."""
        if self.model is None:
            raise ValueError("No trained model to evaluate")

        if test_data is None:
            _, _, test_data = self.dataset_builder.build_all_datasets(
                batch_size=self.config.batch_size,
            )

        results = self.model.evaluate(test_data, return_dict=True, verbose=1)
        logger.info("Evaluation results: %s", results)
        return results

    def export_model(self, name: Optional[str] = None,
                      quantization: str = 'dynamic') -> Dict[str, str]:
        """
        Export model in multiple formats:
        - SavedModel
        - H5
        - TF Lite (with quantization)
        """
        if self.model is None:
            raise ValueError("No model to export")

        name = name or f'{self.config.architecture}_keyword_spotter'
        exports = {}

        saved_model_path = str(self._model_dir / name / 'saved_model')
        self.model.save(saved_model_path)
        exports['saved_model'] = saved_model_path

        h5_path = str(self._model_dir / f'{name}.h5')
        self.model.save(h5_path)
        exports['h5'] = h5_path

        self.inference_engine._tf_models[name] = self.model
        for quant_mode in ['none', 'dynamic', 'float16']:
            tflite_path = self.inference_engine.convert_to_tflite(
                name, quantization=quant_mode
            )
            if tflite_path:
                exports[f'tflite_{quant_mode}'] = tflite_path

        metadata_path = str(self._model_dir / f'{name}_metadata.json')
        metadata = {
            'name': name,
            'architecture': self.config.architecture,
            'num_params': self.model.count_params(),
            'input_shape': list(self.model.input_shape[1:]),
            'num_classes': self.model.output_shape[-1] if not isinstance(self.model.output_shape, dict) else None,
            'keywords': list(self.dataset_builder.label_map.keys()),
            'exports': exports,
        }
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        exports['metadata'] = metadata_path

        logger.info("Model exported to: %s", exports)
        return exports

    def _build_optimizer(self):
        """Build optimizer with learning rate schedule."""
        if self.config.lr_schedule == 'cosine':
            lr_schedule = keras.optimizers.schedules.CosineDecayRestarts(
                initial_learning_rate=self.config.learning_rate,
                first_decay_steps=self.config.epochs // 3,
                t_mul=2.0,
                m_mul=0.9,
                alpha=self.config.min_lr,
            )
        elif self.config.lr_schedule == 'exponential':
            lr_schedule = keras.optimizers.schedules.ExponentialDecay(
                initial_learning_rate=self.config.learning_rate,
                decay_steps=1000,
                decay_rate=0.96,
            )
        else:
            lr_schedule = self.config.learning_rate

        return keras.optimizers.Adam(
            learning_rate=lr_schedule,
            weight_decay=self.config.weight_decay if self.config.weight_decay > 0 else None,
        )

    def _build_callbacks(self) -> List:
        """Build training callbacks."""
        checkpoint_dir = Path(self.config.checkpoint_dir)
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        callbacks = [
            keras.callbacks.ModelCheckpoint(
                filepath=str(checkpoint_dir / 'best_model.keras'),
                monitor='val_accuracy',
                mode='max',
                save_best_only=True,
                verbose=1,
            ),
            keras.callbacks.EarlyStopping(
                monitor='val_loss',
                patience=self.config.early_stopping_patience,
                restore_best_weights=True,
                verbose=1,
            ),
            keras.callbacks.ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=self.config.reduce_lr_patience,
                min_lr=self.config.min_lr,
                verbose=1,
            ),
            keras.callbacks.CSVLogger(
                str(self._model_dir / 'training_log.csv'),
                append=True,
            ),
        ]

        tensorboard_dir = self._model_dir / 'tensorboard'
        tensorboard_dir.mkdir(exist_ok=True)
        callbacks.append(keras.callbacks.TensorBoard(
            log_dir=str(tensorboard_dir),
            histogram_freq=1,
            update_freq='epoch',
        ))

        return callbacks

    def _save_training_results(self, results: Dict):
        """Save training results to JSON."""
        results_path = self._model_dir / 'training_results.json'
        existing = []
        if results_path.exists():
            with open(results_path) as f:
                existing = json.load(f)
        existing.append(results)
        with open(results_path, 'w') as f:
            json.dump(existing, f, indent=2)
