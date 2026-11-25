from __future__ import annotations

import re

import pytest
from django.test import Client

from docs_portal.renderer import ALLOWED_QUADRANTS, DOCS_ROOT, resolve_doc_path


@pytest.mark.django_db
class TestDocsPortal:
    def test_docs_hub_and_quadrant_indices_return_200(self):
        client = Client()
        resp = client.get("/docs/")
        assert resp.status_code == 200
        html = resp.content.decode("utf-8")
        assert "Diátaxis" in html
        for quadrant in ("Tutorials", "How-To Guides", "Reference", "Explanation"):
            assert quadrant in html

        for q_slug in ALLOWED_QUADRANTS:
            q_resp = client.get(f"/docs/{q_slug}/")
            assert q_resp.status_code == 200

    def test_every_quadrant_markdown_doc_renders_cleanly(self):
        client = Client()
        doc_count = 0

        for q_slug in sorted(ALLOWED_QUADRANTS):
            q_dir = DOCS_ROOT / q_slug
            for md_file in sorted(q_dir.glob("*.md")):
                if md_file.name == "README.md":
                    continue
                doc_count += 1
                url = f"/docs/{q_slug}/{md_file.stem}/"
                resp = client.get(url)
                assert resp.status_code == 200, f"Failed for {url}"
                html = resp.content.decode("utf-8")

                # Extract rendered article body
                match = re.search(r'<article[^>]*id="doc-article"[^>]*>([\s\S]*?)</article>', html)
                assert match, f"Missing article container on {url}"
                article_html = match.group(1)

                # Frontmatter must not leak into article
                assert "tags: [" not in article_html
                assert "description:" not in article_html[:200]

                # No un-rewritten relative .md hrefs inside article
                rel_md_hrefs = [
                    h
                    for h in re.findall(r'href="([^"]+)"', article_html)
                    if not h.startswith(("http://", "https://", "mailto:", "#", "/"))
                ]
                assert not rel_md_hrefs, f"Unrewritten relative hrefs in {url}: {rel_md_hrefs}"

                # Ensure math expressions were never mangled with <em> by markdown
                for expr in re.findall(r"\$\$([\s\S]+?)\$\$|\$([^\n$]+?)\$", article_html):
                    combined = expr[0] or expr[1]
                    assert "<em>" not in combined and "</em>" not in combined, (
                        f"Broken <em> inside math expression in {url}: {combined}"
                    )

        assert doc_count == 21

    def test_mermaid_and_alerts_render_expected_markup(self):
        client = Client()

        # Explanation doc with Mermaid + KaTeX
        resp = client.get("/docs/explanation/explanation-combinatorics-of-secret-santa/")
        assert resp.status_code == 200
        html = resp.content.decode("utf-8")
        assert '<div class="mermaid">' in html
        assert "mermaid.esm.min.mjs" in html
        assert "katex.min.js" in html

        # How-To doc with [!CAUTION] alert
        caution_resp = client.get("/docs/how-to/how-to-calibrate-clues-in-rank-it-ito/")
        assert caution_resp.status_code == 200
        assert "doc-callout-caution" in caution_resp.content.decode("utf-8")

    def test_md_extension_redirects_permanently(self):
        client = Client()
        resp = client.get("/docs/tutorials/tutorial-getting-started-with-party-games.md")
        assert resp.status_code == 301
        assert resp["Location"].endswith("/docs/tutorials/tutorial-getting-started-with-party-games/")

    def test_security_traversal_and_non_quadrant_files_return_404(self):
        client = Client()
        assert resolve_doc_path("tutorials", "../AGENTS") is None
        assert resolve_doc_path("reference", "../../website/settings") is None
        assert resolve_doc_path("unknown", "foo") is None

        for bad_url in (
            "/docs/unknown/",
            "/docs/tutorials/does-not-exist/",
            "/docs/tutorials/../AGENTS/",
            "/docs/WORD_GAMES_FEASIBILITY/",
        ):
            assert client.get(bad_url).status_code == 404

    def test_site_nav_and_game_room_links_resolve(self):
        client = Client()
        home_html = client.get("/").content.decode("utf-8")
        assert 'href="/docs/"' in home_html

        games_resp = client.get("/games/")
        assert games_resp.status_code == 200
        games_html = games_resp.content.decode("utf-8")
        doc_links = set(re.findall(r'href="(/docs/[^"#]+)(?:#[^"]*)?"', games_html))
        assert len(doc_links) >= 7
        for link in doc_links:
            assert client.get(link).status_code == 200, f"Broken /games/ doc link: {link}"
