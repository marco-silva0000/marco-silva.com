from __future__ import annotations

import re

import pytest
from django.core.management import call_command
from django.test import Client, RequestFactory
from wagtail.models import Page, Site
from wagtailmarkdown.utils import render_markdown

from blog.management.commands.seed_party_game_blog_drafts import BLOG_DRAFTS
from blog.models import BlogIndexPage, BlogPostPage


def _ensure_wagtail_root():
    if not Page.objects.filter(depth=1).exists():
        root = Page.add_root(title="Root", slug="root")
    else:
        root = Page.objects.filter(depth=1).first()
    if not Page.objects.filter(depth=2).exists():
        home = Page(title="Home", slug="home")
        root.add_child(instance=home)
        home.save_revision().publish()
    else:
        home = Page.objects.filter(depth=2).first()
    if not Site.objects.filter(is_default_site=True).exists():
        Site.objects.create(hostname="testserver", root_page=home, is_default_site=True, site_name="Test")


@pytest.mark.django_db
class TestSeedPartyGameBlogDrafts:
    def test_creates_four_unpublished_drafts_cleanly(self):
        _ensure_wagtail_root()
        call_command("seed_party_game_blog_drafts")

        blog_index = BlogIndexPage.objects.first()
        assert blog_index is not None

        drafts = BlogPostPage.objects.child_of(blog_index).order_by("id")
        assert drafts.count() == 4
        assert BlogPostPage.objects.live().count() == 0

        expected_slugs = {spec["slug"]: spec for spec in BLOG_DRAFTS}
        for post in drafts:
            assert post.slug in expected_slugs
            spec = expected_slugs[post.slug]
            assert post.live is False
            assert post.has_unpublished_changes is True
            assert post.title == spec["title"]
            assert set(post.tags.names()) == set(spec["tags"])
            rev_obj = post.get_latest_revision_as_object()
            assert set(rev_obj.tags.names()) == set(spec["tags"])

            # Ensure markdown renders cleanly with wagtailmarkdown (zero <em> inside math)
            md_text = post.body[0].value
            rendered_html = str(render_markdown(md_text))
            for expr in re.findall(r"\$\$([\s\S]+?)\$\$|\$([^\n$]+?)\$", rendered_html):
                combined = expr[0] or expr[1]
                assert "<em>" not in combined and "</em>" not in combined, (
                    f"Broken <em> inside math for {post.slug}: {combined}"
                )
            if "```mermaid" in md_text:
                assert (
                    "flowchart" in rendered_html
                    or "stateDiagram" in rendered_html
                    or "sequenceDiagram" in rendered_html
                )

        # Drafts must NOT appear on public /blog/
        client = Client()
        blog_resp = client.get("/blog/")
        assert blog_resp.status_code == 200
        blog_html = blog_resp.content.decode("utf-8")
        for spec in BLOG_DRAFTS:
            assert spec["title"] not in blog_html

        # Wagtail preview of a draft returns 200 with Draft Preview badge & JS renderers
        rf = RequestFactory()
        req = rf.get("/")
        sample_post = drafts.first()
        preview_resp = sample_post.serve_preview(req, sample_post.default_preview_mode)
        assert preview_resp.status_code == 200
        preview_resp.render()
        preview_html = preview_resp.content.decode("utf-8")
        assert "Draft Preview" in preview_html
        assert "katex.min.js" in preview_html
        assert "mermaid.esm.min.mjs" in preview_html

    def test_idempotency_preserves_user_edits_and_supports_update_drafts(self):
        _ensure_wagtail_root()
        call_command("seed_party_game_blog_drafts")

        first_slug = BLOG_DRAFTS[0]["slug"]
        post = BlogPostPage.objects.get(slug=first_slug)
        post.title = "Custom Edited Title"
        post.save()
        post.save_revision()

        # Re-running without --update-drafts preserves custom edit
        call_command("seed_party_game_blog_drafts")
        post.refresh_from_db()
        assert post.title == "Custom Edited Title"
        assert post.get_latest_revision_as_object().title == "Custom Edited Title"
        assert post.live is False

        # Re-running with --update-drafts resets draft without publishing
        call_command("seed_party_game_blog_drafts", update_drafts=True)
        post.refresh_from_db()
        assert post.title == BLOG_DRAFTS[0]["title"]
        assert post.get_latest_revision_as_object().title == BLOG_DRAFTS[0]["title"]
        assert post.live is False
        assert post.has_unpublished_changes is True
