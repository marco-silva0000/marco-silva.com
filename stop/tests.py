"""Tests for Stop! (Categories & Letter Speed Game): DB categories, web prompts, custom categories, speed+uniqueness scoring, zero-spoiler view, and views."""

import re
import shutil
import subprocess
import tempfile

import pytest
from django.test import Client
from django.urls import reverse

from gamerooms.models import Room

from .categories import (
    DB_CATEGORIES,
    WEB_PARTY_CATEGORIES,
    get_all_preset_categories,
    get_db_category_words,
    get_db_words_for_letter,
    get_sample_db_words,
    is_word_in_db,
    pick_category_and_letter,
    starts_with_letter,
)
from .game_state import (
    add_custom_category,
    add_player,
    call_stop,
    create_initial_state,
    delete_game,
    get_sanitized_player_view,
    start_round,
    submit_answer,
    toggle_answer_validity,
    update_settings,
)


class TestStopCategoriesAndWordDatabase:
    def test_db_categories_have_words_and_letter_coverage(self):
        assert len(DB_CATEGORIES) >= 20
        for cat in DB_CATEGORIES:
            words = get_db_category_words(cat["id"], lang_code="en")
            assert len(words) > 0, f"DB category {cat['id']} should have words from wordlists/lexicon"

        animals_b = get_db_words_for_letter("db_animal", "B", lang_code="en")
        assert len(animals_b) >= 5
        assert any(w.lower().startswith("b") for w in animals_b)

        samples = get_sample_db_words("db_food", "P", lang_code="en", limit=6)
        assert 1 <= len(samples) <= 6
        assert all(s[0].upper() == "P" for s in samples)

    def test_word_db_verification_and_localization(self):
        assert is_word_in_db("Bear", cat_id="db_animal", lang_code="en") is True
        assert is_word_in_db("Pizza", cat_id="db_food", lang_code="en") is True
        assert is_word_in_db("XyzzyNonexistentWord99", cat_id="db_animal", lang_code="en") is False

        # Localized DB lookup (Portuguese)
        pt_words = get_db_category_words("db_animal", lang_code="pt")
        assert len(pt_words) >= 400

    def test_web_party_and_custom_category_packs(self):
        assert len(WEB_PARTY_CATEGORIES) >= 50
        db_only = get_all_preset_categories("database")
        assert all(c["source"] == "database" for c in db_only)

        party_only = get_all_preset_categories("party")
        assert all(c["source"] == "party" and c["pack"] == "party" for c in party_only)

        spicy_all = get_all_preset_categories("spicy")
        assert any(c["pack"] == "spicy" for c in spicy_all)

        cat, letter = pick_category_and_letter(
            pack="database",
            lang_code="en",
            easy_letters_only=True,
            last_letter="A",
        )
        assert cat["source"] == "database"
        assert letter != "A"
        assert len(get_db_words_for_letter(cat["id"], letter, lang_code="en")) >= 1

    def test_starts_with_letter_handles_articles_and_accents(self):
        assert starts_with_letter("Bear", "B") is True
        assert starts_with_letter("The Matrix", "M") is True
        assert starts_with_letter("The Bear", "T") is True
        assert starts_with_letter("Éclair", "E") is True
        assert starts_with_letter("B", "B") is False  # single char rejected
        assert starts_with_letter("Cat", "B") is False


class TestStopGameplayAndSpeedUniquenessScoring:
    def setup_method(self):
        self.code = "STOPTEST"
        delete_game(self.code)

    def teardown_method(self):
        delete_game(self.code)

    def test_speed_and_uniqueness_scoring_and_zero_spoiler_view(self):
        state = create_initial_state(self.code)
        state, p1, _ = add_player(state, "Alice", is_admin=True)
        state, p2, _ = add_player(state, "Bob")
        state, p3, _ = add_player(state, "Charlie")
        state, p4, _ = add_player(state, "Diana")
        state, p5, _ = add_player(state, "Eve")

        ok, _ = start_round(state, forced_category="db_animal", forced_letter="B")
        assert ok is True
        assert state["phase"] == "playing"
        assert state["current_letter"] == "B"
        assert state["current_category"]["id"] == "db_animal"

        # P1 submits unique 'Bear' first
        submit_answer(state, p1["id"], "Bear")
        state["submissions"][p1["id"]]["elapsed_ms"] = 1500

        # Zero-spoiler check during `playing`: Bob CANNOT see Alice's word "Bear"
        bob_view = get_sanitized_player_view(state, p2["id"])
        assert bob_view["my_submission"] is None
        assert len(bob_view["live_race"]) == 1
        assert bob_view["live_race"][0]["player_name"] == "Alice"
        assert "raw_text" not in bob_view["live_race"][0]
        assert "Bear" not in str(bob_view)

        # Alice CAN see her own locked-in word
        alice_view = get_sanitized_player_view(state, p1["id"])
        assert alice_view["my_submission"]["raw_text"] == "Bear"
        assert alice_view["my_submission"]["in_db"] is True

        # P2 submits unique 'Badger' second
        submit_answer(state, p2["id"], "Badger")
        state["submissions"][p2["id"]]["elapsed_ms"] = 2400

        # P3 & P4 both submit 'Buffalo' (duplicate clash!)
        submit_answer(state, p3["id"], "Buffalo")
        state["submissions"][p3["id"]]["elapsed_ms"] = 3100
        submit_answer(state, p4["id"], "buffalo")
        state["submissions"][p4["id"]]["elapsed_ms"] = 4200

        # P5 submits wrong letter 'Tiger' -> auto-finishes round because all 5 participants submitted!
        submit_answer(state, p5["id"], "Tiger")
        assert state["phase"] == "reveal"

        # Check scores in default 'shared' clash mode:
        # P1 (1st unique): 15 pts
        # P2 (2nd unique): 13 pts
        # P3 & P4 (duplicate clash): 5 pts each
        # P5 (wrong letter): 0 pts
        assert state["players"][p1["id"]]["score"] == 15
        assert state["players"][p2["id"]]["score"] == 13
        assert state["players"][p3["id"]]["score"] == 5
        assert state["players"][p4["id"]]["score"] == 5
        assert state["players"][p5["id"]]["score"] == 0
        assert len(state["sample_db_words"]) >= 1

        # Now test live Host override / validity toggle in Reveal:
        # Suppose Host rejects P1's answer -> P2 should immediately promote to 1st Unique (15 pts)!
        toggle_answer_validity(state, p1["id"], p1["id"])
        assert state["players"][p1["id"]]["score"] == 0
        assert state["players"][p2["id"]]["score"] == 15

    def test_first_steals_and_zero_clash_modes(self):
        state = create_initial_state(self.code)
        update_settings(state, {"clash_rule": "first_steals", "stop_mode": "instant_stop"})
        state, p1, _ = add_player(state, "Alice", is_admin=True)
        state, p2, _ = add_player(state, "Bob")
        state, p3, _ = add_player(state, "Charlie")

        start_round(state, forced_category="Pizza toppings", forced_letter="P")
        submit_answer(state, p1["id"], "Pepperoni")
        state["submissions"][p1["id"]]["elapsed_ms"] = 1200
        submit_answer(state, p2["id"], "Pepperoni")
        state["submissions"][p2["id"]]["elapsed_ms"] = 2800

        # Alice calls STOP before Charlie answers!
        ok, _ = call_stop(state, p1["id"])
        assert ok is True
        assert state["phase"] == "reveal"
        # In first_steals mode, Alice (faster duplicate) gets 10 pts, Bob gets 0 pts, Charlie gets 0 pts
        assert state["players"][p1["id"]]["score"] == 10
        assert state["players"][p2["id"]]["score"] == 0
        assert state["players"][p3["id"]]["score"] == 0

    def test_custom_categories_workflow(self):
        state = create_initial_state(self.code)
        state, p1, _ = add_player(state, "Marco", is_admin=True)
        ok, _ = add_custom_category(state, p1, "Portuguese Pastries")
        assert ok is True
        assert len(state["custom_categories"]) == 1

        update_settings(state, {"category_pack": "custom"})
        start_round(state)
        assert "Portuguese Pastries" in state["current_category"]["title"]


@pytest.mark.django_db
class TestStopViewsAndRoomIntegration:
    def test_create_and_join_stop_room(self):
        client = Client()
        resp = client.post(
            reverse("gamerooms:room-create"),
            {
                "title": "Friday Stop Race",
                "password": "",
                "game_type": "stop",
                "language": "en",
                "captcha_answer": "10",
                "captcha_expected": "10",
            },
        )
        assert resp.status_code == 302
        room = Room.objects.get(title="Friday Stop Race")
        assert room.game_type == "stop"

        # Room list shows Stop! card and active Stop! room
        list_resp = client.get(reverse("gamerooms:room-list"))
        assert list_resp.status_code == 200
        html = list_resp.content.decode()
        assert "Stop!" in html
        assert "Friday Stop Race" in html

        # Join room redirects to /games/stop/<code>/<name>/
        join_resp = client.post(reverse("gamerooms:room-join", args=[room.code]), {"name": "Marco"})
        assert join_resp.status_code == 302
        assert f"/games/stop/{room.code}/Marco/" in join_resp["Location"]

        # Game page renders 200 and valid JS
        game_resp = client.get(join_resp["Location"])
        assert game_resp.status_code == 200
        game_html = game_resp.content.decode()
        assert "Stop! — Category & Letter Speed Race" in game_html

        if shutil.which("node"):
            scripts = re.findall(r"<script[^>]*>(.*?)</script>", game_html, flags=re.S)
            assert len(scripts) >= 1
            for s in scripts:
                if not s.strip():
                    continue
                with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as tf:
                    tf.write(s)
                    tf_path = tf.name
                proc = subprocess.run(["node", "--check", tf_path], capture_output=True, text=True)
                assert proc.returncode == 0, f"JS syntax error in stop/game.html: {proc.stderr}"
