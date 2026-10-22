from django.core.management.base import BaseCommand, CommandError
from photologue.models import Gallery

from photos.telegram import dispatch_gallery_to_telegram


class Command(BaseCommand):
    help = "Dispatch a photo gallery as a 4:5 Instagram carousel pack (with QR slide & caption) to your Telegram bot"

    def add_arguments(self, parser):
        parser.add_argument("gallery_slug", type=str, help="Slug of the gallery to send")

    def handle(self, *args, **options):
        slug = options["gallery_slug"]
        try:
            gallery = Gallery.objects.get(slug=slug)
        except Gallery.DoesNotExist:
            raise CommandError(f"Gallery with slug '{slug}' does not exist.")

        self.stdout.write(f"Preparing 4:5 Instagram carousel pack for '{gallery.title}'...")
        success, msg = dispatch_gallery_to_telegram(gallery)

        if success:
            self.stdout.write(self.style.SUCCESS(f"✓ {msg}"))
        else:
            raise CommandError(f"Failed to dispatch to Telegram: {msg}")
