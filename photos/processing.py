import logging
import math
from io import BytesIO

import exifread
from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

WEB_MAX_SIZE = 1920
AUTHOR = "Marco Silva"


def _get_font(size):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default(size=size)


def _open_photo_image(photo):
    photo.image.open("rb")
    img = Image.open(photo.image.file).convert("RGB")
    photo.image.close()
    return img


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

    lat = _convert_gps(tags.get("GPS GPSLatitude"), tags.get("GPS GPSLatitudeRef"))
    lon = _convert_gps(tags.get("GPS GPSLongitude"), tags.get("GPS GPSLongitudeRef"))
    if lat is not None:
        photo_extension.latitude = lat
    if lon is not None:
        photo_extension.longitude = lon

    photo_extension.save()


def _convert_gps(coord_tag, ref_tag):
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


def _exif_line(ext):
    """Build a short EXIF string like 'f/2.8 · 1/250s · ISO 400'."""
    parts = []
    if ext.aperture:
        parts.append(f"f/{ext.aperture}")
    if ext.shutter_speed:
        parts.append(f"{ext.shutter_speed}s")
    if ext.iso:
        parts.append(f"ISO {ext.iso}")
    return " · ".join(parts)


def generate_web_image(photo_extension):
    """Generate a web-optimized version (max 1920px, quality 85)."""
    try:
        img = _open_photo_image(photo_extension.photo)
    except Exception:
        logger.exception("Failed to open image for web version: %s", photo_extension.photo.title)
        return

    img.thumbnail((WEB_MAX_SIZE, WEB_MAX_SIZE), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    filename = f"web_{photo_extension.photo.slug}.jpg"
    photo_extension.web_image.save(filename, ContentFile(buf.getvalue()), save=False)


def _draw_standard_watermark(img, ext):
    """Standard watermark: © Author + EXIF in bottom-right corner."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font_size = max(14, img.width // 40)
    font = _get_font(font_size)
    small_font = _get_font(max(12, font_size - 4))

    lines = [f"© {AUTHOR}"]
    exif = _exif_line(ext)
    if exif:
        lines.append(exif)

    y = img.height - 20
    for line in reversed(lines):
        f = small_font if line != lines[0] else font
        bbox = draw.textbbox((0, 0), line, font=f)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        y -= th
        draw.text((img.width - tw - 20, y), line, font=f, fill=(255, 255, 255, 140))
        y -= 4

    return Image.alpha_composite(img, overlay)


def _draw_cc_watermark(img, ext):
    """CC BY-NC-SA watermark: © Author + EXIF + license text."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font_size = max(14, img.width // 40)
    font = _get_font(font_size)
    small_font = _get_font(max(12, font_size - 4))

    lines = [f"© {AUTHOR}"]
    exif = _exif_line(ext)
    if exif:
        lines.append(exif)
    lines.append("CC BY-NC-SA 4.0")

    y = img.height - 20
    for line in reversed(lines):
        f = small_font if line != lines[0] else font
        bbox = draw.textbbox((0, 0), line, font=f)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        y -= th
        draw.text((img.width - tw - 20, y), line, font=f, fill=(255, 255, 255, 140))
        y -= 4

    return Image.alpha_composite(img, overlay)


def _draw_commercial_watermark(img, ext):
    """Commercial watermark: diagonal repeating text across the entire image."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font_size = max(20, img.width // 20)
    font = _get_font(font_size)
    text = f"© {AUTHOR}"

    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    # Tile diagonally across the image
    step_x = tw + font_size * 3
    step_y = th + font_size * 4
    diagonal = int(math.sqrt(img.width**2 + img.height**2))

    # Create a larger overlay to rotate
    big = Image.new("RGBA", (diagonal * 2, diagonal * 2), (0, 0, 0, 0))
    big_draw = ImageDraw.Draw(big)

    for y in range(0, diagonal * 2, step_y):
        for x in range(0, diagonal * 2, step_x):
            big_draw.text((x, y), text, font=font, fill=(255, 255, 255, 50))

    big = big.rotate(30, expand=False, center=(diagonal, diagonal))

    # Crop to image size from center
    cx, cy = diagonal, diagonal
    left = cx - img.width // 2
    top = cy - img.height // 2
    cropped = big.crop((left, top, left + img.width, top + img.height))

    return Image.alpha_composite(img, cropped)


def generate_watermark(photo_extension):
    """Generate watermarked version based on photo flags."""
    try:
        img = _open_photo_image(photo_extension.photo).convert("RGBA")
    except Exception:
        logger.exception("Failed to open image for watermark: %s", photo_extension.photo.title)
        return

    ext = photo_extension

    if ext.cc_license:
        watermarked = _draw_cc_watermark(img, ext)
    else:
        watermarked = _draw_commercial_watermark(img, ext)

    watermarked = watermarked.convert("RGB")
    buf = BytesIO()
    watermarked.save(buf, format="JPEG", quality=85)
    filename = f"wm_{photo_extension.photo.slug}.jpg"
    photo_extension.watermarked_image.save(filename, ContentFile(buf.getvalue()), save=False)


def process_photo(photo_extension):
    """Run full processing pipeline on a photo extension."""
    photo_extension.processing_status = "processing"
    photo_extension.save(update_fields=["processing_status"])

    try:
        extract_exif(photo_extension)
        generate_web_image(photo_extension)
        generate_watermark(photo_extension)
        photo_extension.processing_status = "done"
    except Exception:
        logger.exception("Processing failed for %s", photo_extension)
        photo_extension.processing_status = "failed"

    photo_extension.save()
