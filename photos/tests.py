import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from photologue.models import Gallery, Photo
from PIL import Image

from .models import GalleryExtension, PhotoExtension


def _make_image(name="test.jpg", size=(100, 100)):
    buf = io.BytesIO()
    Image.new("RGB", size, "red").save(buf, format="JPEG")
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type="image/jpeg")


@pytest.fixture
def gallery(db):
    g = Gallery.objects.create(title="Test Gallery", slug="test-gallery", is_public=True)
    GalleryExtension.objects.create(gallery=g, gallery_type="curated")
    return g


@pytest.fixture
def photo(db, gallery):
    p = Photo.objects.create(title="Test Photo", slug="test-photo", image=_make_image(), is_public=True)
    gallery.photos.add(p)
    return p


class TestGalleryList:
    def test_returns_200(self, client, db):
        resp = client.get(reverse("photos:gallery-list"))
        assert resp.status_code == 200

    def test_shows_gallery(self, client, gallery):
        resp = client.get(reverse("photos:gallery-list"))
        assert gallery.title in resp.content.decode()

    def test_empty_state(self, client, db):
        resp = client.get(reverse("photos:gallery-list"))
        assert "no galleries yet" in resp.content.decode()


class TestGalleryDetail:
    def test_returns_200(self, client, gallery):
        resp = client.get(reverse("photos:gallery-detail", args=[gallery.slug]))
        assert resp.status_code == 200

    def test_shows_photos(self, client, photo, gallery):
        resp = client.get(reverse("photos:gallery-detail", args=[gallery.slug]))
        assert resp.status_code == 200

    def test_404_for_nonexistent(self, client, db):
        resp = client.get(reverse("photos:gallery-detail", args=["nonexistent"]))
        assert resp.status_code == 404

    def test_404_for_private(self, client, db):
        g = Gallery.objects.create(title="Private", slug="private", is_public=False)
        resp = client.get(reverse("photos:gallery-detail", args=[g.slug]))
        assert resp.status_code == 404


class TestPhotoViewer:
    def test_returns_200(self, client, photo):
        resp = client.get(reverse("photos:photo-viewer", args=[photo.slug]))
        assert resp.status_code == 200

    def test_version_param(self, client, photo):
        for version in ["watermarked", "web", "original"]:
            resp = client.get(reverse("photos:photo-viewer", args=[photo.slug]) + f"?version={version}")
            assert resp.status_code == 200

    def test_404_for_nonexistent(self, client, db):
        resp = client.get(reverse("photos:photo-viewer", args=["nonexistent"]))
        assert resp.status_code == 404

    def test_partial_returns_200(self, client, photo):
        resp = client.get(reverse("photos:photo-viewer-partial", args=[photo.slug]))
        assert resp.status_code == 200


class TestMap:
    def test_returns_200(self, client, db):
        resp = client.get(reverse("photos:map"))
        assert resp.status_code == 200

    def test_data_returns_json(self, client, db):
        resp = client.get(reverse("photos:map-data"))
        assert resp.status_code == 200
        assert resp["Content-Type"] == "application/json"

    def test_data_includes_geotagged_photos(self, client, photo):
        ext, _ = PhotoExtension.objects.get_or_create(photo=photo)
        ext.latitude = 60.1699
        ext.longitude = 24.9384
        ext.save()
        resp = client.get(reverse("photos:map-data"))
        data = resp.json()
        assert len(data) == 1
        assert data[0]["title"] == "Test Photo"


class TestUpload:
    def test_requires_login(self, client, db):
        resp = client.get(reverse("photos:upload"))
        assert resp.status_code == 302
        assert "/login/" in resp.url

    def test_returns_200_for_authenticated(self, auth_client):
        resp = auth_client.get(reverse("photos:upload"))
        assert resp.status_code == 200

    def test_upload_creates_photo(self, auth_client, gallery):
        resp = auth_client.post(
            reverse("photos:upload"),
            {"gallery": gallery.id, "photos": [_make_image("upload1.jpg")]},
        )
        assert resp.status_code == 302
        assert Photo.objects.filter(title="Upload1").exists()

    def test_htmx_upload_returns_partial(self, auth_client, gallery):
        resp = auth_client.post(
            reverse("photos:upload"),
            {"gallery": gallery.id, "photos": [_make_image("upload2.jpg")]},
            HTTP_HX_REQUEST="true",
        )
        assert resp.status_code == 200
        assert "uploaded" in resp.content.decode()


class TestStaticPages:
    def test_homepage(self, client, db):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_cv(self, client, db):
        resp = client.get("/cv")
        assert resp.status_code == 200

    def test_blog_wip(self, client, db):
        resp = client.get("/blog/")
        assert resp.status_code == 200
        assert "work in progress" in resp.content.decode()
