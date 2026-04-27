from django.contrib.syndication.views import Feed

from blog.models import BlogPostPage


class BlogFeed(Feed):
    title = "Marco Silva's Blog"
    link = "/blog/"
    description = "Latest blog posts from marco-silva.com"

    def items(self):
        return BlogPostPage.objects.live().public().order_by("-first_published_at")[:20]

    def item_title(self, item):
        return item.title

    def item_link(self, item):
        return item.url

    def item_pubdate(self, item):
        return item.first_published_at
