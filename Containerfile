FROM python:3.13-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
RUN apt-get update && apt-get -y install libpq-dev gcc

RUN mkdir /venv/
ENV VIRTRUAL_ENV=/venv/
ADD pyproject.toml /tmp/


ENV DJANGO_SETTINGS_MODULE=website.settings

RUN uv venv --directory /venv/
# RUN uv sync --frozen
RUN uv pip install -r /tmp/pyproject.toml --extra dev --directory /venv/

RUN mkdir /code/
WORKDIR /code/
ADD . /code/

EXPOSE 8000

CMD ["/venv/.venv/bin/python", "manage.py", "runserver", "0.0.0.0:8000"]
