# Blog Guide (Wagtail)

## Accessing the CMS

Go to `/cms/` and log in with your admin credentials.

## First-time setup

Run the setup command (already done in prod):

```bash
kubectl exec -n marco-silva deploy/django -- python manage.py setup_blog
```

This creates the BlogIndexPage at `/blog/` and configures the Wagtail site.

## Creating a blog post

1. Go to `/cms/`
2. In the sidebar, click **Pages**
3. Click **Blog** (the BlogIndexPage)
4. Click **Add child page**
5. Select **Blog Post Page**
6. Fill in:
   - **Title** — your post title (also becomes the URL slug)
   - **Body** — click **+** to add blocks:
     - **Markdown** — write in markdown (supports headings, links, code blocks, images, tables)
     - **Raw HTML** — paste raw HTML if needed
   - **Tags** — add comma-separated tags
7. Click **Publish** (or **Save Draft** to work on it later)

## Writing in markdown

The markdown block supports standard markdown plus:

- `# Heading 1` through `###### Heading 6`
- `**bold**` and `*italic*`
- `[link text](url)`
- `` `inline code` `` and fenced code blocks with ``` 
- `> blockquotes`
- `- unordered lists` and `1. ordered lists`
- `| tables |` with pipes
- `![alt](image-url)` for images

## Managing posts

- **Draft** — saved but not visible to the public
- **Published** — live on the site
- **Unpublish** — take a published post offline (from the action menu)
- **Delete** — permanent removal

## Tags

Tags are added per post. They show up on the post detail page. The blog index page lists all published posts ordered by date.

## RSS feed

The blog has an RSS feed at `/feeds/blog/` that readers can subscribe to.

## Templates

Blog templates are in `templates/blog/`:

- `blog_index_page.html` — the `/blog/` listing page
- `blog_post_page.html` — individual post pages

Both extend `base.html` and use the same minimal style as the rest of the site.

## URL structure

```
/blog/                    → BlogIndexPage (list of all posts)
/blog/my-post-title/      → BlogPostPage (individual post)
/feeds/blog/              → RSS feed
/cms/                     → Wagtail admin
```
