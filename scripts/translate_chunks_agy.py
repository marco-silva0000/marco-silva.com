#!/usr/bin/env python3
"""Credit-Optimized Systematic Localization Automation using `agy`.

Optimizations built in to minimize token & credit consumption:
1. Default model: `gemini-3.8-flash-low` with `--effort low` (short-window Flash/Hydrogen pool,
   minimal reasoning token overhead, falling back only to `gemini-4-hydrogen-low` / Flash-Medium /
   Argon-Low — never into costly Opus/Sonnet/Argon-High).
2. Zero-credit local prefill (`prefill_catalogs_locally`): fills curated in-repo dictionaries,
   case/punctuation/emoji variants, and universal brand invariants before touching `agy`.
3. Cognate persistence (`locale/.translated_cognates.json`): prevents infinite re-translation
   of legitimate cognates where the target language matches English (e.g. `Lobby`, `Password`).
4. Minimal-overhead CLI invocation: runs `agy` in `cwd=/tmp` with `--disable-slash-commands`
   and no tool-permission scanning so repository docs/`AGENTS.md` are never injected as context.
5. Compact JSON prompts: omits verbose template file-path `context` columns (~70% smaller input)
   and strips pretty whitespace.
6. Multi-language matrix batching (`--langs-per-call`, default 6) & language tiers (`--tier`),
   cutting CLI calls and system prompt overhead by up to ~6x.
"""

import argparse
import csv
import json
import re
import subprocess
import sys
import time
from pathlib import Path

# Resolve base directories
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent if (SCRIPT_DIR.parent / "manage.py").exists() else Path.cwd()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from scripts.translations_tool import (
        COGNATES_FILE,
        LANGUAGE_NAMES,
        LANGUAGES,
        UNIVERSAL_UNCHANGED_TERMS,
        extract_translatable_strings,
        get_locale_dir,
        is_entry_untranslated,
        load_all_catalogs,
        load_cognates,
        parse_po_file,
        prefill_catalogs_locally,
        save_cognates,
        write_po_file,
    )
except ImportError:
    COGNATES_FILE = PROJECT_ROOT / "locale" / ".translated_cognates.json"
    LANGUAGES = ["en", "pt", "es", "it", "fr", "de", "el", "ru", "hi", "kn", "ar", "fa", "ur"]
    LANGUAGE_NAMES = {c: c.upper() for c in LANGUAGES}
    UNIVERSAL_UNCHANGED_TERMS = {"CTFs", "planz", "pictionary", "Mafia", "Limbo", "blog", "Codenames"}

    def get_locale_dir(lang_code):
        return PROJECT_ROOT / "locale" / lang_code

    def parse_po_file(p):
        return {}

    def write_po_file(lang_code, entries, p):
        pass

    def load_cognates(path=None):
        return {}

    def save_cognates(cognates, path=None):
        pass

    def is_entry_untranslated(val, en_val, lang_code, cognates=None):
        v = (val or "").strip()
        en = (en_val or "").strip()
        if lang_code == "en" or en in UNIVERSAL_UNCHANGED_TERMS or len(en) <= 2:
            return False
        if not v:
            return True
        if v == en:
            return not (cognates and en in cognates.get(lang_code, ()))
        return False

    def extract_translatable_strings():
        return {}

    def load_all_catalogs():
        return {}

    def prefill_catalogs_locally(*args, **kwargs):
        return {}


DEFAULT_MODEL = "gemini-3.8-flash-low"
DEFAULT_EFFORT = "low"
FALLBACK_MODELS = [
    "gemini-3.8-flash-low",
    "gemini-4-hydrogen-low",
    "gemini-3.8-flash-medium",
    "gemini-4-hydrogen-medium",
    "gemini-4-argon-low",
]

TIER_CORE_LANGS = [
    "it-or",
    "pt",
    "es",
    "it",
    "fr",
    "de",
    "el",
    "ru",
    "hi",
    "kn",
    "ar",
    "fa",
    "ur",
]
TIER_PRIORITY_LANGS = TIER_CORE_LANGS + [
    "pl",
    "fi",
    "sv",
    "sw",
    "az",
    "nl",
    "ja",
    "ko",
    "zh-cn",
    "zh-tw",
]

DEFAULT_PRIORITY_LANGS = TIER_PRIORITY_LANGS
LANG_ALIASES = {"fn": "fi", "oritano": "it-or", "it_or": "it-or", "or": "it-or"}

EXHAUSTED_MODELS: set[str] = set()
CURRENT_ACTIVE_MODEL: str | None = None


def get_clean_language_name(code: str) -> str:
    """Return clean human-readable language name without flag emoji."""
    if code == "it-or":
        return "Oritano (Northern Salentino dialect of Oria, Brindisi, Puglia, Southern Italy)"
    raw = LANGUAGE_NAMES.get(code, code.upper())
    parts = raw.split(" ", 1)
    return parts[1] if len(parts) > 1 else raw


def strip_ansi(text: str) -> str:
    """Strip terminal ANSI escape sequences."""
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


def extract_json_response(raw_output: str) -> dict:
    """Extract and parse JSON object from agy CLI output."""
    clean = strip_ansi(raw_output).strip()

    fence_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", clean)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except Exception:
            pass

    try:
        return json.loads(clean)
    except Exception:
        pass

    start = clean.find("{")
    end = clean.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = clean[start : end + 1]
        try:
            return json.loads(candidate)
        except Exception:
            pass

    raise ValueError(f"Could not parse valid JSON from output:\n{clean[:300]}...")


def build_translation_prompt(items: list[dict], target_lang_code: str, target_lang_name: str) -> str:
    """Build compact single-language JSON prompt without file-path context bloat."""
    source_map = {str(item["id"]): item.get("source") or item.get("en", "") for item in items}
    compact_json = json.dumps(source_map, ensure_ascii=False, separators=(",", ":"))
    return (
        f"Translate UI/game strings (portfolio, blog, Lupus/Werewolf, Codenames, Word Impostor, Emojinary) "
        f"from English to idiomatic {target_lang_name} ({target_lang_code}).\n"
        "Preserve %s, %(name)s, {{var}}, HTML tags, markdown, emojis, and technical names. "
        "Keep proper cognates unchanged if natural.\n"
        'Return ONLY raw JSON mapping each numeric id string to its translation (e.g. {"0":"..."}):\n'
        f"{compact_json}"
    )


def build_multi_lang_prompt(items: list[dict], lang_specs: list[tuple[str, str]]) -> str:
    """Build compact matrix prompt translating one source batch into multiple languages at once."""
    source_map = {str(item["id"]): item.get("source") or item.get("en", "") for item in items}
    compact_json = json.dumps(source_map, ensure_ascii=False, separators=(",", ":"))
    langs_desc = ", ".join(f"{code}={name}" for code, name in lang_specs)
    sample_lang = lang_specs[0][0]
    return (
        f"Translate UI/game strings (portfolio, blog, Lupus/Werewolf, Codenames, Word Impostor, Emojinary) "
        f"from English into ALL of: {langs_desc}.\n"
        "Preserve %s, %(name)s, {{var}}, HTML tags, markdown, emojis, and technical names. "
        "Keep valid cognates unchanged.\n"
        f'Return ONLY raw nested JSON {{"<id>":{{"<lang>":"<text>",...}}}} (e.g. {{"0":{{"{sample_lang}":"..."}}}}):\n'
        f"{compact_json}"
    )


def get_next_available_model(preferred: str | None) -> str | None:
    """Return preferred model if not exhausted, else next available lightweight fallback model."""
    global CURRENT_ACTIVE_MODEL
    if CURRENT_ACTIVE_MODEL and CURRENT_ACTIVE_MODEL not in EXHAUSTED_MODELS:
        return CURRENT_ACTIVE_MODEL
    if preferred and preferred not in EXHAUSTED_MODELS:
        CURRENT_ACTIVE_MODEL = preferred
        return CURRENT_ACTIVE_MODEL
    for candidate in FALLBACK_MODELS:
        if candidate not in EXHAUSTED_MODELS:
            CURRENT_ACTIVE_MODEL = candidate
            return CURRENT_ACTIVE_MODEL
    return None


def call_agy(
    prompt: str,
    model: str | None = DEFAULT_MODEL,
    effort: str | None = DEFAULT_EFFORT,
    timeout: int = 180,
    retries: int = 2,
    allow_tools: bool = False,
) -> dict:
    """Invoke `agy` cleanly from /tmp without loading repo AGENTS.md or slash commands."""
    attempt = 1
    while attempt <= retries:
        active_model = get_next_available_model(model)
        if active_model is None:
            print("\n🛑 All configured Flash/Hydrogen agy models have reached their quota — aborting run.")
            print("   Progress so far is saved; re-run later to resume.")
            sys.exit(3)

        cmd = ["agy"]
        if allow_tools:
            cmd.append("--dangerously-skip-permissions")
        cmd.extend(["--disable-slash-commands", "--model", active_model])
        if effort:
            cmd.extend(["--effort", effort])
        cmd.extend(["-p", prompt])

        try:
            res = subprocess.run(cmd, cwd="/tmp", capture_output=True, text=True, timeout=timeout)
            if res.returncode != 0:
                err = (res.stderr or "") + (res.stdout or "")
                if "RESOURCE_EXHAUSTED" in err or "quota reached" in err.lower():
                    EXHAUSTED_MODELS.add(active_model)
                    nxt = get_next_available_model(model)
                    if nxt:
                        print(f"\n      🔄 Model '{active_model}' quota reached — switching to '{nxt}'...")
                        continue
                    print(f"\n🛑 agy quota exhausted on all configured models. {res.stderr.strip()[:200]}")
                    sys.exit(3)
                print(f"      ⚠️  agy exited with code {res.returncode}. Stderr: {res.stderr.strip()[:200]}")
                if attempt < retries:
                    attempt += 1
                    time.sleep(2)
                    continue
                raise RuntimeError(f"agy failed with code {res.returncode}: {res.stderr}")

            return extract_json_response(res.stdout)

        except subprocess.TimeoutExpired:
            print(f"      ⏳ agy timed out after {timeout}s (attempt {attempt}/{retries})")
            if attempt < retries:
                attempt += 1
                time.sleep(3)
                continue
            raise
        except Exception as e:
            if attempt < retries:
                print(f"      ⚠️  Parse error on attempt {attempt}/{retries}: {e}. Retrying...")
                attempt += 1
                time.sleep(2)
                continue
            raise
    raise RuntimeError("Exceeded max retries calling agy")


def normalize_lang_list(langs: list[str] | None) -> list[str] | None:
    """Normalize language codes (e.g. 'fn' -> ['fi', 'fr'], 'sw' -> ['sv', 'sw'])."""
    if not langs:
        return None
    result = []
    for raw in langs:
        low = raw.lower().strip()
        code = LANG_ALIASES.get(low, low)
        if low == "fn":
            for c in ("fi", "fr"):
                if c not in result:
                    result.append(c)
        elif low == "sw":
            for c in ("sv", "sw"):
                if c not in result:
                    result.append(c)
        elif code not in result:
            result.append(code)
    return result


def is_untranslated(val: str, en_val: str, lang_code: str, cognates: dict[str, set[str]] | None = None) -> bool:
    """Determine if a string still needs translation (respecting tracked cognates and invariants)."""
    loaded_cog = cognates if cognates is not None else load_cognates()
    return is_entry_untranslated(val, en_val, lang_code, cognates=loaded_cog)


def sync_csv_to_po(lang: str, rows: list[dict]) -> None:
    """Synchronize rows for a language into its django.po, recompile django.mo, and update per-lang CSV if present."""
    try:
        po_path = get_locale_dir(lang) / "LC_MESSAGES" / "django.po"
        catalog = parse_po_file(po_path)
        updated = False
        for r in rows:
            msgid = r.get("msgid", "").strip()
            val = r.get(lang, "").strip()
            if msgid and val and catalog.get(msgid) != val:
                catalog[msgid] = val
                updated = True
        if updated:
            write_po_file(lang, catalog, po_path)

        per_lang_csv = PROJECT_ROOT / "locale" / f"translations_{lang}.csv"
        if per_lang_csv.exists():
            with open(per_lang_csv, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["msgid", "context", "en", lang])
                writer.writeheader()
                for r in rows:
                    writer.writerow(
                        {
                            "msgid": r.get("msgid", ""),
                            "context": r.get("context", ""),
                            "en": r.get("en", ""),
                            lang: r.get(lang, ""),
                        }
                    )
    except Exception as e:
        print(f"      ⚠️  Warning: could not sync to .po for {lang}: {e}")


def _resolve_target_langs(
    avail_langs: list[str],
    target_langs: list[str] | None,
    tier: str,
) -> list[str]:
    """Select target languages filtered by explicit --lang or requested --tier."""
    if target_langs:
        return [code for code in target_langs if code in avail_langs]
    if tier == "core":
        return [code for code in TIER_CORE_LANGS if code in avail_langs]
    if tier == "priority":
        return [code for code in TIER_PRIORITY_LANGS if code in avail_langs]
    priority_first = [code for code in TIER_PRIORITY_LANGS if code in avail_langs]
    remaining = [code for code in avail_langs if code not in priority_first]
    return priority_first + remaining


def process_csv_file(
    csv_path: Path,
    target_langs: list[str] | None = None,
    chunk_size: int = 80,
    model: str | None = DEFAULT_MODEL,
    effort: str | None = DEFAULT_EFFORT,
    timeout: int = 240,
    dry_run: bool = False,
    sync_po: bool = True,
    max_chunks: int | None = None,
    langs_per_call: int = 6,
    tier: str = "priority",
    allow_tools: bool = False,
) -> int:
    """Process a CSV file with multi-language batching and immediate disk persistence."""
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    if not fieldnames or "msgid" not in fieldnames:
        print(f"  ❌ Skipping {csv_path.name}: missing 'msgid' column.")
        return 0

    avail_langs = [col for col in fieldnames if col not in ("msgid", "context", "en")]
    langs_to_process = _resolve_target_langs(avail_langs, target_langs, tier)
    if not langs_to_process:
        return 0

    cognates = load_cognates()
    cognates_dirty = False

    print(f"\n📂 Processing CSV: {csv_path.name} ({len(langs_to_process)} language(s), batch={langs_per_call})")

    # Build pending row index sets per language & sort by pending count so similar batches cluster together
    pending_by_lang: dict[str, set[int]] = {}
    for lang in langs_to_process:
        needed: set[int] = set()
        for idx, row in enumerate(rows):
            en_val = row.get("en", "") or row.get("msgid", "")
            if is_untranslated(row.get(lang, ""), en_val, lang, cognates=cognates):
                needed.add(idx)
        if needed:
            pending_by_lang[lang] = needed
        else:
            print(f"  ✅ [{LANGUAGE_NAMES.get(lang, lang)}] 100% complete! No missing strings.")

    active_langs = sorted(pending_by_lang.keys(), key=lambda c: len(pending_by_lang[c]))
    if not active_langs:
        return 0

    total_translated = 0
    batch_size = max(1, langs_per_call)

    for b_start in range(0, len(active_langs), batch_size):
        lang_batch = active_langs[b_start : b_start + batch_size]
        union_indices = sorted({idx for lang in lang_batch for idx in pending_by_lang[lang]})
        total_chunks = (len(union_indices) + chunk_size - 1) // chunk_size
        batch_label = ", ".join(lang_batch)
        print(f"  🌐 Batch [{batch_label}]: {len(union_indices)} unique source strings ({total_chunks} call(s))...")

        chunks_done = 0
        for c_start in range(0, len(union_indices), chunk_size):
            if max_chunks and chunks_done >= max_chunks:
                print(f"  🛑 Reached max chunk limit ({max_chunks}). Stopping batch.")
                break

            row_slice = union_indices[c_start : c_start + chunk_size]
            chunk_items = [
                {"id": str(r_idx), "source": rows[r_idx].get("en", "") or rows[r_idx].get("msgid", "")}
                for r_idx in row_slice
            ]
            # Only ask for languages that still need at least one item in this chunk slice
            slice_langs = [lang for lang in lang_batch if any(r_idx in pending_by_lang[lang] for r_idx in row_slice)]
            if not slice_langs:
                continue

            print(
                f"    ➡️  Chunk {chunks_done + 1}/{total_chunks} ({len(chunk_items)} strings × {len(slice_langs)} lang(s))...",
                end="",
                flush=True,
            )

            if dry_run:
                print(" [DRY RUN - skipped agy call]")
                chunks_done += 1
                continue

            if len(slice_langs) == 1:
                prompt = build_translation_prompt(chunk_items, slice_langs[0], get_clean_language_name(slice_langs[0]))
            else:
                lang_specs = [(lang, get_clean_language_name(lang)) for lang in slice_langs]
                prompt = build_multi_lang_prompt(chunk_items, lang_specs)

            t0 = time.time()
            try:
                raw_resp = call_agy(
                    prompt,
                    model=model,
                    effort=effort,
                    timeout=timeout,
                    allow_tools=allow_tools,
                )
                elapsed = time.time() - t0
                applied = 0

                for r_idx in row_slice:
                    sid = str(r_idx)
                    en_val = (rows[r_idx].get("en", "") or rows[r_idx].get("msgid", "")).strip()
                    payload = raw_resp.get(sid)
                    if payload is None:
                        continue

                    if len(slice_langs) == 1:
                        lang = slice_langs[0]
                        if isinstance(payload, dict):
                            tr_val = str(payload.get(lang, "")).strip()
                        else:
                            tr_val = str(payload).strip()
                        if tr_val and r_idx in pending_by_lang[lang]:
                            rows[r_idx][lang] = tr_val
                            applied += 1
                            if tr_val == en_val:
                                cognates.setdefault(lang, set()).add(en_val)
                                cognates_dirty = True
                    elif isinstance(payload, dict):
                        for lang in slice_langs:
                            if r_idx not in pending_by_lang[lang]:
                                continue
                            tr_val = str(payload.get(lang, "")).strip()
                            if tr_val:
                                rows[r_idx][lang] = tr_val
                                applied += 1
                                if tr_val == en_val:
                                    cognates.setdefault(lang, set()).add(en_val)
                                    cognates_dirty = True

                with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)

                if cognates_dirty:
                    save_cognates(cognates)
                    cognates_dirty = False

                if sync_po:
                    for lang in slice_langs:
                        if lang in LANGUAGES:
                            sync_csv_to_po(lang, rows)

                print(f" ✅ OK ({applied} cells in {elapsed:.1f}s)")
                total_translated += applied
                chunks_done += 1

            except Exception as e:
                print(f" ❌ Failed: {e}")
                print("      Progress so far saved; continuing...")

    return total_translated


def process_po_file(
    po_path: Path,
    lang_code: str,
    chunk_size: int = 80,
    model: str | None = DEFAULT_MODEL,
    effort: str | None = DEFAULT_EFFORT,
    timeout: int = 240,
    dry_run: bool = False,
    max_chunks: int | None = None,
    allow_tools: bool = False,
) -> int:
    """Process a django.po file directly, translating missing entries chunk by chunk."""
    display_label = LANGUAGE_NAMES.get(lang_code, lang_code)
    lang_name = get_clean_language_name(lang_code)
    print(f"\n📂 Processing PO: {po_path.relative_to(PROJECT_ROOT) if PROJECT_ROOT in po_path.parents else po_path}")

    catalog = parse_po_file(po_path)
    if not catalog:
        print(f"  ❌ Skipping {po_path.name}: empty or missing catalog.")
        return 0

    cognates = load_cognates()
    pending = []
    for idx, (msgid, msgstr) in enumerate(catalog.items()):
        if not msgid:
            continue
        if is_untranslated(msgstr, msgid, lang_code, cognates=cognates):
            pending.append({"id": str(idx), "msgid": msgid, "source": msgid})

    if not pending:
        print(f"  ✅ [{display_label}] 100% complete! No missing strings.")
        return 0

    total_chunks = (len(pending) + chunk_size - 1) // chunk_size
    print(f"  🌐 [{display_label}] {len(pending)} strings pending ({total_chunks} chunk(s))...")

    chunks_done = 0
    total_translated = 0

    for chunk_idx in range(0, len(pending), chunk_size):
        if max_chunks and chunks_done >= max_chunks:
            print(f"  🛑 Reached max chunk limit ({max_chunks}). Stopping.")
            break

        chunk = pending[chunk_idx : chunk_idx + chunk_size]
        chunk_num = chunks_done + 1
        print(f"    ➡️  Chunk {chunk_num}/{total_chunks} ({len(chunk)} items)...", end="", flush=True)

        if dry_run:
            print(" [DRY RUN - skipped agy call]")
            chunks_done += 1
            continue

        prompt = build_translation_prompt(chunk, lang_code, lang_name)
        t0 = time.time()
        try:
            translations = call_agy(prompt, model=model, effort=effort, timeout=timeout, allow_tools=allow_tools)
            elapsed = time.time() - t0

            applied = 0
            cognates_dirty = False
            for item in chunk:
                sid = item["id"]
                msgid = item["msgid"]
                if sid in translations and translations[sid]:
                    tr_val = str(translations[sid]).strip()
                    catalog[msgid] = tr_val
                    applied += 1
                    if tr_val == msgid.strip():
                        cognates.setdefault(lang_code, set()).add(msgid.strip())
                        cognates_dirty = True

            if cognates_dirty:
                save_cognates(cognates)
            write_po_file(lang_code, catalog, po_path)

            print(f" ✅ OK ({applied} strings in {elapsed:.1f}s, saved & compiled .mo)")
            total_translated += applied
            chunks_done += 1

        except Exception as e:
            print(f" ❌ Failed: {e}")
            print("      Continuing...")

    return total_translated


def discover_files(
    target_dir: Path, file_type: str = "auto", explicit_files: list[str] | None = None
) -> tuple[list[Path], list[Path]]:
    """Discover CSV and PO files in target_dir."""
    if explicit_files:
        csv_files = []
        po_files = []
        for ef in explicit_files:
            p = Path(ef) if Path(ef).is_absolute() else (target_dir / ef)
            if not p.exists():
                print(f"⚠️  Warning: Specified file '{ef}' does not exist.")
                continue
            if p.suffix.lower() == ".csv":
                csv_files.append(p)
            elif p.suffix.lower() == ".po":
                po_files.append(p)
        return sorted(csv_files), sorted(po_files)

    csv_files = []
    po_files = []

    if file_type in ("auto", "csv", "all"):
        master_path = target_dir / "translations_master.csv"
        if master_path.exists():
            csv_files.append(master_path)
        else:
            per_lang = list(target_dir.glob("translations_*.csv"))
            csv_files.extend(sorted(per_lang))
            if not csv_files:
                csv_files.extend(sorted(target_dir.glob("*.csv")))

    if file_type in ("po", "all") or (file_type == "auto" and not csv_files):
        po_files.extend(target_dir.glob("*/LC_MESSAGES/django.po"))
        po_files.extend(target_dir.glob("*.po"))

    return sorted(set(csv_files), key=lambda p: (p.name == "translations_master.csv", p.name)), sorted(set(po_files))


def main():
    parser = argparse.ArgumentParser(
        description="Credit-Optimized Localization Automation using Antigravity (agy)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  # Run default priority languages batched 6-at-a-time on gemini-3.8-flash-low:
  ./translate_with_agy.py

  # Only translate the 12 core site/game languages (lowest credit spend):
  ./translate_with_agy.py --tier core

  # Specific languages batched together:
  ./translate_with_agy.py --lang de nl ja ko zh-cn zh-tw

  # Check dry-run plan (0 credits):
  ./translate_with_agy.py --dry-run
""",
    )

    parser.add_argument(
        "--dir", default=".", help="Directory to scan for translation files (default: current directory)."
    )
    parser.add_argument("--files", nargs="+", help="Explicit file(s) to process instead of scanning the directory.")
    parser.add_argument(
        "--type",
        choices=["auto", "csv", "po", "all"],
        default="auto",
        help="File type filter (auto: CSV if present, else PO; csv; po; all).",
    )
    parser.add_argument("--lang", nargs="+", help="Filter to specific target language code(s) (e.g. pt es de fr).")
    parser.add_argument(
        "--tier",
        choices=["core", "priority", "all"],
        default="priority",
        help="Language tier when --lang is omitted (default: priority=22 langs; core=12; all=63).",
    )
    parser.add_argument(
        "--langs-per-call",
        type=int,
        default=6,
        help="Target languages batched into a single agy call when processing master CSV (default: 6).",
    )
    parser.add_argument("--chunk-size", type=int, default=80, help="Strings per agy call (default: 80).")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Model for agy (default: {DEFAULT_MODEL}). Falls back strictly along Flash/Hydrogen-Low.",
    )
    parser.add_argument(
        "--effort",
        choices=["low", "medium", "high", "xhigh", "max"],
        default=DEFAULT_EFFORT,
        help=f"Reasoning effort level for agy (default: {DEFAULT_EFFORT}).",
    )
    parser.add_argument("--timeout", type=int, default=240, help="Timeout per agy call in seconds (default: 240s).")
    parser.add_argument(
        "--max-chunks", type=int, default=None, help="Maximum chunks per batch (useful for capped runs)."
    )
    parser.add_argument("--no-prefill", action="store_true", help="Skip 0-credit local prefill before calling agy.")
    parser.add_argument("--no-sync-po", action="store_true", help="Do not sync CSV changes back to .po/.mo files.")
    parser.add_argument(
        "--allow-tools", action="store_true", help="Pass --dangerously-skip-permissions (not needed for JSON)."
    )
    parser.add_argument("--dry-run", action="store_true", help="Show batch plan without executing agy calls.")

    args = parser.parse_args()
    args.lang = normalize_lang_list(args.lang)

    target_dir = Path(args.dir).resolve()
    print("==================================================================")
    print("  🌍 Credit-Optimized Antigravity (agy) Localization Pipeline")
    print("==================================================================")
    print(f"Target Directory: {target_dir}")
    print(f"Model / Effort:   {args.model} ({args.effort})")
    print(f"Chunk / Batch:    {args.chunk_size} strings × {args.langs_per_call} lang(s)/call")
    print(f"Target Tier:      {', '.join(args.lang) if args.lang else args.tier}")
    if args.dry_run:
        print("Mode:             DRY-RUN (0 credits — no agy calls)")
    print("------------------------------------------------------------------")

    # 1. Zero-credit local prefill first
    if not args.no_prefill and not args.dry_run and not args.no_sync_po:
        try:
            extracted = extract_translatable_strings()
            catalogs = load_all_catalogs()
            stats = prefill_catalogs_locally(catalogs, extracted, cleanup_placeholders=True)
            for lang_code in LANGUAGES:
                if lang_code == "en":
                    catalogs["en"] = {s: s for s in extracted}
                po_p = get_locale_dir(lang_code) / "LC_MESSAGES" / "django.po"
                write_po_file(lang_code, catalogs[lang_code], po_p)
            print(
                f"⚡ Local prefill (0 credits): {stats.get('filled', 0)} filled, "
                f"{stats.get('placeholders_cleared', 0)} placeholders cleaned, "
                f"{stats.get('cognates_saved', 0)} cognates tracked."
            )
        except Exception as e:
            print(f"⚠️  Local prefill warning: {e}")

    csv_files, po_files = discover_files(target_dir, file_type=args.type, explicit_files=args.files)
    if not csv_files and not po_files:
        print(f"❌ No translation files (.csv or .po) found in {target_dir}.")
        sys.exit(1)

    t_start = time.time()
    grand_total = 0

    for cp in csv_files:
        if cp.name == "translations_master.csv" and not args.no_sync_po and not args.dry_run:
            try:
                from scripts.translations_tool import cmd_export_csv

                class PreExportArgs:
                    lang = "all"
                    output = str(cp)
                    untranslated_only = False

                cmd_export_csv(PreExportArgs())
            except Exception:
                pass

        grand_total += process_csv_file(
            cp,
            target_langs=args.lang,
            chunk_size=args.chunk_size,
            model=args.model,
            effort=args.effort,
            timeout=args.timeout,
            dry_run=args.dry_run,
            sync_po=not args.no_sync_po,
            max_chunks=args.max_chunks,
            langs_per_call=args.langs_per_call,
            tier=args.tier,
            allow_tools=args.allow_tools,
        )

    for pp in po_files:
        lang_code = pp.parent.parent.name if pp.parent.name == "LC_MESSAGES" else pp.stem
        if args.lang and lang_code not in args.lang:
            continue
        grand_total += process_po_file(
            pp,
            lang_code=lang_code,
            chunk_size=args.chunk_size,
            model=args.model,
            effort=args.effort,
            timeout=args.timeout,
            dry_run=args.dry_run,
            max_chunks=args.max_chunks,
            allow_tools=args.allow_tools,
        )

    elapsed_total = time.time() - t_start

    if grand_total > 0 and not args.no_sync_po and not args.dry_run:
        try:
            from scripts.translations_tool import cmd_export_csv

            class ExportArgs:
                lang = "all"
                output = str(target_dir / "translations_master.csv")
                untranslated_only = False

            cmd_export_csv(ExportArgs())
        except Exception as e:
            print(f"⚠️  Note: Could not refresh master CSV: {e}")

    print("\n==================================================================")
    print(f"🎉 Finished in {elapsed_total:.1f}s! Cells translated & saved: {grand_total}")
    print("==================================================================")


if __name__ == "__main__":
    main()
