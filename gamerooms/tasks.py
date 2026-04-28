from datetime import timedelta

from celery import shared_task
from django.utils.timezone import now


@shared_task
def cleanup_old_rooms():
    from .models import Room

    cutoff = now() - timedelta(hours=24)
    deleted, _ = Room.objects.filter(created_at__lt=cutoff).delete()
    return f"Deleted {deleted} old rooms"
