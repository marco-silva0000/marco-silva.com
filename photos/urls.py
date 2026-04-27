from django.urls import path

from . import views

app_name = "photos"

urlpatterns = [
    path("", views.gallery_list, name="gallery-list"),
    path("map/", views.photo_map, name="map"),
    path("map/data/", views.photo_map_data, name="map-data"),
    path("upload/", views.upload, name="upload"),
    path("<slug:slug>/", views.gallery_detail, name="gallery-detail"),
    path("photo/<slug:slug>/", views.photo_viewer, name="photo-viewer"),
    path("photo/<slug:slug>/partial/", views.photo_viewer_partial, name="photo-viewer-partial"),
]
