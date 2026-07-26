# Development image — hot reload via the bind mount in docker-compose.yml.
# Not used in production; see backend.Dockerfile for that image.
# No venv needed here: the container itself is the isolated environment.

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/development.txt
COPY backend/ .

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
