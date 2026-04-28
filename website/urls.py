from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path
from django.views.generic import TemplateView
from photologue.sitemaps import GallerySitemap, PhotoSitemap
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls

from blog.feeds import BlogFeed
from photos.feeds import GalleryFeed

sitemaps = {
    "photologue_galleries": GallerySitemap,
    "photologue_photos": PhotoSitemap,
}


urlpatterns = [
    path("", TemplateView.as_view(template_name="index.html"), name="homepage"),
    path("cv", TemplateView.as_view(template_name="cv.html"), name="cv"),
    path("photos/", include("photos.urls")),
    path("tools/", include("tools.urls")),
    path("games/", include("gamerooms.urls")),
    path("games/emojinary/", include("emojinary.urls")),
    path("admin/", admin.site.urls),
    path("cms/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("photologue/", include("photologue.urls", namespace="photologue")),
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    path("feeds/galleries/", GalleryFeed(), name="gallery-feed"),
    path("feeds/blog/", BlogFeed(), name="blog-feed"),
    # Wagtail catch-all — serves blog pages at /blog/ etc.
    path("", include(wagtail_urls)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
