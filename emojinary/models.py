from django.db import models


class EmojinaryWord(models.Model):
    """Word/phrase database for emojinary."""

    class Category(models.TextChoices):
        MOVIE = "movie", "Movie"
        PHRASE = "phrase", "Phrase"
        SONG = "song", "Song"
        TVSHOW = "tvshow", "TV Show"
        THING = "thing", "Thing"

    text = models.CharField(max_length=200)
    category = models.CharField(max_length=10, choices=Category.choices, default=Category.THING)
    difficulty = models.PositiveIntegerField(default=1, help_text="1=easy, 2=medium, 3=hard")

    class Meta:
        ordering = ["category", "text"]

    def __str__(self):
        return f"{self.text} ({self.get_category_display()})"
