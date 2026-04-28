from django.db import models
from modelcluster.contrib.taggit import ClusterTaggableManager
from modelcluster.fields import ParentalKey
from taggit.models import TaggedItemBase
from wagtail import blocks
from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page
from wagtailmarkdown.blocks import MarkdownBlock

from .blocks import PhotoGalleryBlock, SinglePhotoBlock


class BlogPageTag(TaggedItemBase):
    content_object = ParentalKey("BlogPostPage", related_name="tagged_items", on_delete=models.CASCADE)


class BlogIndexPage(Page):
    subpage_types = ["blog.BlogPostPage"]
    max_count = 1

    def get_context(self, request):
        ctx = super().get_context(request)
        ctx["posts"] = BlogPostPage.objects.live().public().order_by("-first_published_at")
        return ctx


class BlogPostPage(Page):
    body = StreamField(
        [
            ("markdown", MarkdownBlock()),
            ("raw_html", blocks.RawHTMLBlock()),
            ("photo", SinglePhotoBlock()),
            ("gallery", PhotoGalleryBlock()),
        ],
        use_json_field=True,
    )
    tags = ClusterTaggableManager(through=BlogPageTag, blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("body"),
        FieldPanel("tags"),
    ]

    parent_page_types = ["blog.BlogIndexPage"]
