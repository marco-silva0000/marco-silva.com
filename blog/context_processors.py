from blog.models import BlogPostPage


def latest_posts(request):
    posts = BlogPostPage.objects.live().public().order_by("-first_published_at")[:3]
    return {"latest_posts": posts}
