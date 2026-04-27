from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.views.generic import TemplateView
from django.urls import include, path
from photologue.sitemaps import GallerySitemap, PhotoSitemap
from wagtail.admin import urls as wagtailadmin_urls
from wagtail import urls as wagtail_urls
from wagtail.documents import urls as wagtaildocs_urls


sitemaps = {
    "photologue_galleries": GallerySitemap,
    "photologue_photos": PhotoSitemap,
}


urlpatterns = [
    path("", TemplateView.as_view(template_name="index_new.html"), name="homepage"),
    path("cv", TemplateView.as_view(template_name="cv.html"), name="cv"),
    path("blog/", TemplateView.as_view(template_name="wip.html"), name="blog"),
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
    # Wagtail catch-all — serves blog pages at /blog/ etc.
    path("", include(wagtail_urls)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
