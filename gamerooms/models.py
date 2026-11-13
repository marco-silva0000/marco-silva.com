import uuid

from django.db import models


class Room(models.Model):
    STATUS_OPEN = "open"
    STATUS_RUNNING = "running"
    STATUS_FINISHED = "finished"
    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_RUNNING, "Running"),
        (STATUS_FINISHED, "Finished"),
    ]

    code = models.CharField(max_length=8, unique=True, db_index=True)
    title = models.CharField(max_length=100)
    password = models.CharField(max_length=100, blank=True)
    game_type = models.CharField(max_length=50, default="emojinary")
    language = models.CharField(max_length=12, default="en", db_index=True)
    creator = models.CharField(max_length=100, blank=True)
    max_players = models.PositiveIntegerField(default=8)
    status = models.CharField(
        max_length=20,
        default=STATUS_OPEN,
        choices=STATUS_CHOICES,
        db_index=True,
    )
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
