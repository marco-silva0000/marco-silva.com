import pytest
from django.contrib.auth.models import User
from django.test import Client


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(username="testadmin", password="testpass", email="test@test.com")


@pytest.fixture
def auth_client(admin_user):
    c = Client()
    c.login(username="testadmin", password="testpass")
    return c
