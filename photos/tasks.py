import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def process_photo_task(self, photo_extension_id):
    """Async photo processing: EXIF extraction, web image, watermark."""
    from .models import PhotoExtension
    from .processing import process_photo

    try:
        ext = PhotoExtension.objects.get(id=photo_extension_id)
    except PhotoExtension.DoesNotExist:
        logger.error("PhotoExtension %s not found", photo_extension_id)
        return

    try:
        process_photo(ext)
        logger.info("Processed photo: %s", ext.photo.title)
    except Exception as exc:
        logger.exception("Failed to process photo %s", photo_extension_id)
        raise self.retry(exc=exc)
