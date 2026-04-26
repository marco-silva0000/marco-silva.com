import logging

import exifread
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


def extract_exif(photo_extension):
    """Extract EXIF data from the photologue Photo's image file."""
    photo = photo_extension.photo
    try:
        photo.image.open("rb")
        tags = exifread.process_file(photo.image.file, details=False)
        photo.image.close()
    except Exception:
        logger.exception("Failed to read EXIF from %s", photo.title)
        return

    photo_extension.camera_make = str(tags.get("Image Make", ""))[:100]
    photo_extension.camera_model = str(tags.get("Image Model", ""))[:100]
    photo_extension.lens = str(tags.get("EXIF LensModel", ""))[:200]
    photo_extension.focal_length = str(tags.get("EXIF FocalLength", ""))[:20]
    photo_extension.aperture = str(tags.get("EXIF FNumber", ""))[:20]
    photo_extension.shutter_speed = str(tags.get("EXIF ExposureTime", ""))[:20]

    iso_tag = tags.get("EXIF ISOSpeedRatings")
    if iso_tag:
        try:
            photo_extension.iso = int(str(iso_tag))
        except (ValueError, TypeError):
            pass

    # GPS
    lat = _convert_gps(tags.get("GPS GPSLatitude"), tags.get("GPS GPSLatitudeRef"))
    lon = _convert_gps(tags.get("GPS GPSLongitude"), tags.get("GPS GPSLongitudeRef"))
    if lat is not None:
        photo_extension.latitude = lat
    if lon is not None:
        photo_extension.longitude = lon

    photo_extension.save()


def _convert_gps(coord_tag, ref_tag):
    """Convert EXIF GPS coordinates to decimal degrees."""
    if not coord_tag or not ref_tag:
        return None
    try:
        vals = coord_tag.values
        d = float(vals[0].num) / float(vals[0].den)
        m = float(vals[1].num) / float(vals[1].den)
        s = float(vals[2].num) / float(vals[2].den)
        decimal = d + m / 60 + s / 3600
        if str(ref_tag) in ("S", "W"):
            decimal = -decimal
        return round(decimal, 6)
    except (AttributeError, IndexError, ZeroDivisionError):
        return None


def generate_watermark(photo_extension, text="© Marco Silva"):
    """Generate a watermarked version of the photo."""
    photo = photo_extension.photo
    try:
        photo.image.open("rb")
        img = Image.open(photo.image.file).convert("RGBA")
        photo.image.close()
    except Exception:
        logger.exception("Failed to open image for watermark: %s", photo.title)
        return

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Scale font to ~3% of image width
    font_size = max(16, img.width // 30)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
    except OSError:
        font = ImageFont.load_default(size=font_size)

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = img.width - text_w - 20
    y = img.height - text_h - 20

    # Semi-transparent white text
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 128))

    watermarked = Image.alpha_composite(img, overlay).convert("RGB")

    from io import BytesIO

    from django.core.files.base import ContentFile

    buf = BytesIO()
    watermarked.save(buf, format="JPEG", quality=85)
    filename = f"wm_{photo.slug}.jpg"
    photo_extension.watermarked_image.save(filename, ContentFile(buf.getvalue()), save=False)
    photo_extension.save()


def process_photo(photo_extension):
    """Run full processing pipeline on a photo extension."""
    photo_extension.processing_status = "processing"
    photo_extension.save(update_fields=["processing_status"])

    try:
        extract_exif(photo_extension)
        generate_watermark(photo_extension)
        photo_extension.processing_status = "done"
    except Exception:
        logger.exception("Processing failed for %s", photo_extension)
        photo_extension.processing_status = "failed"

    photo_extension.save(update_fields=["processing_status"])
