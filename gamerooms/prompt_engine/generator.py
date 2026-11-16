"""Combinatorial Prompt Synthesizer based on Linguistic Semantic Frames.

Generates prompts adhering to:
[<mod1>] <thing> that <action> [<article>] [<mod2>] <target> [<limiters>]

Also manages fallback to curated gold prompts in deck.py.
"""

import random
from typing import Any, Optional

from .deck import GOLD_PROMPTS, get_curated_deck
from .frames import ALL_FRAMES, ActionSlot, LimiterSlot, SemanticFrame, SubjectSlot, TargetSlot

_rng = random.SystemRandom()

PACK_CHOICES = (
    ("mix", "🎲 Mixed Variety"),
    ("geo", "🌍 Geography & Places"),
    ("media", "🎬 Pop Culture & Cinema"),
    ("food", "🍕 Culinary & Food"),
    ("nature", "🐾 Nature & Wildlife"),
    ("history", "📜 History & Inventions"),
    ("weird", "🤪 Quirky & Everyday"),
)


def _clean_str(text: str) -> str:
    """Normalize excess whitespace and capitalize first character."""
    s = " ".join((text or "").split()).strip()
    return s[0].upper() + s[1:] if s else ""


def synthesize_prompt_from_frame(
    frame: SemanticFrame,
    language: str = "en",
    include_limiter: bool = True,
) -> dict[str, Any]:
    """Synthesize a combinatorial prompt from a semantic frame across languages."""
    sub: SubjectSlot = _rng.choice(frame.subjects)
    # Filter compatible actions if any tag overlap exists
    comp_actions = [
        a for a in frame.actions
        if not a.compatible_tags or any(t in a.compatible_tags for t in sub.tags)
    ] or frame.actions
    act: ActionSlot = _rng.choice(comp_actions)

    tgt: TargetSlot = _rng.choice(frame.targets)

    limiter: Optional[LimiterSlot] = None
    if include_limiter and frame.limiters and _rng.random() < 0.65:
        limiter = _rng.choice(frame.limiters)

    # 1. English Assembly
    subj_en = f"{sub.mod1} {sub.thing}".strip()
    target_parts = [p for p in (tgt.article, tgt.mod2, tgt.target) if p]
    target_en = " ".join(target_parts).strip()
    limiter_en = limiter.limiter if limiter else ""

    text_en = f"{subj_en} {act.relativizer} {act.action} {target_en}"
    if limiter_en:
        text_en = f"{text_en} ({limiter_en})"
    text_en = _clean_str(text_en)

    # 2. Translations Assembly (pt, es, it, fr)
    translations: dict[str, str] = {}
    for lang in ("pt", "es", "it", "fr"):
        sub_tr = sub.translations.get(lang, subj_en)
        act_tr = act.translations.get(lang, f"{act.relativizer} {act.action}")
        tgt_tr = tgt.translations.get(lang, target_en)
        lim_tr = limiter.translations.get(lang, limiter_en) if limiter else ""

        assembled = f"{sub_tr} {act_tr} {tgt_tr}"
        if lim_tr:
            assembled = f"{assembled} ({lim_tr})"
        translations[lang] = _clean_str(assembled)

    prompt_id = f"synth_{frame.category}_{_rng.randint(1000, 9999)}"

    return {
        "id": prompt_id,
        "pack": frame.category,
        "is_synthetic": True,
        "text": text_en,
        "translations": translations,
        "components": {
            "mod1": sub.mod1,
            "thing": sub.thing,
            "relativizer": act.relativizer,
            "action": act.action,
            "article": tgt.article,
            "mod2": tgt.mod2,
            "target": tgt.target,
            "limiter": limiter.limiter if limiter else None,
        },
        "sample_answers": [],
        "cardinality": 15,
    }


def get_next_prompt(
    pack: str = "mix",
    language: str = "en",
    used_ids: Optional[set[str]] = None,
    allow_generative: bool = True,
) -> dict[str, Any]:
    """
    Select the next round prompt.
    Prefers curated gold deck prompts first, seamlessly falling back to
    combinatorial semantic frame generation when the deck runs out.
    """
    used = used_ids or set()
    curated = get_curated_deck(pack)
    unused_curated = [p for p in curated if p.get("id") not in used]

    if unused_curated:
        chosen = dict(_rng.choice(unused_curated))
        # Localize prompt text if language is non-English and translation is present
        lang_code = (language or "en").split("-")[0].lower()
        if lang_code != "en" and lang_code in chosen.get("translations", {}):
            chosen["display_text"] = chosen["translations"][lang_code]
        else:
            chosen["display_text"] = chosen["text"]
        return chosen

    # If deck is exhausted or generative mode requested, use semantic frames
    if allow_generative:
        target_pack = pack
        if target_pack == "mix" or target_pack not in ALL_FRAMES:
            target_pack = _rng.choice(list(ALL_FRAMES.keys()))

        frame = ALL_FRAMES[target_pack]
        synth = synthesize_prompt_from_frame(frame, language=language)
        lang_code = (language or "en").split("-")[0].lower()
        if lang_code != "en" and lang_code in synth.get("translations", {}):
            synth["display_text"] = synth["translations"][lang_code]
        else:
            synth["display_text"] = synth["text"]
        return synth

    # Ultimate fallback to any gold prompt
    chosen = dict(_rng.choice(GOLD_PROMPTS))
    chosen["display_text"] = chosen["text"]
    return chosen
