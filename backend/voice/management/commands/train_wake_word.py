"""
Django management command to train keyword spotting models.

Usage:
    python manage.py train_wake_word
    python manage.py train_wake_word --architecture conformer --epochs 200
    python manage.py train_wake_word --architecture ds_cnn --batch-size 128 --lr 0.0005
"""
import time
from django.core.management.base import BaseCommand

from voice.training.trainer import ModelTrainer, TrainingConfig
from voice.training.dataset_builder import DatasetBuilder
from voice.models import KeywordSpotterModel


class Command(BaseCommand):
    help = 'Train a keyword spotting model for wake word detection'

    def add_arguments(self, parser):
        parser.add_argument(
            '--architecture', type=str, default='ds_cnn',
            choices=['ds_cnn', 'attention_rnn', 'tc_resnet', 'conformer', 'multi_head'],
            help='Model architecture (default: ds_cnn)',
        )
        parser.add_argument(
            '--epochs', type=int, default=100,
            help='Number of training epochs (default: 100)',
        )
        parser.add_argument(
            '--batch-size', type=int, default=64,
            help='Training batch size (default: 64)',
        )
        parser.add_argument(
            '--lr', type=float, default=0.001,
            help='Learning rate (default: 0.001)',
        )
        parser.add_argument(
            '--data-dir', type=str, default=None,
            help='Path to training data directory',
        )
        parser.add_argument(
            '--activate', action='store_true',
            help='Activate the model after training',
        )
        parser.add_argument(
            '--export', action='store_true', default=True,
            help='Export model to TFLite after training',
        )

    def handle(self, *args, **options):
        config = TrainingConfig(
            architecture=options['architecture'],
            epochs=options['epochs'],
            batch_size=options['batch_size'],
            learning_rate=options['lr'],
        )

        dataset_builder = DatasetBuilder(data_dir=options['data_dir'])

        self.stdout.write(self.style.NOTICE(
            f"Training {config.architecture} model: "
            f"{config.epochs} epochs, batch_size={config.batch_size}, "
            f"lr={config.learning_rate}"
        ))

        scan_stats = dataset_builder.scan_dataset()
        self.stdout.write(f"Dataset: {sum(scan_stats.values())} samples, "
                          f"{len(scan_stats)} classes")

        trainer = ModelTrainer(config=config, dataset_builder=dataset_builder)

        self.stdout.write(self.style.NOTICE("\nBuilding model..."))
        model = trainer.build_model()
        trainer.compile_model()
        model.summary(print_fn=lambda x: self.stdout.write(x))

        self.stdout.write(self.style.NOTICE("\nStarting training..."))
        start = time.time()
        results = trainer.train()
        elapsed = time.time() - start

        self.stdout.write(self.style.SUCCESS(
            f"\nTraining complete in {elapsed:.1f}s"
        ))
        self.stdout.write(f"  Best validation accuracy: {results['best_val_acc']:.4f}")
        self.stdout.write(f"  Final train loss: {results['final_train_loss']:.4f}")
        self.stdout.write(f"  Parameters: {results['num_params']:,}")

        exports = {}
        if options['export']:
            self.stdout.write(self.style.NOTICE("\nExporting model..."))
            exports = trainer.export_model()
            for fmt, path in exports.items():
                self.stdout.write(f"  {fmt}: {path}")

        model_record = KeywordSpotterModel.objects.create(
            name=f'{config.architecture}_{int(time.time())}',
            architecture=config.architecture,
            model_path=exports.get('saved_model', ''),
            tflite_path=exports.get('tflite_dynamic', ''),
            num_parameters=results['num_params'],
            num_keywords=dataset_builder.num_classes,
            accuracy=results['best_val_acc'],
            training_epochs=results['epochs_completed'],
            training_samples=sum(scan_stats.values()),
            is_active=options['activate'],
            metadata=results,
        )

        if options['activate']:
            KeywordSpotterModel.objects.exclude(id=model_record.id).update(is_active=False)
            self.stdout.write(self.style.SUCCESS(
                f"\nModel '{model_record.name}' activated!"
            ))

        self.stdout.write(self.style.SUCCESS(
            f"\nModel registered: {model_record.name}"
        ))
