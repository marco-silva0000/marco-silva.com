import logging

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from photologue.admin import GalleryAdmin as PhotologueGalleryAdmin
from photologue.admin import PhotoAdmin as PhotologuePhotoAdmin
from photologue.models import Gallery, Photo

from .models import GalleryExtension, PhotoExtension
from .processing import generate_instagram_crop

logger = logging.getLogger(__name__)


class PhotoExtensionInline(admin.StackedInline):
    model = PhotoExtension
    extra = 0
    readonly_fields = ("instagram_preview", "auto_crop_detected")
    fieldsets = (
        ("RAW File", {"fields": ("raw_file", "processing_status")}),
        (
            "Versions & Instagram",
            {
                "fields": (
                    "watermarked_image",
                    "web_image",
                    "instagram_image",
                    "instagram_preview",
                )
            },
        ),
        (
            "Framing & Crop Focus",
            {
                "fields": (
                    "crop_focus_x",
                    "crop_focus_y",
                    "auto_crop_detected",
                ),
                "description": _(
                    "Adjust focal point for 4:5 vertical Instagram crops. "
                    "0=top/left, 50=center, 100=bottom/right. "
                    "Saving regenerates the crop automatically."
                ),
            },
        ),
        (
            "EXIF Data",
            {
                "classes": ("collapse",),
                "fields": (
                    "camera_make",
                    "camera_model",
                    "lens",
                    "focal_length",
                    "aperture",
                    "shutter_speed",
                    "iso",
                ),
            },
        ),
        ("Location", {"classes": ("collapse",), "fields": ("latitude", "longitude", "location_name")}),
        ("Sales", {"classes": ("collapse",), "fields": ("is_for_sale", "price_raw", "cc_license")}),
    )

    def instagram_preview(self, instance):
        if instance and instance.instagram_image:
            img_style = "height: 180px; width: 144px; object-fit: cover; border-radius: 4px; border: 1px solid #ddd;"
            return format_html(
                '<div style="margin-top: 5px;">'
                '<img src="{}" style="{}">'
                '<p style="font-size: 11px; color: #666; margin-top: 3px;">4:5 Instagram vertical (1080x1350)</p>'
                "</div>",
                instance.instagram_image.url,
                img_style,
            )
        return _("No Instagram crop generated yet.")

    instagram_preview.short_description = _("Instagram 4:5 Preview")


class GalleryExtensionInline(admin.StackedInline):
    model = GalleryExtension
    extra = 0


class ExtendedPhotoAdmin(PhotologuePhotoAdmin):
    inlines = list(PhotologuePhotoAdmin.inlines) + [PhotoExtensionInline]
    actions = ["regenerate_instagram_crops"]

    @admin.action(description=_("Regenerate 4:5 Instagram crops for selected photos"))
    def regenerate_instagram_crops(self, request, queryset):
        count = 0
        for photo in queryset:
            ext, _ = PhotoExtension.objects.get_or_create(photo=photo)
            generate_instagram_crop(ext)
            ext.save()
            count += 1
        self.message_user(request, f"Successfully regenerated {count} Instagram 4:5 crop(s).")


class ExtendedGalleryAdmin(PhotologueGalleryAdmin):
    inlines = list(PhotologueGalleryAdmin.inlines) + [GalleryExtensionInline]
    actions = ["send_to_telegram_pack"]

    @admin.action(description=_("Send Instagram carousel pack to Telegram"))
    def send_to_telegram_pack(self, request, queryset):
        from .telegram import dispatch_gallery_to_telegram

        total_sent = 0
        for gallery in queryset:
            success, msg = dispatch_gallery_to_telegram(gallery)
            if success:
                total_sent += 1
            else:
                self.message_user(request, f"Error sending '{gallery.title}': {msg}", level="error")

        if total_sent:
            self.message_user(request, f"Dispatched {total_sent} gallery pack(s) to Telegram.")


admin.site.unregister(Photo)
admin.site.register(Photo, ExtendedPhotoAdmin)
admin.site.unregister(Gallery)
admin.site.register(Gallery, ExtendedGalleryAdmin)
