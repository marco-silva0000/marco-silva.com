import logging
import math
from io import BytesIO

import exifread
import qrcode
from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFilter, ImageFont

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


def detect_focus_point(img: Image.Image) -> tuple[int, int]:
    """Lightweight saliency / edge-density detection to locate the visual focus point.

    Downsamples the image to a low-res thumbnail, computes gradient edges, and finds the
    center of mass of high-frequency visual detail with a subtle center bias.
    Returns (focus_x, focus_y) as percentages (0-100).
    """
    thumb = img.copy()
    thumb.thumbnail((120, 120))
    gray = thumb.convert("L")
    edges = gray.filter(ImageFilter.FIND_EDGES)

    w, h = edges.size
    pixels = edges.load()

    total_weight = 0.0
    weighted_x = 0.0
    weighted_y = 0.0
    cx, cy = w / 2.0, h / 2.0

    for y in range(h):
        for x in range(w):
            val = pixels[x, y]
            # Center bias helps avoid giving excess weight to noisy outer corners (e.g. foliage borders)
            dist_sq = ((x - cx) / max(cx, 1.0)) ** 2 + ((y - cy) / max(cy, 1.0)) ** 2
            center_bias = max(0.25, 1.0 - 0.35 * dist_sq)
            weight = (val**1.5) * center_bias
            if weight > 0:
                total_weight += weight
                weighted_x += x * weight
                weighted_y += y * weight

    if total_weight > 0:
        focal_x = int(round((weighted_x / total_weight) / w * 100))
        focal_y = int(round((weighted_y / total_weight) / h * 100))
        return max(10, min(90, focal_x)), max(10, min(90, focal_y))

    return 50, 50


def crop_to_aspect_ratio(
    img: Image.Image,
    target_ratio: float = 4 / 5,
    focus_x: int = 50,
    focus_y: int = 50,
    output_size: tuple[int, int] = (1080, 1350),
) -> Image.Image:
    """Crop image to target aspect ratio (width / height) centered around focal point (0-100%)."""
    img_w, img_h = img.size
    current_ratio = img_w / img_h

    if current_ratio > target_ratio:
        # Wider than 4:5 -> crop horizontal sides
        crop_h = img_h
        crop_w = int(round(crop_h * target_ratio))
        center_x = int(round(img_w * (focus_x / 100.0)))
        left = center_x - crop_w // 2
        left = max(0, min(img_w - crop_w, left))
        top = 0
    else:
        # Taller than 4:5 -> crop vertical sides
        crop_w = img_w
        crop_h = int(round(crop_w / target_ratio))
        center_y = int(round(img_h * (focus_y / 100.0)))
        top = center_y - crop_h // 2
        top = max(0, min(img_h - crop_h, top))
        left = 0

    right = left + crop_w
    bottom = top + crop_h

    cropped = img.crop((left, top, right, bottom))
    return cropped.resize(output_size, Image.Resampling.LANCZOS)


def generate_instagram_crop(photo_extension):
    """Generate 4:5 vertical (1080x1350) crop optimized for Instagram carousels."""
    try:
        img = _open_photo_image(photo_extension.photo)
    except Exception:
        logger.exception("Failed to open image for Instagram crop: %s", photo_extension.photo.title)
        return

    # Auto-detect focus point if still at default and not yet detected
    is_default_focus = photo_extension.crop_focus_x == 50 and photo_extension.crop_focus_y == 50
    if not photo_extension.auto_crop_detected and is_default_focus:
        f_x, f_y = detect_focus_point(img)
        photo_extension.crop_focus_x = f_x
        photo_extension.crop_focus_y = f_y
        photo_extension.auto_crop_detected = True

    cropped = crop_to_aspect_ratio(
        img,
        target_ratio=4 / 5,
        focus_x=photo_extension.crop_focus_x,
        focus_y=photo_extension.crop_focus_y,
        output_size=(1080, 1350),
    )

    buf = BytesIO()
    cropped.save(buf, format="JPEG", quality=90)
    filename = f"ig_{photo_extension.photo.slug}.jpg"
    photo_extension.instagram_image.save(filename, ContentFile(buf.getvalue()), save=False)


def generate_instagram_qr_slide(
    title: str,
    target_url: str,
    subtitle: str = "Scan or screenshot to view full story & high-res map",
    exif_summary: str = "",
) -> BytesIO:
    """Generate a clean 1080x1350 4:5 Instagram carousel end-card with a QR code and post info."""
    canvas = Image.new("RGB", (1080, 1350), color="#121214")
    draw = ImageDraw.Draw(canvas)

    title_font = _get_font(42)
    sub_font = _get_font(24)
    info_font = _get_font(20)
    footer_font = _get_font(28)

    # 1. Header: Title
    clean_title = title[:45] + ("..." if len(title) > 45 else "")
    t_bbox = draw.textbbox((0, 0), clean_title, font=title_font)
    t_w = t_bbox[2] - t_bbox[0]
    draw.text(((1080 - t_w) // 2, 140), clean_title, font=title_font, fill="#ffffff")

    # 2. Subtitle
    s_bbox = draw.textbbox((0, 0), subtitle, font=sub_font)
    s_w = s_bbox[2] - s_bbox[0]
    draw.text(((1080 - s_w) // 2, 210), subtitle, font=sub_font, fill="#9ca3af")

    # 3. QR Code in centered white card
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=12,
        border=2,
    )
    qr.add_data(target_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#111111", back_color="#ffffff").convert("RGB")

    card_pad = 28
    card_w = qr_img.width + card_pad * 2
    card_h = qr_img.height + card_pad * 2
    card_x = (1080 - card_w) // 2
    card_y = 340

    draw.rounded_rectangle(
        [card_x, card_y, card_x + card_w, card_y + card_h],
        radius=24,
        fill="#ffffff",
    )
    canvas.paste(qr_img, (card_x + card_pad, card_y + card_pad))

    # 4. EXIF / Metadata
    if exif_summary:
        e_bbox = draw.textbbox((0, 0), exif_summary, font=info_font)
        e_w = e_bbox[2] - e_bbox[0]
        draw.text(((1080 - e_w) // 2, 1020), exif_summary, font=info_font, fill="#6b7280")

    # 5. Footer URL
    brand_text = "marco-silva.com"
    b_bbox = draw.textbbox((0, 0), brand_text, font=footer_font)
    b_w = b_bbox[2] - b_bbox[0]
    draw.text(((1080 - b_w) // 2, 1150), brand_text, font=footer_font, fill="#e5e7eb")

    buf = BytesIO()
    canvas.save(buf, format="JPEG", quality=92)
    buf.seek(0)
    return buf


def process_photo(photo_extension):
    """Run full processing pipeline on a photo extension."""
    photo_extension.processing_status = "processing"
    photo_extension.save(update_fields=["processing_status"])

    try:
        extract_exif(photo_extension)
        generate_web_image(photo_extension)
        generate_watermark(photo_extension)
        generate_instagram_crop(photo_extension)
        photo_extension.processing_status = "done"
    except Exception:
        logger.exception("Processing failed for %s", photo_extension)
        photo_extension.processing_status = "failed"

    photo_extension.save()
