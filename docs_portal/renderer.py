from __future__ import annotations

import html
import posixpath
import re
from pathlib import Path
from typing import Any

import markdown
from django.conf import settings

DOCS_ROOT = (Path(settings.BASE_DIR) / "docs").resolve()

QUADRANTS: list[tuple[str, str, str, str]] = [
    ("tutorials", "Tutorials", "Learning-oriented lessons", "emerald"),
    ("how-to", "How-To Guides", "Problem-oriented recipes", "blue"),
    ("reference", "Reference", "Information-oriented specifications", "purple"),
    ("explanation", "Explanation", "Understanding-oriented architecture", "amber"),
]

QUADRANT_MAP: dict[str, dict[str, str]] = {
    slug: {"slug": slug, "title": title, "subtitle": subtitle, "accent": accent}
    for slug, title, subtitle, accent in QUADRANTS
}
ALLOWED_QUADRANTS = set(QUADRANT_MAP.keys())
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")

_FRONTMATTER_RE = re.compile(r"^---\r?\n([\s\S]*?)\r?\n---\r?\n")
_MERMAID_FENCE_RE = re.compile(r"```mermaid[ \t]*\r?\n([\s\S]*?)```", re.MULTILINE)
_CODE_FENCE_RE = re.compile(r"(```[\s\S]*?```|~~~[\s\S]*?~~~)")
_INLINE_CODE_RE = re.compile(r"(`+[^`\n]+?`+)")
_DISPLAY_MATH_RE = re.compile(r"\$\$([\s\S]+?)\$\$")
_INLINE_MATH_RE = re.compile(r"(?<!\\)(?<!\$)\$(?!\s)((?:[^$\n\\]|\\.)+?)(?<!\s)\$(?!\$)")
_H1_RE = re.compile(r"<h1[^>]*>([\s\S]*?)</h1>", re.IGNORECASE)
_TAG_STRIP_RE = re.compile(r"<[^>]+>")
_HREF_RE = re.compile(r'href="([^"]+)"')
_ALERT_BLOCKQUOTE_RE = re.compile(
    r"<blockquote>\s*<p>\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\](?:<br\s*/?>|\s)*([\s\S]*?)</blockquote>",
    re.IGNORECASE,
)

_ALERT_META = {
    "NOTE": ("note", "ℹ️", "Note"),
    "TIP": ("tip", "💡", "Tip"),
    "IMPORTANT": ("important", "📌", "Important"),
    "WARNING": ("warning", "⚠️", "Warning"),
    "CAUTION": ("caution", "🚨", "Caution"),
}

_RENDER_CACHE: dict[tuple[str, int], dict[str, Any]] = {}
_NAV_CACHE: tuple[tuple[tuple[str, int], ...], list[dict[str, Any]]] | None = None


def resolve_doc_path(quadrant: str | None, slug: str | None) -> Path | None:
    """Resolve and validate a documentation file path inside DOCS_ROOT."""
    if quadrant is None and slug is None:
        candidate = (DOCS_ROOT / "README.md").resolve()
        return candidate if candidate.is_relative_to(DOCS_ROOT) and candidate.is_file() else None

    if quadrant not in ALLOWED_QUADRANTS:
        return None

    if slug is None:
        candidate = (DOCS_ROOT / quadrant / "README.md").resolve()
        return candidate if candidate.is_relative_to(DOCS_ROOT) and candidate.is_file() else None

    if not SLUG_RE.match(slug):
        return None

    candidate = (DOCS_ROOT / quadrant / f"{slug}.md").resolve()
    if not candidate.is_relative_to(DOCS_ROOT) or not candidate.is_file():
        return None
    return candidate


def parse_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    """Extract simple YAML frontmatter fields and return (meta, body)."""
    match = _FRONTMATTER_RE.match(raw)
    if not match:
        return {}, raw

    meta: dict[str, Any] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        if not key:
            continue
        if key == "tags":
            if value.startswith("[") and value.endswith("]"):
                value = value[1:-1]
            meta["tags"] = [t.strip().strip("'\"") for t in value.split(",") if t.strip()]
        else:
            meta[key] = value.strip("'\"")

    return meta, raw[match.end() :]


def _rewrite_relative_href(href: str, rel_dir: str) -> str:
    """Rewrite a relative .md or quadrant directory link to a clean /docs/ URL."""
    if not href or href.startswith(("http://", "https://", "mailto:", "#", "/")):
        return href

    target, _, fragment = href.partition("#")
    frag_suffix = f"#{fragment}" if fragment else ""
    if not target:
        return frag_suffix

    joined = posixpath.normpath(posixpath.join(rel_dir, target)) if rel_dir else posixpath.normpath(target)
    joined = joined.lstrip("./")

    if joined in ("", ".", "README.md"):
        return f"/docs/{frag_suffix}"

    if joined.endswith("/README.md"):
        prefix = joined[: -len("/README.md")]
        return f"/docs/{prefix}/{frag_suffix}" if prefix in ALLOWED_QUADRANTS else href

    if joined.endswith(".md"):
        stripped = joined[:-3]
        parts = stripped.split("/", 1)
        if len(parts) == 2 and parts[0] in ALLOWED_QUADRANTS and SLUG_RE.match(parts[1]):
            return f"/docs/{parts[0]}/{parts[1]}/{frag_suffix}"
        return href

    if joined in ALLOWED_QUADRANTS:
        return f"/docs/{joined}/{frag_suffix}"

    return href


def _convert_alert_blockquote(match: re.Match[str]) -> str:
    """Convert GitHub-style blockquote alerts into styled callout divs."""
    raw_kind = match.group(1).upper()
    inner = match.group(2).strip()
    kind, icon, label = _ALERT_META.get(raw_kind, ("note", "ℹ️", raw_kind.title()))
    if not inner.startswith("<p>"):
        inner = f"<p>{inner}"
    return (
        f'<div class="doc-callout doc-callout-{kind}"><div class="doc-callout-title">{icon} {label}</div>{inner}</div>'
    )


def render_doc_file(path: Path) -> dict[str, Any]:
    """Parse frontmatter, render Markdown with math/mermaid safety, and cache by mtime."""
    resolved = path.resolve()
    mtime_ns = resolved.stat().st_mtime_ns
    cache_key = (str(resolved), mtime_ns)
    if cache_key in _RENDER_CACHE:
        return _RENDER_CACHE[cache_key]

    raw = resolved.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(raw)

    mermaid_blocks: list[str] = []
    code_blocks: list[str] = []
    math_blocks: list[str] = []
    math_inlines: list[str] = []

    def _stash_mermaid(m: re.Match[str]) -> str:
        idx = len(mermaid_blocks)
        mermaid_blocks.append(m.group(1).strip("\r\n"))
        return f"\n\nDOCSMERMAIDBLOCK{idx}END\n\n"

    def _stash_code(m: re.Match[str]) -> str:
        idx = len(code_blocks)
        code_blocks.append(m.group(0))
        return f"DOCSCODEHOLDER{idx}END"

    def _stash_display_math(m: re.Match[str]) -> str:
        idx = len(math_blocks)
        math_blocks.append(m.group(1).strip())
        return f"DOCSMATHBLOCK{idx}END"

    def _stash_inline_math(m: re.Match[str]) -> str:
        idx = len(math_inlines)
        math_inlines.append(m.group(1))
        return f"DOCSMATHINLINE{idx}END"

    # 1. Extract Mermaid blocks first so they render as <div class="mermaid">.
    protected = _MERMAID_FENCE_RE.sub(_stash_mermaid, body)
    # 2. Protect non-mermaid fenced code and inline code before math extraction.
    protected = _CODE_FENCE_RE.sub(_stash_code, protected)
    protected = _INLINE_CODE_RE.sub(_stash_code, protected)
    # 3. Extract LaTeX display and inline math so markdown doesn't mangle underscores or escapes.
    protected = _DISPLAY_MATH_RE.sub(_stash_display_math, protected)
    protected = _INLINE_MATH_RE.sub(_stash_inline_math, protected)
    # 4. Restore regular code blocks/spans before passing to Python-Markdown.
    for idx, code in enumerate(code_blocks):
        protected = protected.replace(f"DOCSCODEHOLDER{idx}END", code)

    md = markdown.Markdown(
        extensions=["extra", "tables", "fenced_code", "toc", "sane_lists"],
        extension_configs={
            "toc": {
                "permalink": "#",
                "permalink_class": "doc-permalink",
                "permalink_title": "Link to this section",
                "toc_depth": "2-3",
            }
        },
    )
    rendered_html = md.convert(protected)

    # Restore math placeholders safely for KaTeX auto-render.
    for idx, expr in enumerate(math_blocks):
        rendered_html = rendered_html.replace(f"DOCSMATHBLOCK{idx}END", f"$${html.escape(expr)}$$")
    for idx, expr in enumerate(math_inlines):
        rendered_html = rendered_html.replace(f"DOCSMATHINLINE{idx}END", f"${html.escape(expr)}$")

    # Restore Mermaid diagrams cleanly without wrapper <p>.
    for idx, diagram in enumerate(mermaid_blocks):
        div = f'<div class="mermaid">{html.escape(diagram)}</div>'
        rendered_html = rendered_html.replace(f"<p>DOCSMERMAIDBLOCK{idx}END</p>", div)
        rendered_html = rendered_html.replace(f"DOCSMERMAIDBLOCK{idx}END", div)

    # Convert GitHub blockquote alerts and wrap wide tables for horizontal scrolling.
    rendered_html = _ALERT_BLOCKQUOTE_RE.sub(_convert_alert_blockquote, rendered_html)
    rendered_html = rendered_html.replace("<table>", '<div class="doc-table-wrap"><table>')
    rendered_html = rendered_html.replace("</table>", "</table></div>")

    # Rewrite relative .md and quadrant directory links.
    rel_path = resolved.relative_to(DOCS_ROOT)
    rel_dir = "" if rel_path.parent == Path(".") else rel_path.parent.as_posix()
    rendered_html = _HREF_RE.sub(lambda m: f'href="{_rewrite_relative_href(m.group(1), rel_dir)}"', rendered_html)

    # Determine document title from frontmatter or first H1.
    title = meta.get("title")
    if not title:
        h1_match = _H1_RE.search(rendered_html)
        if h1_match:
            title = html.unescape(_TAG_STRIP_RE.sub("", h1_match.group(1))).replace("#", "").strip()
        else:
            title = resolved.stem.replace("-", " ").title()

    # Strip the top-level H1 from TOC tokens so the right-hand TOC focuses on sections.
    toc_tokens = md.toc_tokens
    if len(toc_tokens) == 1 and toc_tokens[0].get("level") == 1:
        toc_tokens = toc_tokens[0].get("children", [])

    result = {
        "title": title,
        "description": meta.get("description", ""),
        "tags": meta.get("tags", []),
        "created": meta.get("created", ""),
        "updated": meta.get("updated", ""),
        "html": rendered_html,
        "toc_tokens": toc_tokens,
        "has_mermaid": bool(mermaid_blocks),
        "has_math": bool(math_blocks or math_inlines),
        "source_relpath": rel_path.as_posix(),
    }
    _RENDER_CACHE[cache_key] = result
    return result


def get_docs_navigation() -> list[dict[str, Any]]:
    """Build sidebar navigation grouped by the 4 Diátaxis quadrants."""
    global _NAV_CACHE

    mtime_sig: list[tuple[str, int]] = []
    for q_slug, _, _, _ in QUADRANTS:
        q_dir = DOCS_ROOT / q_slug
        if q_dir.is_dir():
            mtime_sig.append((q_slug, q_dir.stat().st_mtime_ns))
    sig_tuple = tuple(mtime_sig)

    if _NAV_CACHE is not None and _NAV_CACHE[0] == sig_tuple:
        return _NAV_CACHE[1]

    nav: list[dict[str, Any]] = []
    for q_slug, q_title, q_subtitle, q_accent in QUADRANTS:
        q_dir = DOCS_ROOT / q_slug
        items: list[dict[str, str]] = []
        if q_dir.is_dir():
            for md_file in sorted(q_dir.glob("*.md")):
                if md_file.name == "README.md":
                    continue
                rendered = render_doc_file(md_file)
                items.append(
                    {
                        "slug": md_file.stem,
                        "title": rendered["title"],
                        "url": f"/docs/{q_slug}/{md_file.stem}/",
                    }
                )
        nav.append(
            {
                "slug": q_slug,
                "title": q_title,
                "subtitle": q_subtitle,
                "accent": q_accent,
                "url": f"/docs/{q_slug}/",
                "items": items,
            }
        )

    _NAV_CACHE = (sig_tuple, nav)
    return nav


def get_prev_next(
    nav: list[dict[str, Any]],
    quadrant: str | None,
    slug: str | None,
) -> tuple[dict[str, str] | None, dict[str, str] | None]:
    """Return previous and next document descriptors in reading order."""
    ordered: list[dict[str, str]] = [{"title": "Documentation Hub", "url": "/docs/", "quadrant": ""}]
    for group in nav:
        ordered.append({"title": f"{group['title']} Overview", "url": group["url"], "quadrant": group["title"]})
        for item in group["items"]:
            ordered.append({"title": item["title"], "url": item["url"], "quadrant": group["title"]})

    current_url = (
        "/docs/" if quadrant is None else (f"/docs/{quadrant}/" if slug is None else f"/docs/{quadrant}/{slug}/")
    )
    for idx, entry in enumerate(ordered):
        if entry["url"] == current_url:
            prev_entry = ordered[idx - 1] if idx > 0 else None
            next_entry = ordered[idx + 1] if idx + 1 < len(ordered) else None
            return prev_entry, next_entry
    return None, None
