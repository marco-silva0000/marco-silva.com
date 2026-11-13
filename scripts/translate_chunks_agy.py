#!/usr/bin/env python3
"""Systematic Localization Automation using `agy --dangerously-skip-permissions`.

This script iterates through translation files (.csv and/or .po) in a given directory
(defaults to current working directory or locale/), extracts untranslated text into
structured chunks, spawns `agy --dangerously-skip-permissions` with domain-specific
prompts, parses the translated JSON output, and immediately persists updates to disk.

Features:
- Handles per-language CSVs (`translations_<lang>.csv`), master CSV (`translations_master.csv`),
  and GNU gettext PO files (`locale/<lang>/LC_MESSAGES/django.po`).
- Context-aware prompting: informs the agent of the target language, web & game domain,
  HTML tag safety, Django template variables, and Werewolf / Lupus in Tabula terminology.
- Safe chunking (default 20 items) with immediate disk flushing after every chunk.
- Automatic PO synchronization and .mo binary compilation via translations_tool.
- Resilient JSON parsing supporting both direct JSON and markdown-fenced responses.
- Resumable: automatically skips already-translated strings on subsequent runs.
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

# Attempt to load languages and compiler helpers from translations_tool
try:
    from scripts.translations_tool import (
        LANGUAGE_NAMES,
        LANGUAGES,
        get_locale_dir,
        parse_po_file,
        write_po_file,
    )
except ImportError:
    # Fallback definitions if run standalone
    LANGUAGES = [
        "af",
        "sq",
        "ar",
        "az",
        "eu",
        "bn",
        "be",
        "bg",
        "ca",
        "zh-cn",
        "zh-tw",
        "hr",
        "cs",
        "da",
        "nl",
        "en",
        "eo",
        "et",
        "tl",
        "fi",
        "fr",
        "gl",
        "ka",
        "de",
        "el",
        "gu",
        "ht",
        "iw",
        "hi",
        "hu",
        "is",
        "id",
        "ga",
        "it",
        "ja",
        "kn",
        "ko",
        "la",
        "lv",
        "lt",
        "mk",
        "ms",
        "mt",
        "no",
        "fa",
        "pl",
        "pt",
        "ro",
        "ru",
        "sr",
        "sk",
        "sl",
        "es",
        "sw",
        "sv",
        "ta",
        "te",
        "th",
        "tr",
        "uk",
        "ur",
        "vi",
        "cy",
        "yi",
    ]
    LANGUAGE_NAMES = {
        "es": "🇪🇸 Spanish",
        "pt": "🇵🇹 Portuguese",
        "it": "🇮🇹 Italian",
        "fr": "🇫🇷 French",
        "de": "🇩🇪 German",
        "el": "🇬🇷 Greek",
        "ru": "🇷🇺 Russian",
        "hi": "🇮🇳 Hindi",
        "kn": "🇮🇳 Kannada",
        "ar": "🇸🇦 Arabic",
        "fa": "🇮🇷 Persian",
        "ur": "🇵🇰 Urdu",
        "en": "🇬🇧 English",
        "ja": "🇯🇵 Japanese",
        "ko": "🇰🇷 Korean",
        "zh-cn": "🇨🇳 Chinese Simplified",
        "zh-tw": "🇨🇳 Chinese Traditional",
    }

    def parse_po_file(p):
        return {}

    def write_po_file(lang_code, entries, p):
        pass

    def get_locale_dir(lang_code):
        return PROJECT_ROOT / "locale" / lang_code


def get_clean_language_name(code: str) -> str:
    """Return clean human-readable language name without flag emoji."""
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

    # 1. Search for ```json ... ``` code fence
    fence_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", clean)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except Exception:
            pass

    # 2. Try direct json load
    try:
        return json.loads(clean)
    except Exception:
        pass

    # 3. Locate outermost curly brackets
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
    """Generate high-quality prompt for agy."""
    items_json = json.dumps(items, ensure_ascii=False, indent=2)
    return f"""You are a professional software localization specialist and native translator for {target_lang_name} ({target_lang_code}).

Context & Domain:
You are localizing user-facing copy for Marco Silva's web platform (marco-silva.com), which includes:
- Personal developer portfolio, resume/CV, photography galleries, and technical blog (Wagtail CMS).
- Real-time multiplayer games: Lupus in Tabula (Werewolf/Mafia social deduction party game) and Emojinary.
- Legal notices: Privacy policy and Terms of service.
Each item includes a 'context' field indicating which template or module it belongs to.

Translation Guidelines:
1. Translate the 'source' text into natural, idiomatic, and culturally fluent {target_lang_name}.
2. PRESERVE STRICTLY all technical formatting:
   - Django template tags and variables (e.g., %s, %(count)s, %(target)s, {{{{ player }}}}, {{{{ count }}}}, {{{{ total }}}}).
   - HTML tags and entities (e.g., <b>...</b>, <strong>, <span>, <a href="...">, <br>).
   - Markdown formatting (e.g., **, *, `, #).
   - Emojis and UI icons (e.g., 🐺, ✏️, 📸, 👑, 🛡️, 🌙, ☀️).
   - Keybindings and technical tool names (e.g., 'colemak + nvim', 'Ctrl+K').
3. For social deduction / Werewolf game roles (e.g., Seer, Werewolf, Villager, Medium, Bodyguard, Possessed, Mason), use standard canonical terminology recognized by players in {target_lang_name}.
4. If an item is already a universal brand name, punctuation mark, or code symbol (e.g. '+', 'CTFs', 'Wagtail'), keep it as-is or adapt appropriately.
5. Do NOT translate the 'id' or 'context' keys.

Required Output Format:
Output ONLY a single valid, parsable JSON object mapping each numeric id (as a string or number) to the translated string.
Example:
{{
  "0": "Traducción...",
  "1": "Otra traducción..."
}}
Do NOT wrap the output in markdown code blocks (no ```json).
Do NOT include any introduction, explanations, notes, or extra commentary.

Input Items to Translate:
{items_json}
"""


def call_agy(
    prompt: str, model: str | None = None, effort: str | None = None, timeout: int = 180, retries: int = 2
) -> dict:
    """Spawn agy --dangerously-skip-permissions with the given prompt and return parsed JSON."""
    cmd = ["agy", "--dangerously-skip-permissions"]
    if model:
        cmd.extend(["--model", model])
    if effort:
        cmd.extend(["--effort", effort])
    cmd.extend(["-p", prompt])

    for attempt in range(1, retries + 1):
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            if res.returncode != 0:
                print(f"      ⚠️  agy exited with code {res.returncode}. Stderr: {res.stderr.strip()[:200]}")
                if attempt < retries:
                    time.sleep(2)
                    continue
                raise RuntimeError(f"agy failed with code {res.returncode}: {res.stderr}")

            return extract_json_response(res.stdout)

        except subprocess.TimeoutExpired:
            print(f"      ⏳ agy timed out after {timeout}s (attempt {attempt}/{retries})")
            if attempt < retries:
                time.sleep(3)
                continue
            raise
        except Exception as e:
            if attempt < retries:
                print(f"      ⚠️  Parse error on attempt {attempt}/{retries}: {e}. Retrying...")
                time.sleep(2)
                continue
            raise


def is_untranslated(val: str, en_val: str, lang_code: str) -> bool:
    """Determine if a string needs translation."""
    v = val.strip()
    en = en_val.strip()
    if not v:
        return True
    if lang_code == "en":
        return False
    # If it is identical to English fallback, check if it's not a short symbol/emoji
    if v == en:
        if len(en) <= 3 or en.startswith("🐺") or en.startswith("✏️") or en.startswith("+"):
            return False
        return True
    return False


def process_csv_file(
    csv_path: Path,
    target_langs: list[str] | None = None,
    chunk_size: int = 20,
    model: str | None = None,
    effort: str | None = None,
    timeout: int = 180,
    dry_run: bool = False,
    sync_po: bool = True,
    max_chunks: int | None = None,
) -> int:
    """Process a single CSV file, translating untranslated entries chunk by chunk."""
    print(f"\n📂 Processing CSV: {csv_path.name}")

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    if not fieldnames or "msgid" not in fieldnames:
        print(f"  ❌ Skipping {csv_path.name}: missing 'msgid' column.")
        return 0

    # Determine languages present in this CSV
    avail_langs = [col for col in fieldnames if col not in ("msgid", "context", "en")]
    if target_langs:
        langs_to_process = [code for code in avail_langs if code in target_langs]
    else:
        langs_to_process = avail_langs

    if not langs_to_process:
        print(f"  ℹ️  No matching target language columns found in {csv_path.name}.")
        return 0

    total_translated = 0

    for lang in langs_to_process:
        lang_name = get_clean_language_name(lang)
        display_label = LANGUAGE_NAMES.get(lang, lang)

        # Collect rows needing translation for this language
        pending_items = []
        for idx, row in enumerate(rows):
            val = row.get(lang, "")
            en_val = row.get("en", "") or row.get("msgid", "")
            if is_untranslated(val, en_val, lang):
                pending_items.append(
                    {
                        "row_idx": idx,
                        "id": str(idx),
                        "source": en_val,
                        "context": row.get("context", ""),
                    }
                )

        if not pending_items:
            print(f"  ✅ [{display_label}] 100% complete! No missing strings.")
            continue

        total_chunks = (len(pending_items) + chunk_size - 1) // chunk_size
        print(f"  🌐 [{display_label}] {len(pending_items)} strings pending translation ({total_chunks} chunks)...")

        chunks_done = 0
        for chunk_idx in range(0, len(pending_items), chunk_size):
            if max_chunks and chunks_done >= max_chunks:
                print(f"  🛑 Reached max chunk limit ({max_chunks}). Stopping.")
                break

            chunk = pending_items[chunk_idx : chunk_idx + chunk_size]
            chunk_num = chunks_done + 1
            print(f"    ➡️  Chunk {chunk_num}/{total_chunks} ({len(chunk)} items)...", end="", flush=True)

            if dry_run:
                print(" [DRY RUN - skipped agy call]")
                chunks_done += 1
                continue

            # Build prompt
            prompt_items = [{"id": item["id"], "source": item["source"], "context": item["context"]} for item in chunk]
            prompt = build_translation_prompt(prompt_items, lang, lang_name)

            t0 = time.time()
            try:
                translations = call_agy(prompt, model=model, effort=effort, timeout=timeout)
                elapsed = time.time() - t0

                # Update in-memory rows
                applied = 0
                for item in chunk:
                    row_idx = item["row_idx"]
                    sid = item["id"]
                    if sid in translations and translations[sid]:
                        rows[row_idx][lang] = translations[sid].strip()
                        applied += 1
                    elif str(row_idx) in translations and translations[str(row_idx)]:
                        rows[row_idx][lang] = translations[str(row_idx)].strip()
                        applied += 1

                # Flush to disk immediately after each chunk
                with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)

                print(f" ✅ OK ({applied} strings in {elapsed:.1f}s, saved to {csv_path.name})")
                total_translated += applied
                chunks_done += 1

                # Optionally synchronize into django.po and compile .mo
                if sync_po and lang in LANGUAGES:
                    sync_csv_to_po(lang, rows)

            except Exception as e:
                print(f" ❌ Failed: {e}")
                print("      Saving progress and continuing...")

    return total_translated


def sync_csv_to_po(lang: str, rows: list[dict]):
    """Synchronize rows for a language into its django.po and recompile django.mo."""
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
    except Exception as e:
        print(f"      ⚠️  Warning: could not sync to .po for {lang}: {e}")


def process_po_file(
    po_path: Path,
    lang_code: str,
    chunk_size: int = 20,
    model: str | None = None,
    effort: str | None = None,
    timeout: int = 180,
    dry_run: bool = False,
    max_chunks: int | None = None,
) -> int:
    """Process a django.po file directly, translating missing entries chunk by chunk."""
    display_label = LANGUAGE_NAMES.get(lang_code, lang_code)
    lang_name = get_clean_language_name(lang_code)
    print(f"\n📂 Processing PO: {po_path.relative_to(PROJECT_ROOT) if PROJECT_ROOT in po_path.parents else po_path}")

    catalog = parse_po_file(po_path)
    if not catalog:
        print(f"  ❌ Skipping {po_path.name}: empty or missing catalog.")
        return 0

    pending = []
    for idx, (msgid, msgstr) in enumerate(catalog.items()):
        if not msgid:
            continue
        if is_untranslated(msgstr, msgid, lang_code):
            pending.append({"id": str(idx), "msgid": msgid, "source": msgid, "context": ""})

    if not pending:
        print(f"  ✅ [{display_label}] 100% complete! No missing strings.")
        return 0

    total_chunks = (len(pending) + chunk_size - 1) // chunk_size
    print(f"  🌐 [{display_label}] {len(pending)} strings pending translation ({total_chunks} chunks)...")

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

        prompt_items = [{"id": item["id"], "source": item["source"], "context": ""} for item in chunk]
        prompt = build_translation_prompt(prompt_items, lang_code, lang_name)

        t0 = time.time()
        try:
            translations = call_agy(prompt, model=model, effort=effort, timeout=timeout)
            elapsed = time.time() - t0

            applied = 0
            for item in chunk:
                sid = item["id"]
                msgid = item["msgid"]
                if sid in translations and translations[sid]:
                    catalog[msgid] = translations[sid].strip()
                    applied += 1

            # Flush to disk and compile .mo immediately
            write_po_file(lang_code, catalog, po_path)

            print(f" ✅ OK ({applied} strings in {elapsed:.1f}s, saved and compiled .mo)")
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
        # Match per-language translations_*.csv in current dir first
        per_lang = [p for p in target_dir.glob("translations_*.csv") if p.name != "translations_master.csv"]
        csv_files.extend(sorted(per_lang))

        # Add translations_master.csv last (if present) so it benefits from per-language updates
        master_path = target_dir / "translations_master.csv"
        if master_path.exists():
            csv_files.append(master_path)

        # Match other .csv files if no translations_*.csv
        if not csv_files:
            csv_files.extend(sorted(target_dir.glob("*.csv")))

    if file_type in ("po", "all") or (file_type == "auto" and not csv_files):
        # Match LC_MESSAGES/django.po across subdirectories
        po_files.extend(target_dir.glob("*/LC_MESSAGES/django.po"))
        # Direct .po files
        po_files.extend(target_dir.glob("*.po"))

    return sorted(list(set(csv_files))), sorted(list(set(po_files)))


def main():
    parser = argparse.ArgumentParser(
        description="Systematic Localization Automation using agy --dangerously-skip-permissions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  # Process all translations_*.csv in current directory:
  python3 scripts/translate_chunks_agy.py

  # Translate only Spanish with chunks of 25:
  python3 scripts/translate_chunks_agy.py --lang es --chunk-size 25

  # Translate with a specific fast model:
  python3 scripts/translate_chunks_agy.py --lang de --model gemini-3.8-flash-high

  # Translate django.po files directly:
  python3 scripts/translate_chunks_agy.py --type po --lang pt ru

  # Test single chunk dry-run:
  python3 scripts/translate_chunks_agy.py --dry-run --max-chunks 1
""",
    )

    parser.add_argument(
        "--dir",
        default=".",
        help="Directory to scan for translation files (defaults to current working directory).",
    )
    parser.add_argument(
        "--files",
        nargs="+",
        help="Explicit file(s) to process instead of scanning the directory.",
    )
    parser.add_argument(
        "--type",
        choices=["auto", "csv", "po", "all"],
        default="auto",
        help="Type of files to process (auto: CSV if present, else PO; csv; po; all).",
    )
    parser.add_argument(
        "--lang",
        nargs="+",
        help="Filter to specific target language code(s) (e.g. es pt fr ar).",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=20,
        help="Number of strings to translate per agy call (default: 20).",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model to pass to agy (e.g. gemini-3.8-flash-high). Defaults to CLI default.",
    )
    parser.add_argument(
        "--effort",
        choices=["low", "medium", "high", "xhigh", "max"],
        default=None,
        help="Reasoning effort level for agy session.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="Timeout in seconds for each agy call (default: 180s).",
    )
    parser.add_argument(
        "--max-chunks",
        type=int,
        default=None,
        help="Maximum chunks to process per language/file (useful for testing).",
    )
    parser.add_argument(
        "--no-sync-po",
        action="store_true",
        help="Do not automatically update .po and compile .mo when editing CSV files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be translated without executing agy calls.",
    )

    args = parser.parse_args()

    target_dir = Path(args.dir).resolve()
    print("==================================================================")
    print("  🌍 Antigravity (agy) Systematic Translation Automation")
    print("==================================================================")
    print(f"Target Directory: {target_dir}")
    print(f"Chunk Size:       {args.chunk_size}")
    if args.model:
        print(f"Model:            {args.model}")
    if args.effort:
        print(f"Effort:           {args.effort}")
    if args.lang:
        print(f"Languages:        {', '.join(args.lang)}")
    if args.dry_run:
        print("Mode:             DRY-RUN (no actual API calls will be made)")
    print("------------------------------------------------------------------")

    csv_files, po_files = discover_files(target_dir, file_type=args.type, explicit_files=args.files)

    if not csv_files and not po_files:
        print(f"❌ No translation files (.csv or .po) found in {target_dir}.")
        print("Tip: If you are in the project root, specify --dir locale")
        sys.exit(1)

    print(f"Found {len(csv_files)} CSV file(s) and {len(po_files)} PO file(s) to process.")

    t_start = time.time()
    grand_total = 0

    # Process CSV files
    for cp in csv_files:
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
        )

    # Process PO files
    for pp in po_files:
        # Infer language from parent directory name if in LC_MESSAGES
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
        )

    elapsed_total = time.time() - t_start

    # If any strings were translated and sync_po was enabled, refresh translations_master.csv
    if grand_total > 0 and not args.no_sync_po:
        try:
            from scripts.translations_tool import cmd_export_csv

            class ExportArgs:
                lang = "all"
                output = str(target_dir / "translations_master.csv")
                untranslated_only = False

            print("\n🔄 Refreshing translations_master.csv with latest translations...")
            cmd_export_csv(ExportArgs())
        except Exception as e:
            print(f"⚠️  Note: Could not refresh master CSV: {e}")

    print("\n==================================================================")
    print(f"🎉 All batches completed in {elapsed_total:.1f}s!")
    print(f"Total Strings Translated & Saved: {grand_total}")
    print("==================================================================")


if __name__ == "__main__":
    main()
