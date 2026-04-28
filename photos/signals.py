from django.db.models.signals import post_save
from django.dispatch import receiver
from photologue.models import Photo

from .models import PhotoExtension


@receiver(post_save, sender=Photo)
def create_photo_extension(sender, instance, created, **kwargs):
    """Auto-create a PhotoExtension when a Photo is created, and queue processing."""
    if created:
        ext, _ = PhotoExtension.objects.get_or_create(photo=instance)
        try:
            from .tasks import process_photo_task

            process_photo_task.delay(ext.id)
        except Exception:
            # Fallback to sync if Celery/Redis not available
            from .processing import process_photo

            process_photo(ext)
