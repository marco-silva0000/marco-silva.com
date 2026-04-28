from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand

from gamerooms.models import Room


class Command(BaseCommand):
    help = "Clear all game rooms and sessions"

    def handle(self, *args, **options):
        rooms_deleted, _ = Room.objects.all().delete()
        sessions_deleted, _ = Session.objects.all().delete()
        # Clear in-memory game state
        from emojinary.consumers import GAMES

        GAMES.clear()
        self.stdout.write(self.style.SUCCESS(f"Cleared {rooms_deleted} rooms, {sessions_deleted} sessions"))
