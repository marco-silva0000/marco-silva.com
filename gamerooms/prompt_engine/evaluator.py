"""AI Evaluation and Answer Arbitration for party game prompts.

Integrates with local Ollama (`qwen3:30b` on CT 104) with strict timeouts
and robust offline deterministic fallbacks.
"""

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
    norm = re.sub(r"^(the|a|an|o|a|os|as|um|uma|el|la|los|las|un|una|il|lo|la|le|gli|i|un'|l'|le|la|les|un|une)\s+", "", norm).strip()
    return norm


def query_ollama(prompt: str, model: str = DEFAULT_MODEL, timeout: float = 2.5) -> Optional[str]:
    """Query local Ollama instance with strict timeout; returns response string or None."""
    url = f"{DEFAULT_OLLAMA_URL.rstrip('/')}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.2,
            "num_predict": 180,
        },
    }
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
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
    timeout: float = 2.5,
) -> dict[str, Any]:
    """
    Arbitrate a player answer against a prompt.
    1. Fast deterministic check against curated sample answers.
    2. Optional local AI arbitration via qwen3:30b.
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
            f"Question/Prompt: \"{prompt_text}\"\n"
            f"Player Submitted Answer: \"{answer}\"\n"
            f"Is this player answer a factually valid, truthful, and appropriate answer to the prompt? "
            f"Also decide if it is creative/obscure (not the most obvious answer).\n"
            f"Reply ONLY in JSON with keys: \"valid\" (boolean), \"is_obscure\" (boolean), \"reason\" (short string)."
        )
        ai_resp = query_ollama(ai_prompt, timeout=timeout)
        if ai_resp:
            try:
                parsed = json.loads(ai_resp)
                return {
                    "valid": bool(parsed.get("valid", True)),
                    "is_obscure": bool(parsed.get("is_obscure", False)),
                    "source": "ai_evaluation",
                    "reason": parsed.get("reason", "Evaluated by AI"),
                    "pending_host_review": False,
                }
            except Exception:
                pass

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
        f"Analyze this party game prompt: \"{prompt_text}\"\n"
        f"1. Is it clear and grammatically sound?\n"
        f"2. How many valid real-world answers exist? (cardinality)\n"
        f"3. Give 3-5 example answers.\n"
        f"4. Rate party fun from 1 to 10.\n"
        f"Respond in JSON with keys: \"clear\" (bool), \"cardinality\" (int), \"examples\" (list of strings), \"fun_rating\" (int)."
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
