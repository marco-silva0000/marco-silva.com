import os

from django.db import models
from django.utils.translation import gettext_lazy as _
from photologue.models import Gallery, Photo


def raw_upload_path(instance, filename):
    return os.path.join("photologue", "raws", filename)


def watermarked_upload_path(instance, filename):
    return os.path.join("photologue", "watermarked", filename)


def web_upload_path(instance, filename):
    return os.path.join("photologue", "web", filename)


class GalleryExtension(models.Model):
    """Extends photologue Gallery with type and metadata."""

    class GalleryType(models.TextChoices):
        CURATED = "curated", _("Curated")
        DAY_TRIP = "day_trip", _("Day Trip")

    gallery = models.OneToOneField(
        Gallery,
        on_delete=models.CASCADE,
        related_name="extension",
        verbose_name=_("gallery"),
    )
    gallery_type = models.CharField(
        _("type"),
        max_length=10,
        choices=GalleryType.choices,
        default=GalleryType.CURATED,
    )
    date = models.DateField(_("date"), null=True, blank=True, help_text=_("Date of the trip/shoot."))

    class Meta:
        verbose_name = _("gallery extension")
        verbose_name_plural = _("gallery extensions")

    def __str__(self):
        return f"{self.get_gallery_type_display()}: {self.gallery.title}"


class PhotoExtension(models.Model):
    """Extends photologue Photo with RAW file, EXIF metadata, and sales info."""

    photo = models.OneToOneField(
        Photo,
        on_delete=models.CASCADE,
        related_name="extension",
        verbose_name=_("photo"),
    )

    # RAW file
    raw_file = models.FileField(
        _("RAW file"),
        upload_to=raw_upload_path,
        blank=True,
        help_text=_("Original camera RAW file (CR3, ARW, NEF, etc.)"),
    )

    # Versions
    watermarked_image = models.ImageField(_("watermarked image"), upload_to=watermarked_upload_path, blank=True)
    web_image = models.ImageField(_("web-optimized image"), upload_to=web_upload_path, blank=True)

    # EXIF / metadata
    camera_make = models.CharField(_("camera make"), max_length=100, blank=True)
    camera_model = models.CharField(_("camera model"), max_length=100, blank=True)
    lens = models.CharField(_("lens"), max_length=200, blank=True)
    focal_length = models.CharField(_("focal length"), max_length=20, blank=True)
    aperture = models.CharField(_("aperture"), max_length=20, blank=True)
    shutter_speed = models.CharField(_("shutter speed"), max_length=20, blank=True)
    iso = models.PositiveIntegerField(_("ISO"), null=True, blank=True)

    # Location
    latitude = models.DecimalField(_("latitude"), max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(_("longitude"), max_digits=9, decimal_places=6, null=True, blank=True)
    location_name = models.CharField(_("location name"), max_length=200, blank=True)

    # Sales
    is_for_sale = models.BooleanField(_("available for sale"), default=False)
    price_raw = models.DecimalField(
        _("RAW price"),
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Price for the RAW file download."),
    )

    # License
    cc_license = models.BooleanField(
        _("CC BY-NC-SA license"),
        default=False,
        help_text=_("Apply Creative Commons Attribution-NonCommercial-ShareAlike license and watermark."),
    )

    # Processing status
    class ProcessingStatus(models.TextChoices):
        PENDING = "pending", _("Pending")
        PROCESSING = "processing", _("Processing")
        DONE = "done", _("Done")
        FAILED = "failed", _("Failed")

    processing_status = models.CharField(
        _("processing status"),
        max_length=10,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("photo extension")
        verbose_name_plural = _("photo extensions")

    def __str__(self):
        return f"Extension: {self.photo.title}"

    @property
    def has_location(self):
        return self.latitude is not None and self.longitude is not None

    @property
    def exif_summary(self):
        parts = []
        if self.camera_model:
            parts.append(self.camera_model)
        if self.lens:
            parts.append(self.lens)
        settings = " · ".join(
            filter(
                None,
                [
                    self.focal_length,
                    f"f/{self.aperture}" if self.aperture else None,
                    self.shutter_speed,
                    f"ISO {self.iso}" if self.iso else None,
                ],
            )
        )
        if settings:
            parts.append(settings)
        return " — ".join(parts)
