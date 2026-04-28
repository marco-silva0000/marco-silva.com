FROM python:3.13-slim-bookworm AS base
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
RUN apt-get update && apt-get -y install --no-install-recommends libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /code
COPY pyproject.toml uv.lock ./

RUN uv venv /venv && \
    VIRTUAL_ENV=/venv uv pip install -r pyproject.toml

COPY . .

ENV VIRTUAL_ENV=/venv \
    PATH="/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=website.settings \
    PYTHONUNBUFFERED=1

RUN python manage.py collectstatic --noinput || true

EXPOSE 8000

CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "website.asgi:application"]
