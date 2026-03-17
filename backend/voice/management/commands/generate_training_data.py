"""
Django management command to generate training data for keyword spotting.

Usage:
    python manage.py generate_training_data
    python manage.py generate_training_data --samples-per-keyword 5000
    python manage.py generate_training_data --speakers 100 --keywords trutim call message
"""
import time
from django.core.management.base import BaseCommand

from voice.training.data_generator import TrainingDataGenerator, GeneratorConfig
from voice.models import TrainingDataset


class Command(BaseCommand):
    help = 'Generate synthetic training data for keyword spotting'

    def add_arguments(self, parser):
        parser.add_argument(
            '--samples-per-keyword', type=int, default=2000,
            help='Number of samples to generate per keyword (default: 2000)',
        )
        parser.add_argument(
            '--speakers', type=int, default=50,
            help='Number of simulated speakers (default: 50)',
        )
        parser.add_argument(
            '--keywords', nargs='*', default=None,
            help='Specific keywords to generate (default: all)',
        )
        parser.add_argument(
            '--output-dir', type=str, default=None,
            help='Output directory for training data',
        )
        parser.add_argument(
            '--sample-rate', type=int, default=16000,
            help='Audio sample rate in Hz (default: 16000)',
        )

    def handle(self, *args, **options):
        config = GeneratorConfig(
            samples_per_keyword=options['samples_per_keyword'],
            num_speakers=options['speakers'],
            sample_rate=options['sample_rate'],
        )

        generator = TrainingDataGenerator(
            config=config,
            output_dir=options['output_dir'],
        )

        self.stdout.write(self.style.NOTICE(
            f"Generating training data: "
            f"{config.samples_per_keyword} samples/keyword, "
            f"{config.num_speakers} speakers"
        ))

        start = time.time()
        stats = generator.generate_full_dataset(keywords=options['keywords'])
        elapsed = time.time() - start

        total = sum(stats.values())
        self.stdout.write(self.style.SUCCESS(
            f"\nGeneration complete in {elapsed:.1f}s"
        ))
        self.stdout.write(f"Total samples: {total}")

        for keyword, count in sorted(stats.items()):
            self.stdout.write(f"  {keyword}: {count} samples")

        TrainingDataset.objects.create(
            name=f'synthetic_{int(time.time())}',
            data_dir=str(generator.output_dir),
            num_samples=total,
            num_keywords=len(stats),
            sample_rate=config.sample_rate,
            duration_per_sample_s=config.duration_s,
            manifest=stats,
        )

        self.stdout.write(self.style.SUCCESS("Dataset registered in database."))
