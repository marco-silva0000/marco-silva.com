import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "mistral")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
LLM_TIMEOUT = int(os.environ.get("LLM_TIMEOUT", "15"))

SYSTEM_PROMPT = (
    "Extract calendar event details from the provided text. "
    "Return JSON with: title, start (ISO 8601), end (ISO 8601 or null), location, description. "
    "If a field is not found, use a sensible default. For dates without a year, assume the current year."
)

EVENT_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "start": {"type": "string", "description": "ISO 8601 datetime"},
        "end": {"type": ["string", "null"], "description": "ISO 8601 datetime or null"},
        "location": {"type": "string"},
        "description": {"type": "string"},
    },
    "required": ["title", "start"],
}


@dataclass
class EventSchema:
    title: str = "Event"
    start: str = ""
    end: str | None = None
    location: str = ""
    description: str = ""


def extract_event(source: str) -> dict:
    """Try Ollama first, fall back to Gemini on failure/timeout."""
    try:
        return _ollama_extract(source)
    except Exception as e:
        logger.warning("Ollama failed (%s), trying Gemini", e)
    try:
        return _gemini_extract(source)
    except Exception as e:
        logger.error("Gemini also failed (%s), returning defaults", e)
    return _fallback(source)


def _ollama_extract(source: str) -> dict:
    import ollama

    client = ollama.Client(host=OLLAMA_URL, timeout=LLM_TIMEOUT)
    resp = client.chat(
        model=OLLAMA_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": source},
        ],
        format=EVENT_JSON_SCHEMA,
    )
    data = json.loads(resp.message.content)
    return _validate(data)


def _gemini_extract(source: str) -> dict:
    if not GEMINI_API_KEY:
        raise RuntimeError("No GEMINI_API_KEY configured")

    from google import genai

    client = genai.Client(api_key=GEMINI_API_KEY)
    resp = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=f"{SYSTEM_PROMPT}\n\n{source}",
        config=genai.types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema={
                "type": "OBJECT",
                "properties": {
                    "title": {"type": "STRING"},
                    "start": {"type": "STRING"},
                    "end": {"type": "STRING"},
                    "location": {"type": "STRING"},
                    "description": {"type": "STRING"},
                },
                "required": ["title", "start"],
            },
        ),
    )
    data = json.loads(resp.text)
    return _validate(data)


def _validate(data: dict) -> dict:
    event = EventSchema(
        title=data.get("title", "Event"),
        start=data.get("start", ""),
        end=data.get("end"),
        location=data.get("location", ""),
        description=data.get("description", ""),
    )
    return asdict(event)


def _fallback(source: str) -> dict:
    now = datetime.now().replace(hour=18, minute=0, second=0, microsecond=0)
    return asdict(
        EventSchema(
            title="Event",
            start=now.isoformat(),
            description=f"Could not extract from: {source[:100]}",
        )
    )
