from django.db.models.signals import post_save
from django.dispatch import receiver
from photologue.models import Photo

from .models import PhotoExtension
from .processing import process_photo


@receiver(post_save, sender=Photo)
def create_photo_extension(sender, instance, created, **kwargs):
    """Auto-create a PhotoExtension when a Photo is created, and process it."""
    if created:
        ext, _ = PhotoExtension.objects.get_or_create(photo=instance)
        process_photo(ext)
