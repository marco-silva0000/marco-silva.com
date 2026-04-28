import uuid

from django.db import models


class Room(models.Model):
    code = models.CharField(max_length=8, unique=True, db_index=True)
    title = models.CharField(max_length=100)
    password = models.CharField(max_length=100, blank=True)
    game_type = models.CharField(max_length=50, default="emojinary")
    max_players = models.PositiveIntegerField(default=8)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.code})"

    @property
    def has_password(self):
        return bool(self.password)

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = uuid.uuid4().hex[:8].upper()
        super().save(*args, **kwargs)
