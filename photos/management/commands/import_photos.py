from datetime import date
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify
from photologue.models import Gallery, Photo

from photos.models import GalleryExtension, PhotoExtension
from photos.processing import process_photo

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".cr3",
    ".cr2",
    ".arw",
    ".nef",
    ".dng",
    ".raf",
}


class Command(BaseCommand):
    help = "Bulk import photos from a directory into a Photologue gallery with automatic EXIF and watermarking"

    def add_arguments(self, parser):
        parser.add_argument(
            "path",
            type=str,
            help="Directory or file path containing photos to import",
        )
        parser.add_argument(
            "--gallery",
            type=str,
            default="",
            help="Title of the gallery to create or add photos into",
        )
        parser.add_argument(
            "--type",
            choices=["curated", "day_trip"],
            default="curated",
            help="Gallery type: 'curated' (portfolio/collection) or 'day_trip' (chronological event)",
        )
        parser.add_argument(
            "--date",
            type=str,
            default="",
            help="Date of the shoot (YYYY-MM-DD)",
        )
        parser.add_argument(
            "--cc",
            action="store_true",
            help="Apply Creative Commons (CC BY-NC-SA) license and watermark",
        )
        parser.add_argument(
            "--sync",
            action="store_true",
            default=True,
            help="Process photos synchronously rather than queueing to Celery",
        )

    def handle(self, *args, **options):
        input_path = Path(options["path"]).expanduser().resolve()
        if not input_path.exists():
            raise CommandError(f"Path does not exist: {input_path}")

        files_to_import = []
        if input_path.is_file():
            if input_path.suffix.lower() in IMAGE_EXTENSIONS:
                files_to_import.append(input_path)
            else:
                raise CommandError(f"Unsupported image file extension: {input_path.suffix}")
        elif input_path.is_dir():
            for f in sorted(input_path.rglob("*")):
                if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS:
                    files_to_import.append(f)

        if not files_to_import:
            self.stdout.write(self.style.WARNING(f"No matching images found in {input_path}"))
            return

        self.stdout.write(f"Found {len(files_to_import)} photo(s) to import.")

        # Resolve Gallery if specified
        gallery = None
        gallery_title = options.get("gallery", "").strip()
        if gallery_title:
            slug = slugify(gallery_title)
            gallery, created = Gallery.objects.get_or_create(
                slug=slug,
                defaults={"title": gallery_title, "is_public": True},
            )
            g_ext, _ = GalleryExtension.objects.get_or_create(gallery=gallery)
            g_ext.gallery_type = options["type"]

            if options["date"]:
                try:
                    g_ext.date = date.fromisoformat(options["date"])
                except ValueError:
                    self.stdout.write(self.style.WARNING(f"Invalid date format '{options['date']}', ignoring."))
            g_ext.save()

            action_str = "Created" if created else "Found existing"
            self.stdout.write(self.style.SUCCESS(f"{action_str} gallery: '{gallery.title}' (slug: {gallery.slug})"))

        # Process each photo
        success_count = 0
        for idx, file_path in enumerate(files_to_import, 1):
            title = file_path.stem.replace("_", " ").replace("-", " ").title()
            slug = slugify(title)

            # Avoid collision by checking slug
            base_slug = slug
            collision_counter = 1
            while Photo.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{collision_counter}"
                collision_counter += 1

            self.stdout.write(f"[{idx}/{len(files_to_import)}] Importing {file_path.name} as '{title}'...")

            with open(file_path, "rb") as fh:
                django_file = File(fh, name=file_path.name)
                photo = Photo(
                    title=title,
                    slug=slug,
                    is_public=True,
                )
                photo.image.save(file_path.name, django_file, save=True)

            if gallery:
                gallery.photos.add(photo)

            ext, _ = PhotoExtension.objects.get_or_create(photo=photo)
            if options.get("cc"):
                ext.cc_license = True
                ext.save()

            if options.get("sync"):
                process_photo(ext)

            success_count += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully imported and processed {success_count} photo(s)."))
        if gallery:
            self.stdout.write(f"Gallery URL: /photos/galleries/{gallery.slug}/")
            self.stdout.write(f"Wagtail Block slug to embed: '{gallery.slug}'")
