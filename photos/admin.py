from django.contrib import admin
from photologue.admin import GalleryAdmin as PhotologueGalleryAdmin
from photologue.admin import PhotoAdmin as PhotologuePhotoAdmin
from photologue.models import Gallery, Photo

from .models import GalleryExtension, PhotoExtension


class PhotoExtensionInline(admin.StackedInline):
    model = PhotoExtension
    extra = 0
    fieldsets = (
        ("RAW File", {"fields": ("raw_file", "processing_status")}),
        ("Versions", {"fields": ("watermarked_image", "web_image")}),
        (
            "EXIF Data",
            {
                "classes": ("collapse",),
                "fields": ("camera_make", "camera_model", "lens", "focal_length", "aperture", "shutter_speed", "iso"),
            },
        ),
        ("Location", {"classes": ("collapse",), "fields": ("latitude", "longitude", "location_name")}),
        ("Sales", {"classes": ("collapse",), "fields": ("is_for_sale", "price_raw")}),
    )


class GalleryExtensionInline(admin.StackedInline):
    model = GalleryExtension
    extra = 0


class ExtendedPhotoAdmin(PhotologuePhotoAdmin):
    inlines = list(PhotologuePhotoAdmin.inlines) + [PhotoExtensionInline]


class ExtendedGalleryAdmin(PhotologueGalleryAdmin):
    inlines = list(PhotologueGalleryAdmin.inlines) + [GalleryExtensionInline]


admin.site.unregister(Photo)
admin.site.register(Photo, ExtendedPhotoAdmin)
admin.site.unregister(Gallery)
admin.site.register(Gallery, ExtendedGalleryAdmin)
