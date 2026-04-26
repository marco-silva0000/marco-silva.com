from django.apps import AppConfig


class PhotosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "photos"
    verbose_name = "Photos (RAW & Processing)"

    def ready(self):
        import photos.signals  # noqa: F401
