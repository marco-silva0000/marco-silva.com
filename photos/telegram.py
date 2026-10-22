import json
import logging
import os
import urllib.parse
import urllib.request
import uuid

from django.conf import settings
from photologue.models import Gallery

from .processing import generate_instagram_crop, generate_instagram_qr_slide

logger = logging.getLogger(__name__)

DEFAULT_BOT_TOKEN = "8631365300:AAGNoHW31L3-KVa5iHIQUWIU7KEc-o8wM4s"
DEFAULT_CHAT_ID = "482554635"


def get_telegram_config() -> tuple[str, str]:
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", None) or os.environ.get("TELEGRAM_BOT_TOKEN") or DEFAULT_BOT_TOKEN
    chat_id = getattr(settings, "TELEGRAM_CHAT_ID", None) or os.environ.get("TELEGRAM_CHAT_ID") or DEFAULT_CHAT_ID
    return str(token), str(chat_id)


def _encode_multipart(fields: dict, files: list[tuple[str, str, bytes, str]]) -> tuple[bytes, str]:
    """Encode multipart/form-data using pure standard library."""
    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    body = bytearray()

    for key, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"))
        body.extend(f"{value}\r\n".encode("utf-8"))

    for field_name, filename, file_bytes, content_type in files:
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(
            f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode("utf-8")
        )
        body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
        body.extend(file_bytes)
        body.extend(b"\r\n")

    body.extend(f"--{boundary}--\r\n".encode("utf-8"))
    return bytes(body), f"multipart/form-data; boundary={boundary}"


def dispatch_gallery_to_telegram(gallery: Gallery) -> tuple[bool, str]:
    """Prepare 4:5 Instagram photos + QR code end slide and dispatch as an album to Telegram."""
    token, chat_id = get_telegram_config()
    if not token or not chat_id:
        return False, "Missing Telegram BOT_TOKEN or CHAT_ID configuration"

    photos = list(gallery.photos.filter(is_public=True).order_by("id")[:9])
    if not photos:
        return False, f"Gallery '{gallery.title}' has no public photos to send"

    media_group = []
    files_to_send = []

    # Format caption for first photo
    caption = f"📸 {gallery.title}\n\n"
    if gallery.description:
        caption += f"{gallery.description.strip()}\n\n"
    target_url = f"https://marco-silva.com/photos/galleries/{gallery.slug}/"
    caption += f"🔗 View full photo story & map:\n{target_url}\n\n"
    caption += "#photography #outdoors #landscape #helsinki"

    for idx, photo in enumerate(photos):
        ext = getattr(photo, "extension", None)
        if not ext or not ext.instagram_image:
            from .models import PhotoExtension
            ext, _ = PhotoExtension.objects.get_or_create(photo=photo)
            generate_instagram_crop(ext)
            ext.save()

        attach_key = f"photo_{idx}"
        media_group.append({
            "type": "photo",
            "media": f"attach://{attach_key}",
            "caption": caption if idx == 0 else "",
        })

        ext.instagram_image.open("rb")
        img_bytes = ext.instagram_image.read()
        ext.instagram_image.close()

        files_to_send.append((attach_key, f"{photo.slug}_4x5.jpg", img_bytes, "image/jpeg"))

    # Generate QR slide as the final carousel item
    qr_buf = generate_instagram_qr_slide(
        title=gallery.title,
        target_url=target_url,
        subtitle="Scan or screenshot to view full story & map",
    )
    qr_bytes = qr_buf.getvalue()
    qr_key = f"photo_{len(photos)}"
    media_group.append({
        "type": "photo",
        "media": f"attach://{qr_key}",
    })
    files_to_send.append((qr_key, "qr_slide_4x5.jpg", qr_bytes, "image/jpeg"))

    # Dispatch to Telegram sendMediaGroup endpoint
    url = f"https://api.telegram.org/bot{token}/sendMediaGroup"
    fields = {
        "chat_id": chat_id,
        "media": json.dumps(media_group),
    }

    body_bytes, content_type = _encode_multipart(fields, files_to_send)

    req = urllib.request.Request(
        url,
        data=body_bytes,
        headers={"Content-Type": content_type},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
            if resp_data.get("ok"):
                logger.info("Successfully dispatched Instagram pack for gallery '%s' to Telegram", gallery.title)
                return True, "Dispatched album to Telegram successfully"
            return False, f"Telegram API error: {resp_data.get('description')}"
    except Exception as exc:
        logger.exception("Failed to dispatch to Telegram: %s", exc)
        return False, str(exc)
