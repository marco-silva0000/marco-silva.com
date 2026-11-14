from django.db import models


class EmojinaryWord(models.Model):
    """Word/phrase database for emojinary."""

    class Category(models.TextChoices):
        MOVIE = "movie", "Movie"
        PHRASE = "phrase", "Phrase"
        SONG = "song", "Song"
        TVSHOW = "tvshow", "TV Show"
        THING = "thing", "Thing"
        ANIMAL = "animal", "Animal"
        FOOD = "food", "Food & Drink"
        PERSON = "person", "Person & Character"
        PLACE = "place", "Place & Landmark"
        ACTION = "action", "Action & Charade"

    class PartOfSpeech(models.TextChoices):
        NOUN = "noun", "Noun"
        VERB = "verb", "Verb"
        ADJECTIVE = "adjective", "Adjective"
        PHRASE = "phrase", "Phrase / Idiom"
        PROPER = "proper", "Proper Noun"

    text = models.CharField(max_length=200, db_index=True)
    category = models.CharField(max_length=10, choices=Category.choices, default=Category.THING, db_index=True)
    pos = models.CharField(max_length=12, choices=PartOfSpeech.choices, default=PartOfSpeech.NOUN, db_index=True)
    difficulty = models.PositiveIntegerField(default=1, help_text="1=easy, 2=medium, 3=hard")

    # Wiktionary Enrichment Fields (CC BY-SA 4.0)
    definition = models.TextField(blank=True, default="", help_text="Concise 1-line English gloss from Wiktionary")
    etymology = models.TextField(blank=True, default="", help_text="Short origin note for idioms/phrases")
    aliases = models.JSONField(default=list, blank=True, help_text="Accepted English synonyms/variants")
    translations = models.JSONField(default=dict, blank=True, help_text="Map of lang_code -> list of translated terms")
    topics = models.JSONField(default=list, blank=True, help_text="Semantic topic hints")
    is_codenames = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Included in official 400-word Codenames deck",
    )
    related_words = models.JSONField(
        default=list,
        blank=True,
        help_text="Wikisaurus / Wiktionary semantic neighbors",
    )
    source = models.CharField(max_length=50, default="curated", blank=True)

    class Meta:
        ordering = ["category", "text"]

    def __str__(self):
        return f"{self.text} ({self.get_category_display()})"
