from django.contrib import admin
from photologue.admin import PhotoAdmin as PhotologuePhotoAdmin
from photologue.models import Photo

from .models import PhotoExtension


class PhotoExtensionInline(admin.StackedInline):
    model = PhotoExtension
    extra = 0
    fieldsets = (
        ("RAW File", {"fields": ("raw_file", "processing_status")}),
        ("Watermark", {"fields": ("watermarked_image",)}),
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
        (
            "Location",
            {
                "classes": ("collapse",),
                "fields": ("latitude", "longitude", "location_name"),
            },
        ),
        (
            "Sales",
            {
                "classes": ("collapse",),
                "fields": ("is_for_sale", "price_raw"),
            },
        ),
    )


class ExtendedPhotoAdmin(PhotologuePhotoAdmin):
    inlines = list(PhotologuePhotoAdmin.inlines) + [PhotoExtensionInline]


admin.site.unregister(Photo)
admin.site.register(Photo, ExtendedPhotoAdmin)
