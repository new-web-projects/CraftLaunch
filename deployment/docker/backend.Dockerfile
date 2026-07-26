# Production image for the Django backend.
# Build from the repo root:
#   docker build -f deployment/docker/backend.Dockerfile -t craftlaunch-backend .

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production

WORKDIR /app

# libpq5 is the runtime Postgres client library psycopg[binary] needs.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/production.txt

COPY backend/ .

RUN addgroup --system django && adduser --system --ingroup django django \
    && mkdir -p /app/staticfiles /app/media \
    && chown -R django:django /app
USER django

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
