import os

import redis
from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand

from gamerooms.models import Room


class Command(BaseCommand):
    help = "Clear all game rooms and sessions"

    def handle(self, *args, **options):
        rooms_deleted, _ = Room.objects.all().delete()
        sessions_deleted, _ = Session.objects.all().delete()

        # Clear game state from Valkey
        url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
        r = redis.from_url(url)
        keys = r.keys("emojinary:game:*")
        if keys:
            r.delete(*keys)

        msg = f"Cleared {rooms_deleted} rooms, {sessions_deleted} sessions, {len(keys)} games"
        self.stdout.write(self.style.SUCCESS(msg))
