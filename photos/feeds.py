from django.contrib.syndication.views import Feed
from photologue.models import Gallery


class GalleryFeed(Feed):
    title = "Marco Silva — Photo Galleries"
    link = "/photos/"
    description = "Latest photo galleries from Marco Silva"

    def items(self):
        return Gallery.objects.filter(is_public=True).order_by("-date_added")[:10]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.description

    def item_link(self, item):
        return item.get_absolute_url()
