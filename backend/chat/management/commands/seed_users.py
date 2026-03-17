"""
Django management command to seed users and companies with full fake information.
Usage: python manage.py seed_users [--count 15] [--companies 5]
"""
import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from chat.models import Room

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

TITLES = [
    'Senior Software Engineer', 'Full Stack Developer', 'DevOps Engineer', 'Frontend Developer',
    'Backend Engineer', 'Data Scientist', 'Product Manager', 'UX Designer', 'Tech Lead',
    'Cloud Architect', 'Mobile Developer', 'Security Engineer', 'QA Engineer',
]

ADDRESSES = [
    '123 Main St, San Francisco, CA 94102',
    '456 Oak Ave, New York, NY 10001',
    '789 Pine Rd, Seattle, WA 98101',
    '321 Elm St, Austin, TX 78701',
    '654 Maple Dr, Denver, CO 80202',
    '987 Cedar Ln, Boston, MA 02101',
    '147 Birch Way, Portland, OR 97201',
    '258 Walnut St, Chicago, IL 60601',
    '369 Spruce Ave, Los Angeles, CA 90001',
    '741 Ash Blvd, Miami, FL 33101',
]

# (lat, lng) for various cities
LOCATIONS = [
    (37.7749, -122.4194),   # San Francisco
    (40.7128, -74.0060),   # New York
    (47.6062, -122.3321),  # Seattle
    (30.2672, -97.7431),   # Austin
    (39.7392, -104.9903),  # Denver
    (42.3601, -71.0589),   # Boston
    (45.5152, -122.6784),  # Portland
    (41.8781, -87.6298),   # Chicago
    (34.0522, -118.2437),  # Los Angeles
    (25.7617, -80.1918),   # Miami
]

COMPANIES = [
    {'name': 'TechFlow Solutions', 'description': 'Enterprise software development and cloud consulting. We build scalable solutions for Fortune 500 companies.'},
    {'name': 'Nexus Labs', 'description': 'AI and machine learning research lab. Pioneering the future of intelligent systems.'},
    {'name': 'CodeCraft Studios', 'description': 'Creative digital agency specializing in web and mobile app development.'},
    {'name': 'DataDrive Inc', 'description': 'Big data analytics and business intelligence. Turning data into decisions.'},
    {'name': 'CloudNine Systems', 'description': 'Cloud infrastructure and DevOps automation. Your infrastructure, simplified.'},
]

DEFAULT_PASSWORD = 'demo123'


class Command(BaseCommand):
    help = 'Seed the database with users and companies (full fake info)'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=15, help='Number of users to create')
        parser.add_argument('--companies', type=int, default=5, help='Number of companies to create')

    def handle(self, *args, **options):
        user_count = options['count']
        company_count = min(options['companies'], len(COMPANIES))
        created_users = []
        created_rooms = []

        # Create users with full fake info
        for i in range(user_count):
            first = FIRST_NAMES[i % len(FIRST_NAMES)]
            last = LAST_NAMES[i % len(LAST_NAMES)]
            username = f'{first}{last}{(i % 10)}'.lower()
            email = f'{username}@example.com'

            if User.objects.filter(username=username).exists():
                continue

            loc_idx = i % len(LOCATIONS)
            lat, lng = LOCATIONS[loc_idx]
            addr = ADDRESSES[i % len(ADDRESSES)]

            user = User.objects.create_user(
                username=username,
                email=email,
                password=DEFAULT_PASSWORD,
                first_name=first,
                last_name=last,
                title=TITLES[i % len(TITLES)],
                address=addr,
                latitude=Decimal(str(round(lat + random.uniform(-0.1, 0.1), 6))),
                longitude=Decimal(str(round(lng + random.uniform(-0.1, 0.1), 6))),
                github=f'https://github.com/{username}',
                twitter=f'https://twitter.com/{username}',
                facebook=f'https://facebook.com/{username}',
                gmail=f'{username}+work@gmail.com',
                telegram=f'@{username}',
                discord=f'{username}#{1000 + i}',
                whatsapp=f'+1{5550000000 + i}',
            )
            created_users.append(user)
            self.stdout.write(self.style.SUCCESS(f'Created user: {username}'))

        # Users to add to companies (created + existing if we didn't create any)
        users_for_rooms = list(created_users) if created_users else list(User.objects.all()[:20])

        # Create companies (rooms)
        for i in range(company_count):
            comp = COMPANIES[i]
            name = comp['name']
            desc = comp['description']

            room = Room.objects.filter(name=name, is_direct=False).first()
            if room:
                if room.members.count() == 0 and users_for_rooms:
                    for u in users_for_rooms:
                        room.members.add(u)
                    self.stdout.write(self.style.SUCCESS(f'Added members to company: {name}'))
                continue

            creator = users_for_rooms[0] if users_for_rooms else User.objects.first()
            if not creator:
                self.stdout.write(self.style.ERROR('No user to create rooms. Create users first.'))
                return

            room = Room.objects.create(
                name=name,
                description=desc,
                is_direct=False,
                created_by=creator,
            )
            for u in users_for_rooms:
                room.members.add(u)
            created_rooms.append(room)
            self.stdout.write(self.style.SUCCESS(f'Created company: {name}'))

        self.stdout.write(self.style.SUCCESS(
            f'\nDone. Created {len(created_users)} users, {len(created_rooms)} companies.'
        ))
        if created_users:
            self.stdout.write(f'Login with any seeded user (e.g. {created_users[0].username}) / password: {DEFAULT_PASSWORD}')
