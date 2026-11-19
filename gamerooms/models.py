import uuid

from django.db import models
from django.utils import timezone


class GamePrompt(models.Model):
    """Curated and user-submitted question deck for party games."""

    STATUS_APPROVED = "approved"
    STATUS_PENDING = "pending_review"
    STATUS_REJECTED = "rejected"
    STATUS_ARCHIVED = "archived"
    STATUS_CHOICES = [
        (STATUS_APPROVED, "Approved (Active Deck)"),
        (STATUS_PENDING, "Pending Review"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_ARCHIVED, "Archived"),
    ]

    SOURCE_CURATED = "curated_deck"
    SOURCE_SYNTHETIC = "synthetic_frame"
    SOURCE_USER = "user_submission"
    SOURCE_AI = "ai_generated"
    SOURCE_CHOICES = [
        (SOURCE_CURATED, "Curated Deck"),
        (SOURCE_SYNTHETIC, "Linguistic Synthesizer"),
        (SOURCE_USER, "User Submission"),
        (SOURCE_AI, "AI Generated"),
    ]

    CARDINALITY_BROAD = "broad"
    CARDINALITY_MEDIUM = "medium"
    CARDINALITY_TIGHT = "tight"
    CARDINALITY_NARROW = "narrow"
    CARDINALITY_CHOICES = [
        (CARDINALITY_BROAD, "Broad (N >= 18)"),
        (CARDINALITY_MEDIUM, "Medium (10 <= N <= 22)"),
        (CARDINALITY_TIGHT, "Tight (4 <= N <= 12)"),
        (CARDINALITY_NARROW, "Narrow / Sudden Death (N <= 8)"),
    ]

    DOMAIN_CHOICES = [
        ("mix", "🎲 Mixed Variety"),
        ("geo", "🌍 Geography & Places"),
        ("media", "🎬 Pop Culture & Cinema"),
        ("food", "🍕 Culinary & Food"),
        ("nature", "🐾 Nature & Wildlife"),
        ("history", "📜 History & Inventions"),
        ("weird", "🤪 Quirky & Everyday"),
        ("custom", "✨ Custom & User Submitted"),
    ]

    prompt_id = models.CharField(max_length=100, unique=True, db_index=True)
    text = models.CharField(max_length=300, help_text="Primary English prompt text")
    translations = models.JSONField(default=dict, blank=True, help_text="Localized translations {lang: text}")
    game_type = models.CharField(max_length=50, default="dontsay", db_index=True)
    domain = models.CharField(max_length=50, default="mix", choices=DOMAIN_CHOICES, db_index=True)
    cardinality_bracket = models.CharField(
        max_length=20,
        default=CARDINALITY_BROAD,
        choices=CARDINALITY_CHOICES,
        db_index=True,
    )
    estimated_cardinality = models.PositiveIntegerField(default=15, help_text="Estimated count of valid answers")
    sample_answers = models.JSONField(default=list, blank=True, help_text="List of canonical answers for validation")
    status = models.CharField(
        max_length=20,
        default=STATUS_PENDING,
        choices=STATUS_CHOICES,
        db_index=True,
    )
    source = models.CharField(
        max_length=30,
        default=SOURCE_USER,
        choices=SOURCE_CHOICES,
        db_index=True,
    )
    submitter_name = models.CharField(max_length=100, blank=True)
    submitter_room = models.CharField(max_length=20, blank=True)
    reviewer_notes = models.TextField(blank=True)
    times_used = models.PositiveIntegerField(default=0, db_index=True, help_text="Number of times dealt in games")
    last_used_at = models.DateTimeField(null=True, blank=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["times_used", "-created_at"]
        verbose_name = "Game Prompt"
        verbose_name_plural = "Game Prompts"

    def __str__(self):
        return f"{self.prompt_id}: {self.text[:50]}"

    def to_dict(self, language: str = "en") -> dict:
        """Serialize prompt into dictionary expected by game consumers and templates."""
        lang_code = (language or "en").split("-")[0].lower()
        display_text = self.text
        if lang_code != "en" and isinstance(self.translations, dict) and lang_code in self.translations:
            display_text = self.translations[lang_code]
        return {
            "id": self.prompt_id,
            "pack": self.domain,
            "text": self.text,
            "display_text": display_text,
            "translations": self.translations or {},
            "cardinality": self.estimated_cardinality,
            "cardinality_bracket": self.cardinality_bracket,
            "sample_answers": self.sample_answers or [],
            "source": self.source,
            "times_used": self.times_used,
        }

    def record_usage(self):
        """Atomically record question delivery to sprinkle variety across game sessions."""
        try:
            GamePrompt.objects.filter(pk=self.pk).update(
                times_used=models.F("times_used") + 1,
                last_used_at=timezone.now(),
            )
            self.refresh_from_db(fields=["times_used", "last_used_at"])
        except Exception:
            self.times_used += 1
            self.last_used_at = timezone.now()


def create_user_prompt_suggestion(
    text: str,
    domain: str = "mix",
    game_type: str = "dontsay",
    sample_answers: list | str | None = None,
    submitter_name: str = "",
    submitter_room: str = "",
) -> tuple[bool, str, GamePrompt | None]:
    """Create a pending user-submitted prompt for curation in Django Admin."""
    clean_text = " ".join((text or "").split()).strip()[:300]
    if len(clean_text) < 5:
        return False, "Prompt or category must be at least 5 characters.", None

    valid_domains = {"mix", "geo", "media", "food", "nature", "history", "weird", "custom"}
    target_domain = domain if domain in valid_domains else "mix"

    answers: list[str] = []
    if sample_answers:
        if isinstance(sample_answers, str):
            answers = [a.strip() for a in sample_answers.split(",") if a.strip()]
        elif isinstance(sample_answers, list):
            answers = [str(a).strip() for a in sample_answers if str(a).strip()]

    try:
        prompt_id = f"sub_{uuid.uuid4().hex[:10]}"
        prompt = GamePrompt.objects.create(
            prompt_id=prompt_id,
            text=clean_text,
            domain=target_domain,
            game_type=game_type or "dontsay",
            sample_answers=answers,
            status=GamePrompt.STATUS_PENDING,
            source=GamePrompt.SOURCE_USER,
            submitter_name=submitter_name[:100],
            submitter_room=submitter_room[:20],
            is_active=True,
        )
        return True, "Question submitted successfully! Queued for review.", prompt
    except Exception as exc:
        return False, f"Failed to save suggestion: {exc}", None


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
