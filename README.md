# marco-silva.com

Personal website for Marco Silva — software engineer and photographer. Features a photo gallery powered by django-photologue, a blog via Wagtail CMS, and a CV page.

## Tech Stack

- **Python 3.13** / **Django 5** / **Wagtail**
- **django-photologue** for photo galleries
- **PostgreSQL 16**
- **Gunicorn** + **WhiteNoise** for serving
- **Containerfile** (OCI image) deployed on **k3s**
- **uv** for dependency management

## Project Structure

```
website/          Django project settings & root URL config
photos/           Photo gallery app (extends photologue)
blog/             Blog app (Wagtail pages)
templates/        HTML templates
static/           Static assets (images, favicon)
k8s/              Kubernetes manifests (base + overlays)
deploy.sh         Production deploy script
Containerfile     Container image build
```

## Local Development

Prerequisites: [Podman](https://podman.io/) installed.

1. Build the container image:
   ```bash
   podman build -t marco-silva.com:latest -f Containerfile .
   ```

2. Start the dev pod (Django + PostgreSQL):
   ```bash
   podman kube play k8s/dev-pod.yaml
   ```

3. Run migrations:
   ```bash
   podman exec marco-dev-django python manage.py migrate
   ```

4. Create a superuser:
   ```bash
   podman exec -it marco-dev-django python manage.py createsuperuser
   ```

5. Visit http://localhost:8000

To stop:
```bash
podman kube down k8s/dev-pod.yaml
```

## Deployment

Production runs on k3s. The container image is published to `ghcr.io/marco-silva0000/marco-silva.com:latest`.

```bash
./deploy.sh
```

This pulls the latest image from GHCR and restarts the k3s deployment.

## License

All rights reserved.
