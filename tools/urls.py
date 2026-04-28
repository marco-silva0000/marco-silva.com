from django.urls import path

from . import views

app_name = "tools"

urlpatterns = [
    path("planz/", views.planz, name="planz"),
    path("planz/auth/", views.planz_auth, name="planz-auth"),
    path("planz/nav/", views.planz_navigate, name="planz-nav"),
    path("planz/event.ics", views.planz_ics, name="planz-ics"),
]
