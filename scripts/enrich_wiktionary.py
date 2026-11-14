#!/usr/bin/env python3
"""Enrich Emojinary and Pictionary wordlists with Wiktionary lexical data (CC BY-SA 4.0).

Uses the MediaWiki Action API multi-title batch endpoint (50 pages per HTTP call) to extract:
- Concise 1-line English definitions (for clue-giver tooltips)
- Part of speech & semantic topic hints
- Accepted English synonyms/aliases (e.g., couch <-> sofa)
- Short etymology notes for idioms & phrases
- Multilingual translations across all 64 supported site languages (including /translations subpages)

Usage:
    uv run python scripts/enrich_wiktionary.py [--max-words 2500]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

WORDLISTS_PATH = PROJECT_ROOT / "emojinary" / "data" / "wordlists.json"
OUT_PATH = PROJECT_ROOT / "emojinary" / "data" / "wiktionary_lexicon.json"

SUPPORTED_LANGS = {
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
}

WIKT_LANG_MAP = {
    "cmn": "zh-cn",
    "zh": "zh-cn",
    "yue": "zh-tw",
    "he": "iw",
    "nb": "no",
    "nn": "no",
    "sh": "hr",
    "fil": "tl",
}

GRAMMAR_LABELS = {
    "transitive",
    "intransitive",
    "countable",
    "uncountable",
    "idiomatic",
    "slang",
    "colloquial",
    "informal",
    "formal",
    "archaic",
    "obsolete",
    "dated",
    "rare",
    "plural",
    "singular",
    "figurative",
    "figuratively",
    "literally",
    "usually",
    "often",
    "sometimes",
    "especially",
    "chiefly",
    "us",
    "uk",
    "britain",
    "north america",
    "australia",
    "canada",
    "ambitransitive",
    "ergative",
    "reflexive",
    "nonstandard",
    "humorous",
    "offensive",
    "vulgar",
    "derogatory",
    "euphemistic",
    "_",
}

EN_SECTION_RE = re.compile(r"(?:^|\n)==English==\s*\n(.*?)(?=\n==[^=]|\Z)", re.DOTALL)
HEADER_RE = re.compile(r"^(=+)([^=\n]+)\1\s*$")
TRANSL_RE = re.compile(r"\{\{tt?\+?\|([a-zA-Z\-]+)\|([^}|]+)")
SYN_TMPL_RE = re.compile(r"\{\{(?:syn|synonyms)\|en\|([^}]+)\}\}", re.IGNORECASE)
SYNOF_TMPL_RE = re.compile(r"\{\{(?:synonym of|syn of|alt form)\|en\|([^}|]+)", re.IGNORECASE)
TOPIC_TMPL_RE = re.compile(r"\{\{(?:topics|C|top)\|en\|([^}]+)\}\}", re.IGNORECASE)
LB_TMPL_RE = re.compile(r"\{\{lb\|en\|([^}]+)\}\}", re.IGNORECASE)


def fetch_batch(titles: list[str]) -> dict[str, str]:
    """Fetch up to 50 Wiktionary pages in one MediaWiki Action API request via curl."""
    joined = "|".join(titles)
    try:
        out = subprocess.check_output(
            [
                "curl",
                "-sG",
                "--max-time",
                "30",
                "https://en.wiktionary.org/w/api.php",
                "--data-urlencode",
                "action=query",
                "--data-urlencode",
                "prop=revisions",
                "--data-urlencode",
                "rvprop=content",
                "--data-urlencode",
                "rvslots=main",
                "--data-urlencode",
                "redirects=1",
                "--data-urlencode",
                "format=json",
                "--data-urlencode",
                f"titles={joined}",
                "-H",
                "User-Agent: MarcoSilvaWordlistBuilder/1.0 (https://marco-silva.com)",
            ],
            text=True,
        )
        data = json.loads(out)
    except Exception as exc:
        print(f"  ⚠️ Batch error: {exc}", file=sys.stderr)
        return {}

    query = data.get("query", {})
    norm_map = {item["from"]: item["to"] for item in query.get("normalized", []) if "from" in item and "to" in item}
    redir_map = {item["from"]: item["to"] for item in query.get("redirects", []) if "from" in item and "to" in item}

    by_final_title: dict[str, str] = {}
    for page in query.get("pages", {}).values():
        if "missing" in page:
            continue
        title = page.get("title", "")
        revs = page.get("revisions", [])
        if revs:
            content = revs[0].get("slots", {}).get("main", {}).get("*", "")
            if content:
                by_final_title[title] = content

    results: dict[str, str] = {}
    for orig in titles:
        t1 = norm_map.get(orig, orig)
        t2 = redir_map.get(t1, t1)
        if t2 in by_final_title:
            results[orig] = by_final_title[t2]
        elif orig in by_final_title:
            results[orig] = by_final_title[orig]
    return results


def strip_wikitext(raw: str) -> str:
    """Convert MediaWiki/Wiktionary markup into clean plain English text."""
    s = raw.strip()
    # Replace [[target|label]] -> label, [[word]] -> word
    s = re.sub(r"\[\[[^|\]]*\|([^\]]+)\]\]", r"\1", s)
    s = re.sub(r"\[\[([^\]#]+)(?:#[^\]]*)?\]\]", r"\1", s)

    # Extract readable gloss/mention text from common inline templates
    def _tmpl_repl(match: re.Match) -> str:
        inner = match.group(1)
        parts = [p.strip() for p in inner.split("|")]
        name = parts[0].lower() if parts else ""
        if name in ("l", "m", "m+", "link", "mention") and len(parts) >= 3:
            for candidate in parts[2:]:
                if "=" not in candidate and candidate:
                    return candidate
        if name in ("gloss", "non-gloss", "n-g", "ng") and len(parts) >= 2:
            return parts[1]
        if name in ("lb", "senseid", "defdate", "rfdef", "qual", "q", "i"):
            return ""
        if name in ("synonym of", "syn of") and len(parts) >= 3:
            return f"synonym of {parts[2]}"
        if name == "w" and len(parts) >= 2:
            return parts[-1] if "=" not in parts[-1] else parts[1]
        if name == "taxfmt" and len(parts) >= 2:
            return parts[1]
        if name == "place" and len(parts) >= 3:
            place_chunks: list[str] = []
            for p in parts[2:]:
                if "=" in p:
                    continue
                cleaned_p = re.sub(r"<<(?:[a-zA-Z_]+/)?([^>]+)>>", r"\1", p)
                cleaned_p = re.sub(r"^[a-zA-Z_]+/", "", cleaned_p).strip()
                if cleaned_p == "caplc":
                    cleaned_p = "capital and largest city"
                elif cleaned_p == "capc":
                    cleaned_p = "capital city"
                elif "/" in cleaned_p and not cleaned_p.startswith("http"):
                    cleaned_p = " / ".join(seg.strip() for seg in cleaned_p.split("/") if seg.strip())
                if cleaned_p:
                    place_chunks.append(cleaned_p)
            if place_chunks:
                if place_chunks[0].startswith("capital") and len(place_chunks) >= 2:
                    return f"{place_chunks[0]} of {', '.join(place_chunks[1:])}"
                if len(place_chunks) >= 2 and not place_chunks[0].startswith(("A ", "a ", "The ", "the ")):
                    return f"{place_chunks[0]} in {', '.join(place_chunks[1:])}"
                return ", ".join(place_chunks)
        return ""

    # Apply nested template cleanup up to 2 passes
    for _ in range(2):
        s = re.sub(r"\{\{([^{}]+)\}\}", _tmpl_repl, s)

    s = re.sub(r"''+", "", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"\(\s*,?\s*\)", "", s)
    s = re.sub(r"\s+([,.;:!?])", r"\1", s)
    s = re.sub(r"\s+", " ", s).strip(" .,:;")
    if s and s[-1] not in ".!?":
        s += "."
    return s


def _strip_stress_marks(text: str) -> str:
    """Remove editorial acute/grave stress accents (e.g. Russian я́блоко -> яблоко)."""
    if "\u0301" not in text and "\u0300" not in text:
        return text
    nfd = unicodedata.normalize("NFD", text)
    cleaned = "".join(ch for ch in nfd if ch not in ("\u0301", "\u0300"))
    return unicodedata.normalize("NFC", cleaned)


def extract_translations(text: str) -> dict[str, list[str]]:
    """Parse Wiktionary {{t|lang|term}} templates into a compact {lang: [terms]} map."""
    out: dict[str, list[str]] = {}
    for code_raw, term_raw in TRANSL_RE.findall(text):
        code = WIKT_LANG_MAP.get(code_raw.lower(), code_raw.lower())
        if code not in SUPPORTED_LANGS:
            continue
        term = re.sub(r"\[\[[^|\]]*\|([^\]]+)\]\]", r"\1", term_raw)
        term = re.sub(r"\[\[([^\]#]+)(?:#[^\]]*)?\]\]", r"\1", term)
        term = _strip_stress_marks(term).strip("[]() ").strip()
        if not term or "=" in term or len(term) > 60:
            continue
        bucket = out.setdefault(code, [])
        if term not in bucket and len(bucket) < 3:
            bucket.append(term)
    return out


def parse_english_page(title: str, wikitext: str) -> tuple[dict | None, bool]:
    """Extract structured definition, pos, aliases, topics, etymology, and translations."""
    m = EN_SECTION_RE.search(wikitext)
    if not m:
        return None, False
    en_sec = m.group(1)

    has_subpage = "translation subpage" in en_sec.lower() or "{{trans-see" in en_sec.lower()

    pos = "noun"
    best_def = ""
    fallback_def = ""
    etymology = ""
    aliases: list[str] = []
    topics: list[str] = []

    in_etymology = False
    pos_detected = False

    lines = en_sec.splitlines()
    for line in lines:
        s = line.strip()
        hm = HEADER_RE.match(s)
        if hm:
            hdr = hm.group(2).strip().lower()
            if hdr.startswith("etymology"):
                in_etymology = True
                continue
            in_etymology = False
            if not pos_detected:
                if "proper noun" in hdr:
                    pos = "proper"
                    pos_detected = True
                elif hdr in ("proverb", "phrase", "idiom"):
                    pos = "phrase"
                    pos_detected = True
                elif hdr == "verb":
                    pos = "verb"
                    pos_detected = True
                elif hdr == "adjective":
                    pos = "adjective"
                    pos_detected = True
                elif hdr == "noun":
                    pos = "noun"
                    pos_detected = True
            continue

        if in_etymology and not etymology and s and not s.startswith("{{") and not s.startswith("[[File"):
            cleaned_ety = strip_wikitext(s)
            if len(cleaned_ety) >= 15 and "borrowed from" not in cleaned_ety.lower()[:16]:
                etymology = cleaned_ety[:220]
            elif len(cleaned_ety) >= 15 and " " in title:
                etymology = cleaned_ety[:220]

        if s.startswith("# ") and not s.startswith("#*") and not s.startswith("#:") and not s.startswith("##"):
            raw_def = s[2:].strip()
            # Grab topic-like labels on first definition
            for lb_match in LB_TMPL_RE.findall(raw_def):
                for tag in lb_match.split("|"):
                    t = tag.strip().lower()
                    if t and t not in GRAMMAR_LABELS and len(t) > 2 and t not in topics and len(topics) < 4:
                        topics.append(t)

            # Check syn of
            for sm in SYNOF_TMPL_RE.findall(raw_def):
                cand = sm.strip()
                if cand and cand.lower() != title.lower() and len(cand) <= 35 and cand not in aliases:
                    aliases.append(cand)

            cleaned = strip_wikitext(raw_def)
            if cleaned and len(cleaned) >= 8:
                is_obsolete = "obsolete" in raw_def.lower()[:60] or "archaic" in raw_def.lower()[:60]
                if not is_obsolete and not best_def:
                    best_def = cleaned[:220]
                elif not fallback_def:
                    fallback_def = cleaned[:220]

        # Synonyms templates
        for syn_raw in SYN_TMPL_RE.findall(s):
            for part in syn_raw.split("|"):
                part = part.strip()
                if not part or "=" in part or part.startswith("Thesaurus:"):
                    continue
                cand = re.sub(r"\[\[[^|\]]*\|([^\]]+)\]\]", r"\1", part).strip("[] ")
                if cand and cand.lower() != title.lower() and 2 <= len(cand) <= 35 and cand not in aliases:
                    aliases.append(cand)

        # Topics templates
        for top_raw in TOPIC_TMPL_RE.findall(s):
            for part in top_raw.split("|"):
                t = part.strip().lower()
                if t and "=" not in t and t not in GRAMMAR_LABELS and t not in topics and len(topics) < 5:
                    topics.append(t)

    definition = best_def or fallback_def
    translations = extract_translations(en_sec)

    if not definition and not aliases and not translations:
        return None, has_subpage

    return {
        "pos": pos,
        "definition": definition,
        "etymology": etymology if (pos == "phrase" or " " in title) else "",
        "aliases": aliases[:8],
        "topics": topics[:4],
        "translations": translations,
    }, has_subpage


def collect_candidate_words(max_words: int) -> list[str]:
    """Select priority vocabulary words from wordlists.json for Wiktionary lookup."""
    if not WORDLISTS_PATH.exists():
        return []
    with open(WORDLISTS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Core common / game priority terms first
    priority_order: list[str] = []
    seen: set[str] = set()

    def _add(w: str) -> None:
        clean = w.strip()
        low = clean.lower()
        if not clean or low in seen or len(clean) > 45:
            return
        seen.add(low)
        priority_order.append(clean)

    # 0. Built-in curated words from seed_emojinary.WORDS first
    try:
        from emojinary.management.commands.seed_emojinary import WORDS as CURATED_WORDS

        for text, _, _ in CURATED_WORDS:
            _add(text)
    except Exception:
        pass

    # 0b. Codenames 400-word deck & Impostor pairs
    for w in data.get("codenames", []):
        _add(str(w))
    try:
        from impostor.word_pairs import CURATED_IMPOSTOR_PAIRS

        for citizen, poison, lethal, _ in CURATED_IMPOSTOR_PAIRS:
            _add(citizen)
            _add(poison)
            _add(lethal)
    except Exception:
        pass

    # 1. All phrases/idioms (high value for tooltip & etymology) + animals + foods + actions
    priority_cats = ("phrase", "animal", "food", "action", "thing", "place")
    for diff_target in (1, 2, 3):
        for item in data.get("emojinary", []):
            text, cat, diff = item[0], item[1], item[2]
            if cat in priority_cats and diff == diff_target:
                _add(text)

    # 2. Pictionary verbs, adjectives, sentences, nouns
    pic = data.get("pictionary", {})
    for diff in ("easy", "medium", "hard"):
        for pos in ("verb", "adjective", "noun"):
            for w in pic.get(pos, {}).get(diff, []):
                _add(w)
    for sent in pic.get("sentence", []):
        _add(sent)

    return priority_order[:max_words]


def _fetch_subpages(subpage_needed: list[tuple[str, str]], lexicon: dict[str, dict], workers: int) -> None:
    if not subpage_needed:
        return
    print(f"Fetching {len(subpage_needed)} Wiktionary /translations subpages...")
    sub_titles = [sp for _, sp in subpage_needed]
    sub_to_key = {sp: key for key, sp in subpage_needed}
    sub_batches = [sub_titles[i : i + 50] for i in range(0, len(sub_titles), 50)]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch_batch, b): b for b in sub_batches}
        for fut in as_completed(futures):
            pages = fut.result()
            for sp_title, wikitext in pages.items():
                key = sub_to_key.get(sp_title)
                if not key or key not in lexicon:
                    continue
                extra_tr = extract_translations(wikitext)
                existing_tr = lexicon[key].setdefault("translations", {})
                for lang, terms in extra_tr.items():
                    bucket = existing_tr.setdefault(lang, [])
                    for t in terms:
                        if t not in bucket and len(bucket) < 3:
                            bucket.append(t)


def _merge_wikisaurus_related(lexicon: dict[str, dict]) -> int:
    """Attach filtered Wikisaurus semantic neighbors from wordlists.json to lexicon entries."""
    if not WORDLISTS_PATH.exists():
        return 0
    with open(WORDLISTS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    wikisaurus: dict[str, list[str]] = data.get("codenames_wikisaurus", {})
    updated = 0
    for key, neighbors in wikisaurus.items():
        clean_neighbors = [str(n).strip() for n in neighbors if str(n).strip()]
        if not clean_neighbors:
            continue
        entry = lexicon.setdefault(
            key.lower(),
            {
                "pos": "noun",
                "definition": "",
                "etymology": "",
                "aliases": [],
                "topics": [],
                "translations": {},
            },
        )
        existing_rel = list(entry.get("related", []))
        for nb in clean_neighbors:
            if nb not in existing_rel:
                existing_rel.append(nb)
        if existing_rel != entry.get("related"):
            entry["related"] = existing_rel[:30]
            updated += 1
    return updated


def extend_codenames_and_impostor(workers: int) -> None:
    """Incrementally enrich Codenames (400 words) + Impostor pairs without dropping existing entries."""
    lexicon: dict[str, dict] = {}
    if OUT_PATH.exists():
        with open(OUT_PATH, "r", encoding="utf-8") as f:
            lexicon = json.load(f)

    with open(WORDLISTS_PATH, "r", encoding="utf-8") as f:
        wl_data = json.load(f)

    targets: list[str] = []
    seen_targets: set[str] = set()

    def _add_target(w: str) -> None:
        cw = str(w or "").strip()
        if not cw or cw.lower() in seen_targets:
            return
        seen_targets.add(cw.lower())
        targets.append(cw)

    for w in wl_data.get("codenames", []):
        _add_target(w)

    try:
        from impostor.word_pairs import CURATED_IMPOSTOR_PAIRS

        for citizen, poison, lethal, _ in CURATED_IMPOSTOR_PAIRS:
            _add_target(citizen)
            _add_target(poison)
            _add_target(lethal)
    except Exception:
        pass

    to_fetch: list[str] = []
    for w in targets:
        k = w.lower()
        existing = lexicon.get(k)
        if not existing or not existing.get("definition") or len(existing.get("translations", {})) < 5:
            to_fetch.append(w)

    print(f"Extending lexicon ({len(lexicon)} existing): fetching {len(to_fetch)} Codenames/Impostor words...")
    fetch_titles: list[str] = []
    seen_fetch: set[str] = set()
    for w in to_fetch:
        for cand in (w.lower(), w.title()):
            if cand not in seen_fetch:
                seen_fetch.add(cand)
                fetch_titles.append(cand)

    raw_pages: dict[str, str] = {}
    batches = [fetch_titles[i : i + 50] for i in range(0, len(fetch_titles), 50)]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for fut in as_completed([pool.submit(fetch_batch, b) for b in batches]):
            raw_pages.update(fut.result())

    subpage_needed: list[tuple[str, str]] = []
    for w in to_fetch:
        k = w.lower()
        low_wt = raw_pages.get(w.lower(), "")
        title_wt = raw_pages.get(w.title(), "")
        low_parsed, low_sub = parse_english_page(w.lower(), low_wt) if low_wt else (None, False)
        title_parsed, title_sub = parse_english_page(w.title(), title_wt) if title_wt else (None, False)

        chosen = low_parsed
        chosen_title = w.lower()
        chosen_sub = low_sub
        if title_parsed and (
            not low_parsed or len(title_parsed.get("translations", {})) > len(low_parsed.get("translations", {})) + 2
        ):
            chosen = title_parsed
            chosen_title = w.title()
            chosen_sub = title_sub
        elif low_parsed and title_parsed and title_parsed.get("definition") and not low_parsed.get("definition"):
            chosen["definition"] = title_parsed["definition"]

        if chosen:
            prev = lexicon.get(k, {})
            # Preserve any existing richer translations/related fields
            for lang, vals in (prev.get("translations") or {}).items():
                bucket = chosen["translations"].setdefault(lang, [])
                for v in vals:
                    if v not in bucket and len(bucket) < 3:
                        bucket.append(v)
            if prev.get("related"):
                chosen["related"] = prev["related"]
            if not chosen.get("definition") and prev.get("definition"):
                chosen["definition"] = prev["definition"]
            lexicon[k] = chosen
            if chosen_sub and len(chosen["translations"]) < 5:
                subpage_needed.append((k, f"{chosen_title}/translations"))
            elif title_sub and title_parsed and len(chosen["translations"]) < 5:
                subpage_needed.append((k, f"{w.title()}/translations"))

    _fetch_subpages(subpage_needed, lexicon, workers)
    rel_count = _merge_wikisaurus_related(lexicon)

    cleaned_lexicon = {
        k: v
        for k, v in sorted(lexicon.items())
        if v.get("definition") or v.get("translations") or v.get("aliases") or v.get("related")
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(cleaned_lexicon, f, ensure_ascii=False, separators=(",", ":"))

    cn_covered = sum(1 for w in wl_data.get("codenames", []) if w.lower() in cleaned_lexicon)
    cn_trans = sum(1 for w in wl_data.get("codenames", []) if cleaned_lexicon.get(w.lower(), {}).get("translations"))
    print(f"✅ Extended lexicon to {len(cleaned_lexicon)} entries ({rel_count} with Wikisaurus edges).")
    print(
        f"   - Codenames words in lexicon: {cn_covered}/{len(wl_data.get('codenames', []))} (with translations: {cn_trans})"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich game wordlists using Wiktionary API")
    parser.add_argument("--max-words", type=int, default=6000, help="Maximum words to look up (default: 6000)")
    parser.add_argument("--workers", type=int, default=8, help="Concurrent HTTP batch workers (default: 8)")
    parser.add_argument(
        "--extend-codenames",
        action="store_true",
        help="Incrementally enrich Codenames (400) & Impostor words + merge Wikisaurus neighbors",
    )
    args = parser.parse_args()

    if args.extend_codenames:
        extend_codenames_and_impostor(args.workers)
        return

    candidates = collect_candidate_words(args.max_words)
    print(f"Querying Wiktionary in batches of 50 for {len(candidates)} candidate words...")

    lexicon: dict[str, dict] = {}
    subpage_needed: list[tuple[str, str]] = []  # (word_lower, subpage_title)

    batches = [candidates[i : i + 50] for i in range(0, len(candidates), 50)]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(fetch_batch, b): b for b in batches}
        done = 0
        for fut in as_completed(futures):
            done += 1
            pages = fut.result()
            for orig_word, wikitext in pages.items():
                parsed, has_subpage = parse_english_page(orig_word, wikitext)
                if parsed:
                    key = orig_word.lower()
                    lexicon[key] = parsed
                    if has_subpage and len(parsed["translations"]) < 5 and len(subpage_needed) < 400:
                        subpage_needed.append((key, f"{orig_word}/translations"))
            if done % 15 == 0 or done == len(batches):
                print(f"  Pass 1: {done}/{len(batches)} batches processed ({len(lexicon)} enriched)")

    _fetch_subpages(subpage_needed, lexicon, args.workers)
    _merge_wikisaurus_related(lexicon)

    # Prune entries that still ended up with neither definition nor translations
    cleaned_lexicon = {
        k: v
        for k, v in sorted(lexicon.items())
        if v.get("definition") or v.get("translations") or v.get("aliases") or v.get("related")
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(cleaned_lexicon, f, ensure_ascii=False, separators=(",", ":"))

    with_defs = sum(1 for v in cleaned_lexicon.values() if v.get("definition"))
    with_syns = sum(1 for v in cleaned_lexicon.values() if v.get("aliases"))
    with_trans = sum(1 for v in cleaned_lexicon.values() if v.get("translations"))
    with_etym = sum(1 for v in cleaned_lexicon.values() if v.get("etymology"))
    print(f"\n✅ Saved {len(cleaned_lexicon)} Wiktionary entries to {OUT_PATH.relative_to(PROJECT_ROOT)}:")
    print(f"   - With definitions : {with_defs}")
    print(f"   - With synonyms    : {with_syns}")
    print(f"   - With translations: {with_trans}")
    print(f"   - With etymology   : {with_etym}")


if __name__ == "__main__":
    main()
