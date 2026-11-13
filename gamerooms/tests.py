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


class TestGameroomsI18n:
    """Verify localization across all 9 supported languages on the game rooms pages."""

    @pytest.mark.parametrize(
        "lang,expected_title",
        [
            ("en", "Game Rooms"),
            ("pt", "Salas de Jogos"),
            ("it", "Sale Giochi"),
            ("es", "Salas de Juegos"),
            ("fr", "Salons de Jeux"),
            ("el", "Αίθουσες Παιχνιδιών"),
            ("ru", "Игровые комнаты"),
            ("hi", "गेम रूम"),
            ("kn", "ಆಟದ ಕೊಠಡಿಗಳು"),
        ],
    )
    def test_room_list_multilingual_titles(self, client, db, lang, expected_title):
        client.cookies["django_language"] = lang
        resp = client.get(reverse("gamerooms:room-list"))
        assert resp.status_code == 200
        content = resp.content.decode("utf-8")
        assert expected_title in content

    @pytest.mark.parametrize(
        "lang,expected_hub_title",
        [
            ("en", "Active Lupus Rooms"),
            ("pt", "Salas Ativas de Lupus"),
            ("it", "Stanze Lupus Attive"),
            ("es", "Salas Activas de Lupus"),
            ("fr", "Salons Lupus Actifs"),
            ("el", "Ενεργές Αίθουσες Lupus"),
            ("ru", "Активные комнаты Lupus"),
            ("hi", "सक्रिय लुपस कमरे"),
            ("kn", "ಸಕ್ರಿಯ ಲೂಪಸ್ ಕೊಠಡಿಗಳು"),
        ],
    )
    def test_lupus_hub_multilingual(self, client, db, lang, expected_hub_title):
        client.cookies["django_language"] = lang
        resp = client.get(reverse("gamerooms:lupus:hub"))
        assert resp.status_code == 200
        content = resp.content.decode("utf-8")
        assert expected_hub_title in content

    @pytest.mark.parametrize(
        "lang,expected_create_title",
        [
            ("en", "Create Lupus / Werewolf Room"),
            ("pt", "Criar Sala de Lupus / Lobisomem"),
            ("it", "Crea Stanza Lupus / Licantropo"),
            ("es", "Crear Sala de Lupus / Hombre Lobo"),
            ("fr", "Créer un Salon Lupus / Loup-Garou"),
            ("el", "Δημιουργία Αίθουσας Lupus / Λυκάνθρωπου"),
            ("ru", "Создать комнату Lupus / Оборотни"),
            ("hi", "लुपस / वेयरवोल्फ कमरा बनाएं"),
            ("kn", "ಲೂಪಸ್ / ತೋಳಮಾನವ ಕೊಠಡಿ ರಚಿಸಿ"),
        ],
    )
    def test_lupus_create_multilingual(self, client, db, lang, expected_create_title):
        client.cookies["django_language"] = lang
        resp = client.get(reverse("gamerooms:lupus:create"))
        assert resp.status_code == 200
        content = resp.content.decode("utf-8")
        assert expected_create_title in content

    def test_room_create_error_localized_pt(self, client, db):
        client.cookies["django_language"] = "pt"
        resp = client.post(
            reverse("gamerooms:room-create"),
            {"title": "Sala", "password": "", "captcha_answer": "99", "captcha_expected": "15"},
        )
        assert resp.status_code == 200
        content = resp.content.decode("utf-8")
        assert "captcha incorreto" in content


class TestSiteWideI18n:
    """Verify site-wide template internationalization and tooling."""

    @pytest.mark.parametrize(
        "lang,expected_phrase",
        [
            ("en", "I code, take pics and many other things"),
            ("pt", "Eu programo, tiro fotos e muitas outras coisas"),
            ("es", "Programo, saco fotos y muchas otras cosas"),
            ("fr", "Je code, je prends des photos et bien plus encore"),
            ("it", "Sviluppo software, scatto foto e molto altro"),
        ],
    )
    def test_homepage_multilingual(self, client, db, lang, expected_phrase):
        client.cookies["django_language"] = lang
        resp = client.get("/")
        assert resp.status_code == 200
        content = resp.content.decode("utf-8")
        assert expected_phrase in content

    @pytest.mark.parametrize(
        "lang,expected_phrase",
        [
            ("en", "Hobbies"),
            ("pt", "Passatempos"),
            ("es", "Aficiones"),
            ("fr", "Loisirs"),
            ("it", "Hobby"),
            ("ar", "الهوايات"),
            ("fa", "سرگرمی‌ها"),
            ("ur", "مشاغل"),
        ],
    )
    def test_cv_multilingual(self, client, db, lang, expected_phrase):
        client.cookies["django_language"] = lang
        resp = client.get("/cv")
        assert resp.status_code == 200
        content = resp.content.decode("utf-8")
        assert expected_phrase in content

    @pytest.mark.parametrize(
        "lang,expected_dir",
        [
            ("en", "ltr"),
            ("pt", "ltr"),
            ("es", "ltr"),
            ("fr", "ltr"),
            ("it", "ltr"),
            ("el", "ltr"),
            ("ru", "ltr"),
            ("hi", "ltr"),
            ("kn", "ltr"),
            ("ar", "rtl"),
            ("fa", "rtl"),
            ("ur", "rtl"),
        ],
    )
    def test_bidi_directionality(self, client, db, lang, expected_dir):
        """Test root html tag dir attribute respects Django LANGUAGE_BIDI."""
        client.cookies["django_language"] = lang
        for path in ["/", "/cv", "/games/lupus/"]:
            resp = client.get(path)
            assert resp.status_code == 200
            content = resp.content.decode("utf-8")
            assert f'dir="{expected_dir}"' in content
            assert f'lang="{lang}"' in content

    def test_lupus_rtl_translations(self):
        """Test Lupus translation dictionaries for Arabic, Persian, and Urdu."""
        from lupus.translations import (
            get_localized_faction,
            get_localized_phase,
            get_localized_status,
            get_localized_ui_strings,
        )

        # Arabic
        assert get_localized_status("alive", "ar") == "حي"
        assert get_localized_faction("wolves", "ar") == "المستذئبون / المافيا"
        assert get_localized_phase("night", "ar") == "الليل"
        ar_ui = get_localized_ui_strings("ar")
        assert ar_ui["chat_title"] == "رسالة خاصة إلى راوي اللعبة"

        # Persian / Farsi
        assert get_localized_status("alive", "fa") == "زنده"
        assert get_localized_faction("town", "fa") == "اهالی روستا / شهر"
        assert get_localized_phase("day", "fa") == "روز"
        fa_ui = get_localized_ui_strings("fa")
        assert fa_ui["chat_title"] == "پیام خصوصی به مدیر بازی"

        # Urdu
        assert get_localized_status("alive", "ur") == "زندہ"
        assert get_localized_faction("neutral", "ur") == "غیر جانبدار"
        assert get_localized_phase("lobby", "ur") == "انتظار گاہ"
        ur_ui = get_localized_ui_strings("ur")
        assert ur_ui["chat_title"] == "گیم ماسٹر کو براہ راست پیغام"

    def test_pictionary_multilingual(self, client, db):
        client.cookies["django_language"] = "pt"
        resp = client.get(reverse("gamerooms:pictionary"))
        assert resp.status_code == 200
        content = resp.content.decode("utf-8")
        assert "escolha as opções, clique no botão e desenhe!" in content
        assert "dificuldade" in content

    def test_translations_tool_discovery_and_export(self, tmp_path):
        import argparse

        from scripts.translations_tool import cmd_export_csv, extract_translatable_strings

        extracted = extract_translatable_strings()
        assert len(extracted) >= 300
        assert "I code, take pics and many other things" in extracted
        assert "Hobbies" in extracted

        out_csv = tmp_path / "test_export.csv"
        args = argparse.Namespace(lang="pt", output=str(out_csv), untranslated_only=False)
        cmd_export_csv(args)
        assert out_csv.exists()
        csv_text = out_csv.read_text(encoding="utf-8-sig")
        assert "msgid,context,en,pt" in csv_text
        assert "Eu programo, tiro fotos e muitas outras coisas" in csv_text


class TestRoomLanguageAndImpostorRouting:
    def test_language_support_classification(self):
        from gamerooms.language_support import get_game_language_support

        # English & Wiktionary-covered languages get Full Content + UI for Impostor/Emojinary
        pt_imp = get_game_language_support("impostor", "pt")
        assert pt_imp["content_supported"] is True
        assert pt_imp["mode"] == "full_content"
        assert pt_imp["entry_count"] >= 2000

        el_emoji = get_game_language_support("emojinary", "el")
        assert el_emoji["content_supported"] is True
        assert el_emoji["mode"] == "full_content"

        # Serbian lacks bulk Wiktionary word entries -> UI Only with English fallback words
        sr_imp = get_game_language_support("impostor", "sr")
        assert sr_imp["content_supported"] is False
        assert sr_imp["mode"] == "ui_only"

        # Lupus full content vs UI-only
        assert get_game_language_support("lupus", "pt")["mode"] == "full_content"
        assert get_game_language_support("lupus", "fi")["mode"] == "ui_only"

    def test_create_impostor_room_with_language(self, client, db):
        resp = client.post(
            reverse("gamerooms:room-create"),
            {
                "title": "Lisbon Secret Agents",
                "password": "",
                "game_type": "impostor",
                "language": "pt",
                "captcha_answer": "9",
                "captcha_expected": "9",
            },
        )
        assert resp.status_code == 302
        room = Room.objects.get(title="Lisbon Secret Agents")
        assert room.game_type == "impostor"
        assert room.language == "pt"

        # Joining with player name routes directly into impostor:game
        join_resp = client.post(
            reverse("gamerooms:room-join", args=[room.code]),
            {"name": "Marco"},
        )
        assert join_resp.status_code == 302
        assert f"/games/impostor/{room.code}/Marco/" in join_resp["Location"]

    def test_room_list_shows_impostor_card_and_language_badge(self, client, db):
        Room.objects.create(title="Athens Undercover", code="ATHENS01", game_type="impostor", language="el")
        resp = client.get(reverse("gamerooms:room-list"))
        assert resp.status_code == 200
        html = resp.content.decode()
        assert "Word Impostor" in html
        assert "Athens Undercover" in html
        assert "Greek" in html or "🇬🇷" in html
