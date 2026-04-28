import pytest
from django.test import Client
from django.urls import reverse

from gamerooms.models import Room


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def room(db):
    return Room.objects.create(title="Test Room", code="TESTROOM")


@pytest.fixture
def locked_room(db):
    return Room.objects.create(title="Locked Room", code="LOCKROOM", password="secret")


class TestRoomList:
    def test_returns_200(self, client, db):
        resp = client.get(reverse("gamerooms:room-list"))
        assert resp.status_code == 200

    def test_shows_rooms(self, client, room):
        resp = client.get(reverse("gamerooms:room-list"))
        assert room.title in resp.content.decode()

    def test_shows_create_link(self, client, db):
        resp = client.get(reverse("gamerooms:room-list"))
        assert "create room" in resp.content.decode()

    def test_shows_pictionary_link(self, client, db):
        resp = client.get(reverse("gamerooms:room-list"))
        assert "pictionary" in resp.content.decode()


class TestPictionary:
    def test_page_returns_200(self, client, db):
        resp = client.get("/games/pictionary/")
        assert resp.status_code == 200

    def test_word_returns_200(self, client, db):
        resp = client.get("/games/pictionary/word/?d=easy&cat=noun&mode=word")
        assert resp.status_code == 200
        assert len(resp.content.decode()) > 0

    def test_sentence_mode(self, client, db):
        resp = client.get("/games/pictionary/word/?mode=sentence")
        assert resp.status_code == 200


class TestRoomCreate:
    def test_get_returns_200(self, client, db):
        resp = client.get(reverse("gamerooms:room-create"))
        assert resp.status_code == 200
        assert "captcha" in resp.content.decode().lower() or "+" in resp.content.decode()

    def test_create_with_correct_captcha(self, client, db):
        resp = client.post(
            reverse("gamerooms:room-create"),
            {"title": "My Room", "password": "", "captcha_answer": "15", "captcha_expected": "15"},
        )
        assert resp.status_code == 302
        assert Room.objects.filter(title="My Room").exists()

    def test_create_with_wrong_captcha(self, client, db):
        resp = client.post(
            reverse("gamerooms:room-create"),
            {"title": "My Room", "password": "", "captcha_answer": "99", "captcha_expected": "15"},
        )
        assert resp.status_code == 200
        assert "wrong captcha" in resp.content.decode()
        assert not Room.objects.filter(title="My Room").exists()

    def test_create_without_title(self, client, db):
        resp = client.post(
            reverse("gamerooms:room-create"),
            {"title": "", "captcha_answer": "15", "captcha_expected": "15"},
        )
        assert resp.status_code == 200
        assert "title is required" in resp.content.decode()


class TestRoomJoin:
    def test_open_room_asks_for_name(self, client, room):
        resp = client.get(reverse("gamerooms:room-join", args=[room.code]))
        assert resp.status_code == 200
        assert "your name" in resp.content.decode()

    def test_locked_room_asks_for_password(self, client, locked_room):
        resp = client.get(reverse("gamerooms:room-join", args=[locked_room.code]))
        assert resp.status_code == 200
        assert "password" in resp.content.decode()

    def test_locked_room_wrong_password(self, client, locked_room):
        resp = client.post(reverse("gamerooms:room-join", args=[locked_room.code]), {"password": "wrong"})
        assert "wrong password" in resp.content.decode()

    def test_join_with_name_redirects_to_game(self, client, room):
        resp = client.post(reverse("gamerooms:room-join", args=[room.code]), {"name": "Marco"})
        assert resp.status_code == 302
        assert "emojinary" in resp.url

    def test_nonexistent_room_404(self, client, db):
        resp = client.get(reverse("gamerooms:room-join", args=["NOPE1234"]))
        assert resp.status_code == 404


class TestRoomModel:
    def test_auto_generates_code(self, db):
        room = Room.objects.create(title="Auto Code")
        assert len(room.code) == 8

    def test_has_password(self, db):
        room = Room.objects.create(title="Open")
        assert not room.has_password
        room2 = Room.objects.create(title="Locked", password="abc")
        assert room2.has_password
