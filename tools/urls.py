from django.urls import path

from . import views

app_name = "tools"

urlpatterns = [
    path("planz/", views.planz, name="planz"),
    path("planz/auth/", views.planz_auth, name="planz-auth"),
]
