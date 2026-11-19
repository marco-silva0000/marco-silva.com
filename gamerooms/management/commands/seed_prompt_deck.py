from django.core.management.base import BaseCommand

from gamerooms.models import GamePrompt
from gamerooms.prompt_engine.deck import GOLD_PROMPTS
from rankit.prompts import RANKIT_PROMPTS


class Command(BaseCommand):
    help = "Seed or synchronize pre-generated curated prompt deck into GamePrompt database model"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-usage",
            action="store_true",
            help="Reset usage statistics (times_used=0, last_used_at=None) for all prompts",
        )

    def handle(self, *args, **options):
        reset_usage = options.get("reset_usage", False)

        created_count = 0
        updated_count = 0

        for p in GOLD_PROMPTS:
            prompt_id = p.get("id")
            if not prompt_id:
                continue

            cardinality = p.get("cardinality", 15)
            if cardinality >= 18:
                bracket = GamePrompt.CARDINALITY_BROAD
            elif cardinality >= 10:
                bracket = GamePrompt.CARDINALITY_MEDIUM
            elif cardinality >= 5:
                bracket = GamePrompt.CARDINALITY_TIGHT
            else:
                bracket = GamePrompt.CARDINALITY_NARROW

            defaults = {
                "text": p.get("text", ""),
                "translations": p.get("translations", {}),
                "domain": p.get("pack", "mix"),
                "cardinality_bracket": bracket,
                "estimated_cardinality": cardinality,
                "sample_answers": p.get("sample_answers", []),
                "status": GamePrompt.STATUS_APPROVED,
                "source": GamePrompt.SOURCE_CURATED,
                "is_active": True,
            }

            obj, created = GamePrompt.objects.get_or_create(
                prompt_id=prompt_id,
                defaults=defaults,
            )

            if created:
                created_count += 1
            else:
                # Update content fields without wiping usage metrics unless requested
                for field, val in defaults.items():
                    setattr(obj, field, val)
                if reset_usage:
                    obj.times_used = 0
                    obj.last_used_at = None
                obj.save()
                updated_count += 1

        for rk in RANKIT_PROMPTS:
            prompt_id = rk.get("id")
            if not prompt_id:
                continue

            sample_answers = [
                f"1: {rk.get('low_desc', '')}",
                f"100: {rk.get('high_desc', '')}",
            ]
            defaults = {
                "text": rk.get("title", ""),
                "translations": rk.get("translations", {}),
                "game_type": "rankit",
                "domain": rk.get("pack", "classic"),
                "cardinality_bracket": GamePrompt.CARDINALITY_BROAD,
                "estimated_cardinality": 100,
                "sample_answers": sample_answers,
                "status": GamePrompt.STATUS_APPROVED,
                "source": GamePrompt.SOURCE_CURATED,
                "is_active": True,
            }

            obj, created = GamePrompt.objects.get_or_create(
                prompt_id=prompt_id,
                defaults=defaults,
            )

            if created:
                created_count += 1
            else:
                for field, val in defaults.items():
                    setattr(obj, field, val)
                if reset_usage:
                    obj.times_used = 0
                    obj.last_used_at = None
                obj.save()
                updated_count += 1

        if reset_usage:
            GamePrompt.objects.all().update(times_used=0, last_used_at=None)

        msg = (
            f"Successfully seeded prompt deck: {created_count} created, "
            f"{updated_count} synchronized. Total active prompts: {GamePrompt.objects.filter(status=GamePrompt.STATUS_APPROVED).count()}."
        )
        self.stdout.write(self.style.SUCCESS(msg))
