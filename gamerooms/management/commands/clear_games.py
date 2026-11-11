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

        # Clear game state from Valkey / Redis
        url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
        try:
            r = redis.from_url(url)
            keys = list(r.keys("emojinary:game:*")) + list(r.keys("lupus:*"))
            if keys:
                r.delete(*keys)
            cleared_keys_count = len(keys)
        except Exception as e:
            cleared_keys_count = 0
            self.stdout.write(self.style.WARNING(f"Could not connect to Redis: {e}"))

        msg = f"Cleared {rooms_deleted} rooms, {sessions_deleted} sessions, {cleared_keys_count} Redis keys"
        self.stdout.write(self.style.SUCCESS(msg))
