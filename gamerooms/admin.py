from django.contrib import admin
from django.utils.html import format_html

from .models import GamePrompt, Room


@admin.register(GamePrompt)
class GamePromptAdmin(admin.ModelAdmin):
    list_display = (
        "prompt_id",
        "text_preview",
        "domain",
        "status_badge",
        "bracket_badge",
        "source",
        "times_used",
        "last_used_at",
        "submitter_name",
        "is_active",
    )
    list_filter = (
        "status",
        "domain",
        "cardinality_bracket",
        "source",
        "is_active",
        "created_at",
    )
    search_fields = (
        "prompt_id",
        "text",
        "submitter_name",
        "submitter_room",
        "reviewer_notes",
    )
    ordering = ("-created_at",)
    readonly_fields = ("times_used", "last_used_at", "created_at", "updated_at")

    fieldsets = (
        (
            "Prompt Content",
            {
                "fields": (
                    "prompt_id",
                    "text",
                    "domain",
                    "game_type",
                    "is_active",
                )
            },
        ),
        (
            "Cardinality & Validation",
            {
                "fields": (
                    "cardinality_bracket",
                    "estimated_cardinality",
                    "sample_answers",
                ),
                "description": "Cardinality bracket determines when this prompt appears in Goldilocks pacing mode.",
            },
        ),
        (
            "Multilingual Translations",
            {
                "fields": ("translations",),
                "classes": ("collapse",),
                "description": "Dictionary of localized prompt texts, e.g. {'pt': '...', 'es': '...', 'it': '...'}",
            },
        ),
        (
            "Curation & Moderation",
            {
                "fields": (
                    "status",
                    "source",
                    "submitter_name",
                    "submitter_room",
                    "reviewer_notes",
                ),
                "description": "Moderate user-submitted questions here before approving them into the active rotation.",
            },
        ),
        (
            "Usage Telemetry & Variety",
            {
                "fields": ("times_used", "last_used_at", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    actions = [
        "approve_prompts",
        "reject_prompts",
        "mark_pending",
        "reset_usage_statistics",
    ]

    @admin.display(description="Prompt Text")
    def text_preview(self, obj):
        return obj.text[:65] + ("..." if len(obj.text) > 65 else "")

    @admin.display(description="Status")
    def status_badge(self, obj):
        colors = {
            GamePrompt.STATUS_APPROVED: ("#16a34a", "#ffffff", "Approved"),
            GamePrompt.STATUS_PENDING: ("#d97706", "#ffffff", "Pending Review"),
            GamePrompt.STATUS_REJECTED: ("#dc2626", "#ffffff", "Rejected"),
            GamePrompt.STATUS_ARCHIVED: ("#64748b", "#ffffff", "Archived"),
        }
        bg, fg, label = colors.get(obj.status, ("#475569", "#ffffff", obj.status))
        return format_html(
            '<span style="background:{}; color:{}; padding:3px 8px; border-radius:4px; font-weight:600; font-size:11px;">{}</span>',
            bg,
            fg,
            label,
        )

    @admin.display(description="Bracket")
    def bracket_badge(self, obj):
        colors = {
            GamePrompt.CARDINALITY_BROAD: "#2563eb",
            GamePrompt.CARDINALITY_MEDIUM: "#0891b2",
            GamePrompt.CARDINALITY_TIGHT: "#7c3aed",
            GamePrompt.CARDINALITY_NARROW: "#c026d3",
        }
        bg = colors.get(obj.cardinality_bracket, "#475569")
        return format_html(
            '<span style="background:{}; color:#fff; padding:2px 6px; border-radius:3px; font-size:10px;">{}</span>',
            bg,
            obj.cardinality_bracket.upper(),
        )

    @admin.action(description="✅ Approve selected prompts into active rotation")
    def approve_prompts(self, request, queryset):
        updated = queryset.update(status=GamePrompt.STATUS_APPROVED, is_active=True)
        self.message_user(request, f"{updated} prompt(s) successfully approved into active rotation.")

    @admin.action(description="❌ Reject selected prompts")
    def reject_prompts(self, request, queryset):
        updated = queryset.update(status=GamePrompt.STATUS_REJECTED, is_active=False)
        self.message_user(request, f"{updated} prompt(s) rejected.")

    @admin.action(description="⏳ Mark selected prompts as Pending Review")
    def mark_pending(self, request, queryset):
        updated = queryset.update(status=GamePrompt.STATUS_PENDING)
        self.message_user(request, f"{updated} prompt(s) marked as pending review.")

    @admin.action(description="🔄 Reset question usage counts to 0")
    def reset_usage_statistics(self, request, queryset):
        updated = queryset.update(times_used=0, last_used_at=None)
        self.message_user(request, f"Usage telemetry reset for {updated} prompt(s).")


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "title",
        "game_type",
        "status_badge",
        "language",
        "creator",
        "max_players",
        "created_at",
    )
    list_filter = ("game_type", "status", "language", "is_active")
    search_fields = ("code", "title", "creator")
    ordering = ("-created_at",)

    @admin.display(description="Status")
    def status_badge(self, obj):
        colors = {
            Room.STATUS_OPEN: ("#16a34a", "Open"),
            Room.STATUS_RUNNING: ("#2563eb", "Running"),
            Room.STATUS_FINISHED: ("#64748b", "Finished"),
        }
        bg, label = colors.get(obj.status, ("#475569", obj.status))
        return format_html(
            '<span style="background:{}; color:#fff; padding:2px 6px; border-radius:4px; font-weight:600; font-size:11px;">{}</span>',
            bg,
            label,
        )
