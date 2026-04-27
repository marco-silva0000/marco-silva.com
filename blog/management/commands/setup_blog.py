from django.core.management.base import BaseCommand
from wagtail.models import Page, Site

from blog.models import BlogIndexPage


class Command(BaseCommand):
    help = "Set up the Wagtail page tree with a BlogIndexPage at /blog/"

    def handle(self, *args, **options):
        root = Page.objects.filter(depth=1).first()
        if not root:
            self.stderr.write("No root page found. Run migrations first.")
            return

        # Get or create the default home page (depth 2)
        home = Page.objects.filter(depth=2).first()
        if not home:
            self.stderr.write("No home page found.")
            return

        # Create BlogIndexPage if it doesn't exist
        if BlogIndexPage.objects.exists():
            blog_index = BlogIndexPage.objects.first()
            self.stdout.write(f"BlogIndexPage already exists: {blog_index.url}")
        else:
            blog_index = BlogIndexPage(title="Blog", slug="blog")
            home.add_child(instance=blog_index)
            blog_index.save_revision().publish()
            self.stdout.write(self.style.SUCCESS(f"Created BlogIndexPage at {blog_index.url}"))

        # Ensure Site is configured
        site, created = Site.objects.get_or_create(
            is_default_site=True,
            defaults={
                "hostname": "marco-silva.com",
                "root_page": home,
                "site_name": "Marco Silva",
            },
        )
        if not created:
            site.hostname = "marco-silva.com"
            site.root_page = home
            site.site_name = "Marco Silva"
            site.save()
            self.stdout.write("Updated default site config.")
        else:
            self.stdout.write(self.style.SUCCESS("Created default site."))
