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
        a for a in frame.actions if not a.compatible_tags or any(t in a.compatible_tags for t in sub.tags)
    ] or frame.actions
    act: ActionSlot = _rng.choice(comp_actions)

    tgt: TargetSlot = _rng.choice(frame.targets)

    limiter: Optional[LimiterSlot] = None
    if include_limiter and frame.limiters and _rng.random() < 0.65:
        limiter = _rng.choice(frame.limiters)

    # Construction Grammar variation (CxG): direct imperative, interrogative, or attributive relative
    construction = _rng.choice(["attributive", "imperative", "can_you_name"])

    # 1. English Assembly
    subj_en = f"{sub.mod1} {sub.thing}".strip()
    target_parts = [p for p in (tgt.article, tgt.mod2, tgt.target) if p]
    target_en = " ".join(target_parts).strip()
    limiter_en = limiter.limiter if limiter else ""

    if construction == "imperative":
        art = "an" if subj_en and subj_en[0].lower() in "aeiou" else "a"
        text_en = f"Name {art} {subj_en} {act.relativizer} {act.action} {target_en}"
    elif construction == "can_you_name":
        art = "an" if subj_en and subj_en[0].lower() in "aeiou" else "a"
        text_en = f"Can you name {art} {subj_en} {act.relativizer} {act.action} {target_en}?"
    else:
        text_en = f"{subj_en} {act.relativizer} {act.action} {target_en}"

    if limiter_en:
        text_en = f"{text_en} ({limiter_en})"
    text_en = _clean_str(text_en)

    # 2. Translations Assembly (pt, es, it, fr)
    translations: dict[str, str] = {}
    prefix_map = {
        "imperative": {
            "pt": "Diz um(a)",
            "es": "Nombra un(a)",
            "it": "Nomina un",
            "fr": "Cite un(e)",
        },
        "can_you_name": {
            "pt": "Consegues dizer um(a)",
            "es": "¿Puedes nombrar un(a)",
            "it": "Puoi nominare un",
            "fr": "Peux-tu citer un(e)",
        },
    }

    for lang in ("pt", "es", "it", "fr"):
        sub_tr = sub.translations.get(lang, subj_en)
        act_tr = act.translations.get(lang, f"{act.relativizer} {act.action}")
        tgt_tr = tgt.translations.get(lang, target_en)
        lim_tr = limiter.translations.get(lang, limiter_en) if limiter else ""

        core = f"{sub_tr} {act_tr} {tgt_tr}".strip()
        if construction in prefix_map:
            prefix = prefix_map[construction].get(lang, "")
            assembled = f"{prefix} {core}"
            if construction == "can_you_name":
                assembled = f"{assembled}?"
        else:
            assembled = core

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
    round_num: int = 1,
    pacing_mode: str = "funnel",
) -> dict[str, Any]:
    """
    Select the next round prompt with progressive Goldilocks narrowing.
    - 'funnel': Wide open questions in early rounds (N >= 18) -> moderate mid rounds (10 <= N <= 22)
      -> tight late rounds (4 <= N <= 12) -> sudden death collisions in deep elimination (N <= 7).
    - 'narrow': High-collision sudden death prompts only (N <= 8).
    - 'random': Pure random mix without cardinality weighting.
    """
    used = used_ids or set()
    curated = get_curated_deck(pack)
    unused_curated = [p for p in curated if p.get("id") not in used]

    if unused_curated:
        candidates = []
        if pacing_mode in ("funnel", "narrowing"):
            if round_num <= 2:
                candidates = [p for p in unused_curated if p.get("cardinality", 15) >= 18]
            elif round_num in (3, 4):
                candidates = [p for p in unused_curated if 10 <= p.get("cardinality", 15) <= 22]
            elif round_num in (5, 6):
                candidates = [p for p in unused_curated if 4 <= p.get("cardinality", 15) <= 12]
            else:
                candidates = [p for p in unused_curated if p.get("cardinality", 15) <= 8]
        elif pacing_mode in ("narrow", "sudden_death"):
            candidates = [p for p in unused_curated if p.get("cardinality", 15) <= 8]

        pool_to_pick = candidates if candidates else unused_curated
        chosen = dict(_rng.choice(pool_to_pick))

        card = chosen.get("cardinality", 15)
        if card >= 18:
            chosen["cardinality_bracket"] = "broad"
        elif card >= 10:
            chosen["cardinality_bracket"] = "medium"
        elif card >= 5:
            chosen["cardinality_bracket"] = "tight"
        else:
            chosen["cardinality_bracket"] = "narrow"

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
        need_strict_limiter = (round_num >= 4) or (pacing_mode in ("narrow", "sudden_death"))
        synth = synthesize_prompt_from_frame(frame, language=language, include_limiter=need_strict_limiter)
        synth["cardinality_bracket"] = "narrow" if need_strict_limiter else "broad"
        lang_code = (language or "en").split("-")[0].lower()
        if lang_code != "en" and lang_code in synth.get("translations", {}):
            synth["display_text"] = synth["translations"][lang_code]
        else:
            synth["display_text"] = synth["text"]
        return synth

    # Ultimate fallback to any gold prompt
    chosen = dict(_rng.choice(GOLD_PROMPTS))
    chosen["cardinality_bracket"] = "broad"
    chosen["display_text"] = chosen["text"]
    return chosen
