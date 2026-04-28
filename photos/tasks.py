import logging

from celery import shared_task
from django.core.mail import send_mail

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


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def send_purchase_request_email(self, photo_title, photo_url, requester_email, message):
    """Send purchase request notification email."""
    import os

    to_email = os.environ.get("CONTACT_EMAIL", "inbox@marco-silva.com")

    try:
        send_mail(
            subject=f"Photo request: {photo_title}",
            message=(
                f"Someone wants to buy a photo!\n\n"
                f"Photo: {photo_title}\n"
                f"URL: {photo_url}\n"
                f"From: {requester_email}\n"
                f"Message: {message or '(no message)'}\n"
            ),
            from_email="noreply@marco-silva.com",
            recipient_list=[to_email],
            fail_silently=False,
        )
        logger.info("Sent purchase request email for %s", photo_title)
    except Exception as exc:
        logger.exception("Failed to send purchase request email")
        raise self.retry(exc=exc)
