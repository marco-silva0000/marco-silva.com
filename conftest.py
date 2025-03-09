import pytest
import faker
from rest_framework.test import APIClient


fake = faker.Faker()


@pytest.fixture
def unauthenticated_client(django_db_setup):
    client = APIClient()
    return client


@pytest.fixture
def fake_email():
    return fake.email()


@pytest.fixture
def authenticated_client():
    from auth_app.factories import UserFactory

    user = UserFactory()
    client = APIClient()
    client.force_authenticate(user, fake.sha256())
    client.user = user
    return client
