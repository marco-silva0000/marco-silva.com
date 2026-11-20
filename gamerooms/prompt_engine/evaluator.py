"""AI Evaluation and Answer Arbitration for party game prompts.

Integrates with local Ollama (`qwen3:30b` on CT 104) with strict timeouts
and robust offline deterministic fallbacks.
"""

import difflib
import json
import logging
import os
import re
import urllib.request
from typing import Any, Optional

from impostor.word_pairs import normalize_text

logger = logging.getLogger(__name__)

DEFAULT_OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://192.168.1.104:11434")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:30b")


def clean_answer_key(text: str) -> str:
    """Normalize answer text for collision detection (lowercase, accents, leading articles)."""
    norm = normalize_text(text)
    # Strip common leading articles in en/pt/es/it/fr
    norm = re.sub(
        r"^(the|a|an|o|a|os|as|um|uma|el|la|los|las|un|una|il|lo|la|le|gli|i|un'|l'|le|la|les|un|une)\s+", "", norm
    ).strip()
    return norm


def levenshtein(s1: str, s2: str) -> int:
    """Compute Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        curr = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev[j + 1] + 1
            deletions = curr[j] + 1
            substitutions = prev[j] + (c1 != c2)
            curr.append(min(insertions, deletions, substitutions))
        prev = curr
    return prev[-1]


def are_similar_answers(w1: str, w2: str) -> bool:
    """
    Check if two cleaned answer strings represent the same word with minor typos,
    phonetic variants, singular/plural, or internal space differences.
    Prevents players from evading collisions or earning unfair rarity points due to misspellings.
    """
    if not w1 or not w2:
        return False
    w1 = w1.strip().lower()
    w2 = w2.strip().lower()
    if w1 == w2:
        return True

    # Compound space differences: 'mona lisa' vs 'monalisa'
    s1 = w1.replace(" ", "")
    s2 = w2.replace(" ", "")
    if s1 == s2:
        return True

    # Plural / singular variants (English / Romance)
    if s1 + "s" == s2 or s2 + "s" == s1 or s1 + "es" == s2 or s2 + "es" == s1:
        return True

    min_len = min(len(s1), len(s2))
    if min_len <= 3:
        return False

    dist = levenshtein(s1, s2)
    ratio = difflib.SequenceMatcher(None, s1, s2).ratio()

    # For 4-letter words, avoid false collisions between distinct words (e.g. rome/rose, bear/beer).
    if min_len == 4:
        if len(s1) == len(s2):
            diff_chars = [(c1, c2) for c1, c2 in zip(s1, s2) if c1 != c2]
            if len(diff_chars) == 1:
                c1, c2 = diff_chars[0]
                if {c1, c2} in [{"i", "y"}, {"c", "k"}, {"s", "z"}]:
                    return True
            return False
        return dist == 1 and (s1 in s2 or s2 in s1) and ratio >= 0.88

    # For 5-letter words
    if min_len == 5:
        if len(s1) == len(s2):
            diff_chars = [(c1, c2) for c1, c2 in zip(s1, s2) if c1 != c2]
            if len(diff_chars) == 1:
                c1, c2 = diff_chars[0]
                if {c1, c2} in [{"i", "y"}, {"c", "k"}, {"s", "z"}, {"u", "v"}]:
                    return True
                return ratio >= 0.82
            return dist <= 2 and ratio >= 0.80
        return dist <= 1 and ratio >= 0.82

    # For 6-8 letter words
    if min_len <= 8:
        return dist <= 2 and ratio >= 0.80

    # For long words (9+ letters)
    return dist <= 3 and ratio >= 0.82


def cluster_answer_keys(
    entries: list[tuple[str, Any]],
    fuzzy: bool = True,
) -> dict[str, list[Any]]:
    """
    Cluster a list of (cleaned_key, item) pairs so that exact matches and close typos
    are merged into a single canonical collision group.
    Returns: dict mapping canonical_key -> list of grouped items.
    """
    clusters: list[tuple[str, list[Any]]] = []

    for key, val in entries:
        if not key:
            continue
        matched_idx = -1
        if fuzzy:
            for idx, (rep_key, _) in enumerate(clusters):
                if are_similar_answers(key, rep_key):
                    matched_idx = idx
                    break
        else:
            for idx, (rep_key, _) in enumerate(clusters):
                if key == rep_key:
                    matched_idx = idx
                    break

        if matched_idx >= 0:
            clusters[matched_idx][1].append(val)
        else:
            clusters.append((key, [val]))

    return {rep_key: vals for rep_key, vals in clusters}


def query_ollama(prompt: str, model: str = DEFAULT_MODEL, timeout: float = 5.5) -> Optional[str]:
    """Query local Ollama instance with strict timeout; returns response string or None."""
    url = f"{DEFAULT_OLLAMA_URL.rstrip('/')}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.1,
            "num_predict": 320,
        },
    }
    try:
        if not url.startswith(("http://", "https://")):
            raise ValueError("Unsupported Ollama URL scheme")
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})  # nosec B310
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
            if resp.status == 200:
                body = json.loads(resp.read().decode("utf-8"))
                return body.get("response")
    except Exception as exc:
        logger.debug("Ollama request failed or timed out: %s", exc)
        return None
    return None


def validate_player_answer(
    prompt_text: str,
    answer: str,
    sample_answers: Optional[list[str]] = None,
    obscurity_examples: Optional[list[str]] = None,
    use_ai: bool = True,
    timeout: float = 5.5,
) -> dict[str, Any]:
    """
    Arbitrate a player answer against a prompt.
    1. Fast deterministic check against curated sample answers (instant <1ms).
    2. Optional local AI arbitration via Qwen 30B on CT 104.
    3. Safe fallback marked for host review if unknown.
    """
    clean_ans = clean_answer_key(answer)
    if not clean_ans:
        return {
            "valid": False,
            "is_obscure": False,
            "source": "empty",
            "reason": "Empty answer",
            "pending_host_review": False,
        }

    # 1. Deterministic match against known answers
    samples = sample_answers or []
    for s in samples:
        if clean_answer_key(s) == clean_ans:
            is_obs = bool(obscurity_examples and any(clean_answer_key(o) == clean_ans for o in obscurity_examples))
            return {
                "valid": True,
                "is_obscure": is_obs,
                "source": "curated_match",
                "reason": "Matches verified sample answer",
                "pending_host_review": False,
            }

    # 2. Local AI verification if enabled
    if use_ai:
        ai_prompt = (
            f"Verify answer for a party game.\n"
            f"Prompt/Category: {prompt_text}\n"
            f"Player Answer: {answer}\n"
            f"Be concise. Reply strictly with JSON:\n"
            f'{{"valid": true or false, "is_obscure": true or false, "reason": "brief explanation under 15 words"}}'
        )
        ai_resp = query_ollama(ai_prompt, timeout=timeout)
        if ai_resp:
            try:
                clean_json = ai_resp.strip()
                if "```json" in clean_json:
                    clean_json = clean_json.split("```json")[1].split("```")[0].strip()
                elif "```" in clean_json:
                    clean_json = clean_json.split("```")[1].split("```")[0].strip()
                parsed = json.loads(clean_json)
                return {
                    "valid": bool(parsed.get("valid", True)),
                    "is_obscure": bool(parsed.get("is_obscure", False)),
                    "source": "ai_evaluation",
                    "reason": str(parsed.get("reason") or "Evaluated by AI"),
                    "pending_host_review": False,
                }
            except Exception as e:
                logger.debug("Failed to parse Ollama JSON: %s", e)

    # 3. Rule-based offline fallback (assume valid pending host review if non-empty)
    return {
        "valid": True,
        "is_obscure": len(clean_ans) > 10,
        "source": "unverified_fallback",
        "reason": "Pending host review",
        "pending_host_review": True,
    }


def evaluate_prompt_quality(prompt_text: str, timeout: float = 3.0) -> dict[str, Any]:
    """Evaluate synthetic prompt clarity, estimated cardinality, and sample answers via LLM."""
    query = (
        f'Analyze this party game prompt: "{prompt_text}"\n'
        f"1. Is it clear and grammatically sound?\n"
        f"2. How many valid real-world answers exist? (cardinality)\n"
        f"3. Give 3-5 example answers.\n"
        f"4. Rate party fun from 1 to 10.\n"
        f'Respond in JSON with keys: "clear" (bool), "cardinality" (int), "examples" (list of strings), "fun_rating" (int).'
    )
    raw = query_ollama(query, timeout=timeout)
    if raw:
        try:
            return json.loads(raw)
        except Exception:
            pass
    return {
        "clear": True,
        "cardinality": 15,
        "examples": [],
        "fun_rating": 8,
    }
