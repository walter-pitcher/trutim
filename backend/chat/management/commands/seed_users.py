"""
Django management command to seed real users in the database.
Usage: python manage.py seed_users [--count 20]
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

FIRST_NAMES = [
    'Alex', 'Jordan', 'Sam', 'Taylor', 'Morgan', 'Casey', 'Riley', 'Avery', 'Quinn', 'Parker',
    'Sakura', 'Yuki', 'Hiro', 'Mei', 'Kenji', 'Luna', 'Aria', 'Nova', 'Zara', 'Kai',
    'Emma', 'Liam', 'Olivia', 'Noah', 'Sophia', 'Ethan', 'Isabella', 'Mason', 'Mia', 'William',
]

LAST_NAMES = [
    'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez',
    'Anderson', 'Taylor', 'Thomas', 'Moore', 'Jackson', 'Martin', 'Lee', 'Thompson', 'White', 'Harris',
]

# Default password for seeded users (change in production)
DEFAULT_PASSWORD = 'demo123'


class Command(BaseCommand):
    help = 'Seed the database with real users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=20,
            help='Number of users to create (default: 20)',
        )

    def handle(self, *args, **options):
        count = options['count']
        created = 0
        skipped = 0

        for i in range(count):
            first = FIRST_NAMES[i % len(FIRST_NAMES)]
            last = LAST_NAMES[i % len(LAST_NAMES)]
            username = f'{first}{last}{(i % 10)}'.lower()
            email = f'{username}@example.com'

            if User.objects.filter(username=username).exists():
                skipped += 1
                continue

            User.objects.create_user(
                username=username,
                email=email,
                password=DEFAULT_PASSWORD,
                first_name=first,
                last_name=last,
                title='Developer' if i % 3 == 0 else '',
            )
            created += 1
            self.stdout.write(self.style.SUCCESS(f'Created user: {username}'))

        self.stdout.write(self.style.SUCCESS(f'\nDone. Created {created} users, skipped {skipped} (already exist).'))
        if created > 0:
            self.stdout.write(f'Default password for all seeded users: {DEFAULT_PASSWORD}')
