from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from photologue.models import Gallery, Photo

from .models import PhotoExtension


def gallery_list(request):
    galleries = Gallery.objects.filter(is_public=True).order_by("-date_added")
    return render(request, "photos/gallery_list.html", {"galleries": galleries})


def gallery_detail(request, slug):
    gallery = get_object_or_404(Gallery, slug=slug, is_public=True)
    photos = gallery.photos.filter(is_public=True)
    return render(request, "photos/gallery_detail.html", {"gallery": gallery, "photos": photos})


def photo_viewer(request, slug):
    photo = get_object_or_404(Photo, slug=slug, is_public=True)
    ext = getattr(photo, "extension", None)
    version = request.GET.get("version", "watermarked")
    return render(request, "photos/photo_viewer.html", {"photo": photo, "ext": ext, "version": version})


def photo_viewer_partial(request, slug):
    """HTMX partial for switching photo versions."""
    photo = get_object_or_404(Photo, slug=slug, is_public=True)
    ext = getattr(photo, "extension", None)
    version = request.GET.get("version", "watermarked")
    return render(request, "photos/partials/photo_image.html", {"photo": photo, "ext": ext, "version": version})


def photo_map(request):
    """Map view showing all photos with GPS data."""
    extensions = PhotoExtension.objects.filter(
        latitude__isnull=False, longitude__isnull=False, photo__is_public=True
    ).select_related("photo")
    return render(request, "photos/map.html", {"extensions": extensions})


def photo_map_data(request):
    """JSON endpoint for map markers."""
    extensions = PhotoExtension.objects.filter(
        latitude__isnull=False, longitude__isnull=False, photo__is_public=True
    ).select_related("photo")
    markers = [
        {
            "lat": float(ext.latitude),
            "lng": float(ext.longitude),
            "title": ext.photo.title,
            "slug": ext.photo.slug,
            "thumbnail": ext.photo.get_thumbnail_url() if hasattr(ext.photo, "get_thumbnail_url") else "",
        }
        for ext in extensions
    ]
    return JsonResponse(markers, safe=False)


@login_required
def upload(request):
    if request.method == "POST":
        return _handle_upload(request)
    galleries = Gallery.objects.all().order_by("-date_added")
    return render(request, "photos/upload.html", {"galleries": galleries})


@login_required
@require_POST
def _handle_upload(request):
    gallery_id = request.POST.get("gallery")
    gallery = get_object_or_404(Gallery, id=gallery_id) if gallery_id else None
    files = request.FILES.getlist("photos")

    for f in files:
        title = f.name.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()
        photo = Photo(title=title, image=f, is_public=True)
        photo.save()
        if gallery:
            gallery.photos.add(photo)
        # Signal auto-creates extension and processes

    if request.headers.get("HX-Request"):
        return render(request, "photos/partials/upload_success.html", {"count": len(files)})
    return redirect("photos:gallery-list")
