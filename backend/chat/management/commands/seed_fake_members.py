"""
Seed the database with fake company rooms and members for demo purposes.

Usage:
    python manage.py seed_fake_members
    python manage.py seed_fake_members --users 10 --rooms 3
"""
import random
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from chat.models import Room, Channel


FIRST_NAMES = [
    "Alice", "Bob", "Charlie", "Diana", "Ethan", "Fiona", "George", "Hannah",
    "Ivan", "Julia", "Kevin", "Laura", "Max", "Nina", "Oscar", "Paula",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Miller",
    "Davis", "Garcia", "Rodriguez", "Wilson", "Martinez", "Anderson",
]

TITLES = [
    "Senior Engineer", "Staff Engineer", "Tech Lead", "Product Manager",
    "Designer", "QA Engineer", "DevOps Engineer", "Data Scientist",
]

COMPANY_NAMES = [
    "Trutim HQ", "Engineering Guild", "Design Studio",
]


class Command(BaseCommand):
    help = "Create fake users and company rooms so the sidebar has content."

    def add_arguments(self, parser):
        parser.add_argument("--users", type=int, default=12, help="Number of fake users to create")
        parser.add_argument("--rooms", type=int, default=2, help="Number of company rooms to create")

    def handle(self, *args, **options):
        User = get_user_model()
        num_users = options["users"]
        num_rooms = options["rooms"]

        self.stdout.write(self.style.NOTICE(f"Seeding {num_users} users and {num_rooms} company rooms..."))

        # Create or reuse an admin/owner for rooms
        owner = User.objects.filter(is_superuser=True).first() or User.objects.first()
        if not owner:
            owner = User.objects.create_user(username="admin", password="admin123", title="Admin")
            self.stdout.write(self.style.WARNING("Created default admin user: admin / admin123"))

        # Create company rooms if needed
        rooms = list(Room.objects.filter(is_direct=False))
        while len(rooms) < num_rooms:
            name = COMPANY_NAMES[len(rooms) % len(COMPANY_NAMES)]
            room, created = Room.objects.get_or_create(
                name=name,
                is_direct=False,
                defaults={
                    "description": f"{name} demo room",
                    "created_by": owner,
                },
            )
            room.members.add(owner)
            Channel.objects.get_or_create(
                room=room,
                name="general",
                defaults={
                    "description": "General discussion",
                    "is_default": True,
                    "created_by": owner,
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created room: {room.name}"))
            rooms.append(room)

        # Create fake users
        created_users = []
        existing_usernames = set(User.objects.values_list("username", flat=True))
        for i in range(num_users):
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            base_username = f"{first.lower()}.{last.lower()}"
            username = base_username
            suffix = 1
            while username in existing_usernames:
                suffix += 1
                username = f"{base_username}{suffix}"

            user = User.objects.create_user(
                username=username,
                password="password123",
                first_name=first,
                last_name=last,
                title=random.choice(TITLES),
            )
            existing_usernames.add(username)
            created_users.append(user)
            self.stdout.write(f"Created user: {username} / password123")

        # Add all users (existing + new) to all company rooms
        all_members = list(User.objects.all())
        for room in rooms:
            for u in all_members:
                room.members.add(u)
            room.save()
            self.stdout.write(self.style.SUCCESS(f"Room '{room.name}' members: {room.members.count()}"))

        self.stdout.write(self.style.SUCCESS("Seeding complete. You should now see companies and members in the sidebar."))

