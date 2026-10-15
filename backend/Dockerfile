# Django/DRF petition API served by gunicorn. SQLite lives on a mounted volume
# (SQLITE_PATH); admin static assets are baked in via collectstatic + whitenoise.
FROM python:3.13-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=config.settings

EXPOSE 8000

# Non-root runtime user (uid/gid 1000 — matches the Deployment's fsGroup so the
# mounted SQLite volume is writable).
RUN useradd --create-home --uid 1000 app

WORKDIR /app

# Install Python dependencies (gunicorn is pinned in requirements.txt).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application source.
COPY . .

# Collect admin/static assets. DEBUG defaults to True at build time (no env), so
# the production SECRET_KEY guard is not triggered; no database is touched.
RUN python manage.py collectstatic --noinput

RUN chown -R app:app /app
USER app

CMD ["gunicorn", "config.wsgi:application", "-b", "0.0.0.0:8000"]
