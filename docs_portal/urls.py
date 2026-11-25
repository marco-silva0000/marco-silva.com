from django.urls import path

from . import views

app_name = "docs"

urlpatterns = [
    path("", views.doc_index, name="index"),
    path("<str:quadrant>/", views.doc_quadrant, name="quadrant"),
    path("<str:quadrant>/<str:slug>.md", views.doc_md_redirect, name="detail-md-redirect"),
    path("<str:quadrant>/<str:slug>/", views.doc_detail, name="detail"),
]
