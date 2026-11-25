from __future__ import annotations

from django.http import Http404
from django.shortcuts import redirect, render

from .renderer import (
    QUADRANT_MAP,
    get_docs_navigation,
    get_prev_next,
    render_doc_file,
    resolve_doc_path,
)


def _render_doc_response(request, quadrant: str | None = None, slug: str | None = None):
    path = resolve_doc_path(quadrant, slug)
    if path is None:
        raise Http404("Documentation page not found.")

    doc = render_doc_file(path)
    nav = get_docs_navigation()
    prev_doc, next_doc = get_prev_next(nav, quadrant, slug)
    quadrant_meta = QUADRANT_MAP.get(quadrant) if quadrant else None

    return render(
        request,
        "docs_portal/doc_page.html",
        {
            "doc": doc,
            "nav": nav,
            "active_quadrant": quadrant,
            "active_slug": slug,
            "quadrant_meta": quadrant_meta,
            "prev_doc": prev_doc,
            "next_doc": next_doc,
        },
    )


def doc_index(request):
    return _render_doc_response(request, quadrant=None, slug=None)


def doc_quadrant(request, quadrant: str):
    return _render_doc_response(request, quadrant=quadrant, slug=None)


def doc_md_redirect(request, quadrant: str, slug: str):
    path = resolve_doc_path(quadrant, slug)
    if path is None:
        raise Http404("Documentation page not found.")
    return redirect("docs:detail", quadrant=quadrant, slug=slug, permanent=True)


def doc_detail(request, quadrant: str, slug: str):
    if slug.endswith(".md"):
        clean_slug = slug[:-3]
        if resolve_doc_path(quadrant, clean_slug) is None:
            raise Http404("Documentation page not found.")
        return redirect("docs:detail", quadrant=quadrant, slug=clean_slug, permanent=True)
    return _render_doc_response(request, quadrant=quadrant, slug=slug)
