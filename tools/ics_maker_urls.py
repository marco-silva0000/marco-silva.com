from django.urls import path

from .ics_maker import ics_download, ics_extract, ics_maker

urlpatterns = [
    path("", ics_maker, name="ics-maker"),
    path("extract/", ics_extract, name="ics-extract"),
    path("download/", ics_download, name="ics-download"),
]
