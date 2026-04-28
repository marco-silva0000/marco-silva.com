from wagtail import blocks


class PhotoGalleryBlock(blocks.StructBlock):
    """Embed a photologue gallery in a blog post."""

    gallery_slug = blocks.CharBlock(help_text="Slug of the photologue gallery to embed.")
    columns = blocks.ChoiceBlock(
        choices=[("2", "2 columns"), ("3", "3 columns"), ("4", "4 columns")],
        default="3",
    )

    class Meta:
        template = "blog/blocks/photo_gallery.html"
        icon = "image"
        label = "Photo Gallery"

    def get_context(self, value, parent_context=None):
        from photologue.models import Gallery

        ctx = super().get_context(value, parent_context=parent_context)
        try:
            gallery = Gallery.objects.get(slug=value["gallery_slug"], is_public=True)
            ctx["gallery"] = gallery
            ctx["photos"] = gallery.photos.filter(is_public=True)
        except Gallery.DoesNotExist:
            ctx["gallery"] = None
            ctx["photos"] = []
        ctx["columns"] = value.get("columns", "3")
        return ctx


class SinglePhotoBlock(blocks.StructBlock):
    """Embed a single photo with optional caption."""

    photo_slug = blocks.CharBlock(help_text="Slug of the photologue photo to embed.")
    caption = blocks.CharBlock(required=False)

    class Meta:
        template = "blog/blocks/single_photo.html"
        icon = "image"
        label = "Photo"

    def get_context(self, value, parent_context=None):
        from photologue.models import Photo

        ctx = super().get_context(value, parent_context=parent_context)
        try:
            photo = Photo.objects.get(slug=value["photo_slug"], is_public=True)
            ctx["photo"] = photo
            ext = getattr(photo, "extension", None)
            ctx["ext"] = ext
        except Photo.DoesNotExist:
            ctx["photo"] = None
            ctx["ext"] = None
        ctx["caption"] = value.get("caption", "")
        return ctx
