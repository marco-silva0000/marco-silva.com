#!/usr/bin/env python3
"""Centralized Translation Tool for Marco Silva's Web Platform.

Features:
1. `export-csv`: Exports all translatable strings to CSV (master or per-language)
   ready to upload directly to Google Sheets or Excel for native speakers.
2. `import-csv`: Imports translated CSV back from Google Sheets / native speakers,
   updates django.po files, and recompiles .mo binaries.
3. `status`: Displays current translation progress and completion percentage across all 9 languages.
4. `extract`: Scans all templates and Python files to discover new translatable strings.
5. `compile`: Compiles .po files to binary .mo catalogs using pure-Python compiler (+ msgfmt if available).

Supported Languages:
- en: English
- pt: Português
- it: Italiano
- es: Español
- fr: Français
- el: Ελληνικά
- ru: Русский
- hi: हिन्दी
- kn: ಕನ್ನಡ
"""

import argparse
import csv
import glob
import os
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LOCALE_DIR = BASE_DIR / "locale"

LANGUAGES = ["en", "pt", "it", "es", "fr", "el", "ru", "hi", "kn"]
LANGUAGE_NAMES = {
    "en": "English",
    "pt": "Português",
    "it": "Italiano",
    "es": "Español",
    "fr": "Français",
    "el": "Ελληνικά",
    "ru": "Русский",
    "hi": "हिन्दी",
    "kn": "ಕನ್ನಡ",
}


def escape_po(s: str) -> str:
    """Escape string for inclusion in .po file."""
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def unescape_po(s: str) -> str:
    """Unescape string from .po file."""
    res = []
    i = 0
    n = len(s)
    while i < n:
        if s[i] == "\\" and i + 1 < n:
            nxt = s[i + 1]
            if nxt == "n":
                res.append("\n")
                i += 2
            elif nxt == '"':
                res.append('"')
                i += 2
            elif nxt == "\\":
                res.append("\\")
                i += 2
            elif nxt == "t":
                res.append("\t")
                i += 2
            else:
                res.append(nxt)
                i += 2
        else:
            res.append(s[i])
            i += 1
    return "".join(res)


def compile_dict_to_mo(entries: dict[str, str], mo_path: Path):
    """Pure-Python compiler producing binary .mo files conforming to GNU gettext specs."""
    keys = sorted(entries.keys())
    num_strings = len(keys)
    orig_table_offset = 28
    trans_table_offset = orig_table_offset + num_strings * 8
    strings_start = trans_table_offset + num_strings * 8

    orig_indices = []
    trans_indices = []
    orig_data = bytearray()
    trans_data = bytearray()

    cur_offset = strings_start
    for k in keys:
        k_bytes = k.encode("utf-8") + b"\x00"
        orig_indices.append((len(k_bytes) - 1, cur_offset))
        orig_data.extend(k_bytes)
        cur_offset += len(k_bytes)

    for k in keys:
        v_bytes = entries[k].encode("utf-8") + b"\x00"
        trans_indices.append((len(v_bytes) - 1, cur_offset))
        trans_data.extend(v_bytes)
        cur_offset += len(v_bytes)

    mo_path.parent.mkdir(parents=True, exist_ok=True)
    with open(mo_path, "wb") as f:
        f.write(struct.pack("<7I", 0x950412DE, 0, num_strings, orig_table_offset, trans_table_offset, 0, 0))
        for length, offset in orig_indices:
            f.write(struct.pack("<2I", length, offset))
        for length, offset in trans_indices:
            f.write(struct.pack("<2I", length, offset))
        f.write(orig_data)
        f.write(trans_data)


def parse_po_file(po_path: Path) -> dict[str, str]:
    """Parse a .po file into a dictionary of {msgid: msgstr}."""
    if not po_path.exists():
        return {}

    content = po_path.read_text(encoding="utf-8")
    entries = {}
    current_msgid = None
    current_msgstr = None
    state = None

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith('msgid "'):
            if current_msgid is not None and current_msgstr is not None:
                entries[unescape_po(current_msgid)] = unescape_po(current_msgstr)
            current_msgid = line[7:-1]
            current_msgstr = ""
            state = "msgid"
        elif line.startswith('msgstr "'):
            current_msgstr = line[8:-1]
            state = "msgstr"
        elif line.startswith('"') and line.endswith('"'):
            val = line[1:-1]
            if state == "msgid":
                current_msgid += val
            elif state == "msgstr":
                current_msgstr += val

    if current_msgid is not None and current_msgstr is not None:
        entries[unescape_po(current_msgid)] = unescape_po(current_msgstr)

    return entries


def write_po_file(lang: str, entries: dict[str, str], po_path: Path):
    """Write entries to a .po file and compile to .mo."""
    po_path.parent.mkdir(parents=True, exist_ok=True)
    mo_path = po_path.parent / "django.mo"

    header = [
        'msgid ""',
        'msgstr ""',
        '"Content-Type: text/plain; charset=UTF-8\\n"',
        '"Content-Transfer-Encoding: 8bit\\n"',
        f'"Language: {lang}\\n"',
        '"MIME-Version: 1.0\\n"',
        "",
    ]

    mo_dict = {
        "": f"Content-Type: text/plain; charset=UTF-8\nContent-Transfer-Encoding: 8bit\nLanguage: {lang}\nMIME-Version: 1.0\n"
    }

    lines = list(header)
    for msgid in sorted(entries.keys()):
        if not msgid:
            continue
        msgstr = entries[msgid]
        lines.append(f'msgid "{escape_po(msgid)}"')
        lines.append(f'msgstr "{escape_po(msgstr)}"')
        lines.append("")
        if msgstr:
            mo_dict[msgid] = msgstr
        else:
            # Fall back to English msgid for compilation
            mo_dict[msgid] = msgid

    po_path.write_text("\n".join(lines), encoding="utf-8")
    compile_dict_to_mo(mo_dict, mo_path)

    # If GNU msgfmt is available, verify / re-compile
    msgfmt_bin = shutil.which("msgfmt")
    if not msgfmt_bin:
        for candidate in [
            "/nix/store/sz6wx51pnm4dpcliyysd27i0jqywm15x-gettext-0.22.5/bin/msgfmt",
            "/nix/store/sal5l525psrrii8w1c9dhznb8sdajl30-gettext-1.0/bin/msgfmt",
        ]:
            if os.path.exists(candidate):
                msgfmt_bin = candidate
                break
    if msgfmt_bin:
        try:
            subprocess.run(
                [msgfmt_bin, "-o", str(mo_path), str(po_path)],
                check=True,
                capture_output=True,
            )
        except Exception:
            pass


def extract_translatable_strings() -> dict[str, list[str]]:
    """Scan all HTML templates and Python files to discover translatable strings."""
    found = {}

    # HTML templates
    template_paths = sorted(glob.glob(str(BASE_DIR / "templates/**/*.html"), recursive=True))
    for tp in template_paths:
        rel = os.path.relpath(tp, BASE_DIR)
        content = Path(tp).read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r'{%\s*trans\s+["\']([^"\']+)["\']\s*%}', content):
            s = m.group(1).strip()
            if s:
                found.setdefault(s, set()).add(rel)

    # Python files
    py_paths = sorted(glob.glob(str(BASE_DIR / "**/*.py"), recursive=True))
    for pp in py_paths:
        if "venv" in pp or ".venv" in pp or "migrations" in pp or "generate_locales" in pp or "translations_tool" in pp:
            continue
        rel = os.path.relpath(pp, BASE_DIR)
        content = Path(pp).read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r'(?<![a-zA-Z0-9_])_\(\s*["\']([^"\']+)["\']\s*\)', content):
            s = m.group(1).strip()
            if s:
                found.setdefault(s, set()).add(rel)

    # Also include any existing keys from generate_locales if available
    try:
        sys.path.insert(0, str(BASE_DIR))
        from scripts.generate_locales import TRANSLATIONS
        for s in TRANSLATIONS.keys():
            if s:
                found.setdefault(s, set()).add("scripts/generate_locales.py")
    except Exception:
        pass

    return {k: sorted(list(v)) for k, v in found.items()}


def load_all_catalogs() -> dict[str, dict[str, str]]:
    """Load PO entries for each language."""
    catalogs = {}
    for lang in LANGUAGES:
        po_path = LOCALE_DIR / lang / "LC_MESSAGES" / "django.po"
        catalogs[lang] = parse_po_file(po_path)
    return catalogs


def cmd_extract(args):
    """Extract all translatable strings and synchronize into all .po files."""
    strings = extract_translatable_strings()
    print(f"Extracted {len(strings)} unique translatable strings across the project.")

    catalogs = load_all_catalogs()

    # Import initial TRANSLATIONS if available
    seed_translations = {}
    try:
        sys.path.insert(0, str(BASE_DIR))
        from scripts.generate_locales import TRANSLATIONS
        seed_translations = TRANSLATIONS
    except Exception:
        pass

    total_added = 0
    for msgid, locations in strings.items():
        for lang in LANGUAGES:
            if msgid not in catalogs[lang] or not catalogs[lang][msgid]:
                if lang == "en":
                    catalogs[lang][msgid] = msgid
                elif msgid in seed_translations and lang in seed_translations[msgid]:
                    catalogs[lang][msgid] = seed_translations[msgid][lang]
                else:
                    # Keep empty for untranslated so status checkers and Poedit see it
                    catalogs[lang][msgid] = ""
                total_added += 1

    # Write PO files
    for lang in LANGUAGES:
        po_path = LOCALE_DIR / lang / "LC_MESSAGES" / "django.po"
        write_po_file(lang, catalogs[lang], po_path)

    print(f"Updated .po catalogs for all 9 languages in {LOCALE_DIR}/")


def cmd_export_csv(args):
    """Export translations to CSV format for Google Sheets or native speakers."""
    # Ensure strings are extracted
    extracted = extract_translatable_strings()
    catalogs = load_all_catalogs()

    # Sync any newly discovered strings into catalogs
    for msgid in extracted:
        for lang in LANGUAGES:
            if msgid not in catalogs[lang]:
                catalogs[lang][msgid] = msgid if lang == "en" else ""

    target_lang = args.lang
    untranslated_only = args.untranslated_only

    if target_lang and target_lang != "all":
        if target_lang not in LANGUAGES:
            print(f"Error: Unknown language '{target_lang}'. Must be one of {LANGUAGES}")
            sys.exit(1)

        out_path = Path(args.output or (LOCALE_DIR / f"translations_{target_lang}.csv"))
        out_path.parent.mkdir(parents=True, exist_ok=True)

        rows = []
        for msgid in sorted(extracted.keys()):
            context = ", ".join(extracted[msgid])
            en_val = catalogs["en"].get(msgid, msgid)
            target_val = catalogs[target_lang].get(msgid, "")

            is_translated = bool(target_val) and target_val != en_val
            if untranslated_only and is_translated:
                continue

            rows.append({
                "msgid": msgid,
                "context": context,
                "en": en_val,
                target_lang: target_val,
            })

        with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["msgid", "context", "en", target_lang])
            writer.writeheader()
            writer.writerows(rows)

        print(f"Exported {len(rows)} strings to {out_path} for '{LANGUAGE_NAMES[target_lang]}' ({target_lang}).")
        print("Tip: You can upload this CSV directly to Google Sheets and share the edit link with a native speaker!")

    else:
        # Master CSV with all languages
        out_path = Path(args.output or (LOCALE_DIR / "translations_master.csv"))
        out_path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = ["msgid", "context", "en"] + [l for l in LANGUAGES if l != "en"]
        rows = []

        for msgid in sorted(extracted.keys()):
            context = ", ".join(extracted[msgid])
            en_val = catalogs["en"].get(msgid, msgid)

            if untranslated_only:
                # check if any language is untranslated
                has_untranslated = any(
                    not catalogs[l].get(msgid) or catalogs[l].get(msgid) == en_val
                    for l in LANGUAGES if l != "en"
                )
                if not has_untranslated:
                    continue

            row = {
                "msgid": msgid,
                "context": context,
                "en": en_val,
            }
            for l in LANGUAGES:
                if l != "en":
                    row[l] = catalogs[l].get(msgid, "")
            rows.append(row)

        with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        print(f"Exported {len(rows)} master translation rows to {out_path}.")
        print("Tip: Upload to Google Sheets to collaborate on all languages in one centralized spreadsheet!")


def cmd_import_csv(args):
    """Import translations from a CSV file (e.g. downloaded from Google Sheets)."""
    csv_path = Path(args.file)
    if not csv_path.exists():
        print(f"Error: File not found: {csv_path}")
        sys.exit(1)

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []

        if "msgid" not in fieldnames:
            print(f"Error: CSV file must contain a 'msgid' column. Found columns: {fieldnames}")
            sys.exit(1)

        import_langs = [col for col in fieldnames if col in LANGUAGES and col != "en"]
        if not import_langs:
            print(f"Error: No supported language column found in CSV. Expected one or more of {LANGUAGES}")
            sys.exit(1)

        catalogs = load_all_catalogs()
        updated_counts = {l: 0 for l in import_langs}

        for row in reader:
            msgid = row.get("msgid", "").strip()
            if not msgid:
                continue

            for lang in import_langs:
                val = row.get(lang, "").strip()
                if val:
                    old_val = catalogs[lang].get(msgid, "")
                    if val != old_val:
                        catalogs[lang][msgid] = val
                        updated_counts[lang] += 1

    # Write updated catalogs and recompile .mo
    for lang in import_langs:
        po_path = LOCALE_DIR / lang / "LC_MESSAGES" / "django.po"
        write_po_file(lang, catalogs[lang], po_path)

    print(f"Import complete from {csv_path}!")
    for lang, count in updated_counts.items():
        print(f"  - {LANGUAGE_NAMES[lang]} ({lang}): {count} strings updated/added.")
    print("All .po catalogs updated and .mo files compiled successfully.")


def cmd_status(args):
    """Print the translation status and coverage percentage across all languages."""
    extracted = extract_translatable_strings()
    total_strings = len(extracted)
    catalogs = load_all_catalogs()

    print(f"\n========================================================")
    print(f"  Marco Silva Homelab — Translation Status Report")
    print(f"========================================================")
    print(f"Total Unique Strings Discovered: {total_strings}\n")
    print(f"{'Code':<6} {'Language':<14} {'Translated':<12} {'Missing':<10} {'Coverage':<8}")
    print(f"{'-'*6} {'-'*14} {'-'*12} {'-'*10} {'-'*8}")

    for lang in LANGUAGES:
        if lang == "en":
            print(f"{lang:<6} {LANGUAGE_NAMES[lang]:<14} {total_strings:<12} {0:<10} {'100.0%':<8}")
            continue

        cat = catalogs.get(lang, {})
        translated_count = 0
        for s in extracted.keys():
            val = cat.get(s, "").strip()
            # If non-empty and not just identical to english key (unless short symbol or brand)
            if val and (val != s or len(s) <= 3 or s.startswith("🐺") or s.startswith("✏️")):
                translated_count += 1

        missing_count = total_strings - translated_count
        coverage = (translated_count / total_strings * 100.0) if total_strings else 0.0
        print(f"{lang:<6} {LANGUAGE_NAMES[lang]:<14} {translated_count:<12} {missing_count:<10} {coverage:>5.1f}%")

    print(f"========================================================\n")


def cmd_compile(args):
    """Recompile all .po files into .mo binary catalogs."""
    catalogs = load_all_catalogs()
    for lang in LANGUAGES:
        po_path = LOCALE_DIR / lang / "LC_MESSAGES" / "django.po"
        write_po_file(lang, catalogs[lang], po_path)
    print(f"Recompiled binary .mo catalogs for all {len(LANGUAGES)} languages in {LOCALE_DIR}/.")


def main():
    parser = argparse.ArgumentParser(description="Translation Tool for Marco Silva's Website")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # extract
    subparsers.add_parser("extract", help="Scan codebase for all translatable strings and update catalogs")

    # export-csv
    p_export = subparsers.add_parser("export-csv", help="Export translations to CSV for Google Sheets / translators")
    p_export.add_argument("--lang", default="all", help="Target language (e.g. 'es', 'pt') or 'all' for master CSV")
    p_export.add_argument("--output", help="Custom output CSV file path")
    p_export.add_argument("--untranslated-only", action="store_true", help="Only export strings that need translation")

    # import-csv
    p_import = subparsers.add_parser("import-csv", help="Import translations from a completed CSV file")
    p_import.add_argument("--file", required=True, help="Path to CSV file to import")

    # status
    subparsers.add_parser("status", help="Show translation progress and coverage across all languages")

    # compile
    subparsers.add_parser("compile", help="Recompile all .po files to binary .mo")

    args = parser.parse_args()

    if args.command == "extract":
        cmd_extract(args)
    elif args.command == "export-csv":
        cmd_export_csv(args)
    elif args.command == "import-csv":
        cmd_import_csv(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "compile":
        cmd_compile(args)


if __name__ == "__main__":
    main()
