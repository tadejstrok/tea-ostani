# Petition API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone Django REST API that persists petition signatures and optional public messages, exposes public count/names/messages endpoints, and provides moderation via Django admin.

**Architecture:** API-only Django project in `backend/`, served separately from the static `index.html` (CORS-enabled). One app `petition` with `Signature` and `Message` models, DRF views under `/api/`, a pluggable `screen()` auto-hold hook for post-moderation, and Django admin as the moderation UI. SQLite storage.

**Tech Stack:** Python 3.11, Django 5.x, Django REST Framework, django-cors-headers, WhiteNoise, python-dotenv, pytest + pytest-django.

## Global Constraints

- All backend code lives under `backend/`. Do **not** modify `index.html` or `public/`.
- Python 3.11 (available as `python3`). Use a project venv at `backend/.venv`.
- API paths are all under `/api/`. Admin at `/admin/`.
- A signature **always counts** toward the total; moderation status only gates public *display* of the name. Only deletion removes it from the count.
- Anonymous signatures never appear in the public names list, regardless of status.
- Duplicate email on submit → **silent success** (never reveal the email already signed).
- Moderation statuses are exactly: `published`, `pending`, `hidden`.
- Message `text` max length 500.
- Tests are written first (TDD). Commit after each task's tests pass.
- Run all commands from the `backend/` directory unless stated otherwise.

---

### Task 1: Project scaffold, dependencies, settings

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/requirements-dev.txt`
- Create: `backend/.env.example`
- Create: `backend/.gitignore`
- Create: `backend/config/__init__.py`, `backend/config/settings.py`, `backend/config/urls.py`, `backend/config/wsgi.py`, `backend/config/asgi.py`
- Create: `backend/manage.py`
- Create: `backend/petition/__init__.py`, `backend/petition/apps.py`
- Create: `backend/pytest.ini`
- Create: `backend/petition/tests/__init__.py`, `backend/petition/tests/test_smoke.py`

**Interfaces:**
- Produces: Django project `config` with `DJANGO_SETTINGS_MODULE=config.settings`; app label `petition`; root URLConf `config.urls` mounting `petition.urls` under `api/`; DRF configured with `PageNumberPagination` (PAGE_SIZE 50) and throttle rate scope `signature: 20/hour`; CORS via `CORS_ALLOWED_ORIGINS`.

- [ ] **Step 1: Create venv and install dependencies**

Create `backend/requirements.txt`:

```
Django>=5.0,<5.2
djangorestframework>=3.15,<3.16
django-cors-headers>=4.3
whitenoise>=6.6
python-dotenv>=1.0
```

Create `backend/requirements-dev.txt`:

```
-r requirements.txt
pytest>=8.0
pytest-django>=4.8
```

Run:

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements-dev.txt
```

Expected: installs succeed. (All subsequent `python`/`pytest`/`django-admin` commands use `.venv/bin/…`.)

- [ ] **Step 2: Scaffold the Django project**

Run:

```bash
cd backend
.venv/bin/django-admin startproject config .
```

Expected: creates `backend/manage.py` and `backend/config/`.

- [ ] **Step 3: Create the `petition` app package**

Create `backend/petition/__init__.py` (empty).

Create `backend/petition/apps.py`:

```python
from django.apps import AppConfig


class PetitionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "petition"
```

Create `backend/petition/tests/__init__.py` (empty).

- [ ] **Step 4: Write `backend/config/settings.py`**

Replace the generated `backend/config/settings.py` with:

```python
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _csv(name, default):
    return [v.strip() for v in os.getenv(name, default).split(",") if v.strip()]


SECRET_KEY = os.getenv("SECRET_KEY", "dev-insecure-key-change-me")
DEBUG = os.getenv("DEBUG", "True").lower() == "true"
ALLOWED_HOSTS = _csv("ALLOWED_HOSTS", "localhost,127.0.0.1")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "petition",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Europe/Ljubljana"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = _csv(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:8000,http://127.0.0.1:8000,"
    "http://localhost:5500,http://127.0.0.1:5500",
)

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_THROTTLE_RATES": {"signature": "20/hour"},
}
```

- [ ] **Step 5: Wire root URLConf**

Replace `backend/config/urls.py` with:

```python
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("petition.urls")),
]
```

Create a temporary empty `backend/petition/urls.py` so the include resolves:

```python
from django.urls import path

urlpatterns = []
```

- [ ] **Step 6: Add pytest config and .env.example and .gitignore**

Create `backend/pytest.ini`:

```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings
python_files = test_*.py
```

Create `backend/.env.example`:

```
SECRET_KEY=change-me-to-a-long-random-string
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5500,http://127.0.0.1:5500
```

Create `backend/.gitignore`:

```
.venv/
db.sqlite3
.env
staticfiles/
__pycache__/
*.pyc
```

- [ ] **Step 7: Write the smoke test**

Create `backend/petition/tests/test_smoke.py`:

```python
def test_settings_load():
    from django.conf import settings

    assert "petition" in settings.INSTALLED_APPS
    assert settings.REST_FRAMEWORK["PAGE_SIZE"] == 50
```

- [ ] **Step 8: Run system check and smoke test**

Run:

```bash
cd backend
.venv/bin/python manage.py check
.venv/bin/pytest -v
```

Expected: `check` reports no issues; smoke test PASSES.

- [ ] **Step 9: Commit**

```bash
cd backend
git add -A
git commit -m "chore: scaffold Django petition API project"
```

---

### Task 2: Models — Signature and Message

**Files:**
- Create: `backend/petition/models.py`
- Create: `backend/petition/tests/test_models.py`
- Create (generated): `backend/petition/migrations/__init__.py` + `0001_initial.py`

**Interfaces:**
- Produces:
  - `ModerationStatus` (TextChoices): `PUBLISHED="published"`, `PENDING="pending"`, `HIDDEN="hidden"`.
  - `Signature(name, email[unique], newsletter[bool], anonymous[bool], consent[bool], name_status[ModerationStatus, default PUBLISHED], ip_address[nullable], created_at)`; `Meta.ordering = ["-created_at"]`.
  - `Message(signature[FK→Signature, related_name="messages"], recipient, text[max 500], status[ModerationStatus, default PUBLISHED], created_at)`; `Meta.ordering = ["-created_at"]`.

- [ ] **Step 1: Write the failing tests**

Create `backend/petition/tests/test_models.py`:

```python
import pytest
from django.db import IntegrityError

from petition.models import Message, ModerationStatus, Signature

pytestmark = pytest.mark.django_db


def test_signature_defaults():
    sig = Signature.objects.create(name="Ana", email="ana@example.com", consent=True)
    assert sig.newsletter is False
    assert sig.anonymous is False
    assert sig.name_status == ModerationStatus.PUBLISHED
    assert sig.ip_address is None
    assert sig.created_at is not None


def test_email_is_unique():
    Signature.objects.create(name="Ana", email="dup@example.com", consent=True)
    with pytest.raises(IntegrityError):
        Signature.objects.create(name="Bob", email="dup@example.com", consent=True)


def test_message_linked_to_signature():
    sig = Signature.objects.create(name="Ana", email="ana@example.com", consent=True)
    msg = Message.objects.create(signature=sig, recipient="Mijič", text="Odstopi.")
    assert msg.status == ModerationStatus.PUBLISHED
    assert list(sig.messages.all()) == [msg]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/bin/pytest petition/tests/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError`/`ImportError` for `petition.models`.

- [ ] **Step 3: Write the models**

Create `backend/petition/models.py`:

```python
from django.db import models


class ModerationStatus(models.TextChoices):
    PUBLISHED = "published", "Published"
    PENDING = "pending", "Pending"
    HIDDEN = "hidden", "Hidden"


class Signature(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    newsletter = models.BooleanField(default=False)
    anonymous = models.BooleanField(default=False)
    consent = models.BooleanField(default=False)
    name_status = models.CharField(
        max_length=20,
        choices=ModerationStatus.choices,
        default=ModerationStatus.PUBLISHED,
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} <{self.email}>"


class Message(models.Model):
    signature = models.ForeignKey(
        Signature, on_delete=models.CASCADE, related_name="messages"
    )
    recipient = models.CharField(max_length=200)
    text = models.CharField(max_length=500)
    status = models.CharField(
        max_length=20,
        choices=ModerationStatus.choices,
        default=ModerationStatus.PUBLISHED,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"To {self.recipient}: {self.text[:40]}"
```

- [ ] **Step 4: Generate and apply migration**

Run:

```bash
cd backend
.venv/bin/python manage.py makemigrations petition
.venv/bin/python manage.py migrate
```

Expected: creates `petition/migrations/0001_initial.py`; migrate applies cleanly.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && .venv/bin/pytest petition/tests/test_models.py -v`
Expected: all 3 tests PASS.

- [ ] **Step 6: Commit**

```bash
cd backend
git add -A
git commit -m "feat: add Signature and Message models"
```

---

### Task 3: The `screen()` auto-hold scaffold

**Files:**
- Create: `backend/petition/moderation.py`
- Create: `backend/petition/tests/test_moderation.py`

**Interfaces:**
- Produces: `screen(text: str | None) -> bool` — returns `True` when the text should be held for manual review. Default heuristic flags any text containing a URL (`http://`, `https://`, or `www.`); empty/None is never flagged. `BLOCKLIST` module constant documents the extension point.

- [ ] **Step 1: Write the failing tests**

Create `backend/petition/tests/test_moderation.py`:

```python
from petition.moderation import screen


def test_clean_text_not_flagged():
    assert screen("Odstopi takoj, gospod Mijič.") is False


def test_empty_and_none_not_flagged():
    assert screen("") is False
    assert screen(None) is False


def test_url_is_flagged():
    assert screen("Poglej https://spam.example") is True
    assert screen("obisci www.spam.si") is True
    assert screen("HTTP://LOUD.example") is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/bin/pytest petition/tests/test_moderation.py -v`
Expected: FAIL with import error for `petition.moderation`.

- [ ] **Step 3: Write the implementation**

Create `backend/petition/moderation.py`:

```python
"""Pluggable auto-hold hook for post-moderation.

`screen()` returns True when content should be withheld (status `pending`)
until a moderator approves it. The default heuristic holds anything that
contains a URL — a common spam signal. Extend `BLOCKLIST` or replace the
body to tighten moderation without touching models or views.
"""

# Substrings (case-insensitive) that hold content for manual review.
BLOCKLIST = (
    "http://",
    "https://",
    "www.",
)


def screen(text):
    """Return True if `text` should be held for manual review."""
    if not text:
        return False
    lowered = text.lower()
    return any(term in lowered for term in BLOCKLIST)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && .venv/bin/pytest petition/tests/test_moderation.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
cd backend
git add -A
git commit -m "feat: add screen() auto-hold moderation scaffold"
```

---

### Task 4: Serializers

**Files:**
- Create: `backend/petition/serializers.py`
- Create: `backend/petition/tests/test_serializers.py`

**Interfaces:**
- Consumes: `Signature`, `Message` from `petition.models`.
- Produces:
  - `MessageInputSerializer` — fields `recipient` (CharField, max 200), `text` (CharField, max 500). Both required.
  - `SignatureCreateSerializer` — fields `name` (CharField, max 200), `email` (EmailField), `newsletter` (BooleanField default False), `anonymous` (BooleanField default False), `consent` (BooleanField), `message` (nested `MessageInputSerializer`, `required=False`). `validate_consent` rejects non-true.
  - `PublicSignatureSerializer` — ModelSerializer, fields `["name", "created_at"]`.
  - `PublicMessageSerializer` — ModelSerializer, fields `["recipient", "text", "created_at"]`.

- [ ] **Step 1: Write the failing tests**

Create `backend/petition/tests/test_serializers.py`:

```python
from petition.serializers import SignatureCreateSerializer


def test_valid_payload_without_message():
    s = SignatureCreateSerializer(
        data={"name": "Ana", "email": "ana@example.com", "consent": True}
    )
    assert s.is_valid(), s.errors
    assert s.validated_data["newsletter"] is False
    assert s.validated_data["anonymous"] is False
    assert "message" not in s.validated_data


def test_valid_payload_with_message():
    s = SignatureCreateSerializer(
        data={
            "name": "Ana",
            "email": "ana@example.com",
            "consent": True,
            "message": {"recipient": "Mijič", "text": "Odstopi."},
        }
    )
    assert s.is_valid(), s.errors
    assert s.validated_data["message"]["recipient"] == "Mijič"


def test_consent_must_be_true():
    s = SignatureCreateSerializer(
        data={"name": "Ana", "email": "ana@example.com", "consent": False}
    )
    assert not s.is_valid()
    assert "consent" in s.errors


def test_message_requires_recipient_and_text():
    s = SignatureCreateSerializer(
        data={
            "name": "Ana",
            "email": "ana@example.com",
            "consent": True,
            "message": {"text": "Odstopi."},
        }
    )
    assert not s.is_valid()
    assert "message" in s.errors


def test_message_text_max_length():
    s = SignatureCreateSerializer(
        data={
            "name": "Ana",
            "email": "ana@example.com",
            "consent": True,
            "message": {"recipient": "Mijič", "text": "x" * 501},
        }
    )
    assert not s.is_valid()
    assert "message" in s.errors
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/bin/pytest petition/tests/test_serializers.py -v`
Expected: FAIL with import error for `petition.serializers`.

- [ ] **Step 3: Write the serializers**

Create `backend/petition/serializers.py`:

```python
from rest_framework import serializers

from .models import Message, Signature


class MessageInputSerializer(serializers.Serializer):
    recipient = serializers.CharField(max_length=200)
    text = serializers.CharField(max_length=500)


class SignatureCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    email = serializers.EmailField()
    newsletter = serializers.BooleanField(default=False)
    anonymous = serializers.BooleanField(default=False)
    consent = serializers.BooleanField()
    message = MessageInputSerializer(required=False)

    def validate_consent(self, value):
        if value is not True:
            raise serializers.ValidationError("Consent is required.")
        return value


class PublicSignatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Signature
        fields = ["name", "created_at"]


class PublicMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ["recipient", "text", "created_at"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && .venv/bin/pytest petition/tests/test_serializers.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
cd backend
git add -A
git commit -m "feat: add petition serializers"
```

---

### Task 5: Signature endpoints (submit, list, count)

**Files:**
- Create: `backend/petition/views.py`
- Modify: `backend/petition/urls.py` (replace the empty stub)
- Create: `backend/petition/tests/test_signature_api.py`

**Interfaces:**
- Consumes: serializers from Task 4; `screen()` from Task 3; models + `ModerationStatus` from Task 2.
- Produces:
  - `get_client_ip(request) -> str | None`.
  - `SignatureListCreateView` at `GET/POST /api/signatures/`:
    - `POST` body `{name, email, newsletter?, anonymous?, consent, message?: {recipient, text}}`. Validates via `SignatureCreateSerializer`. Runs `screen()` on name and message text → sets `pending`/`published`. Captures IP. **Silent dedupe** on existing email (case-insensitive) → returns `201 {"status": "ok"}` with no new rows. Fresh create also returns `201 {"status": "ok"}`. Throttled with scope `signature` on POST only.
    - `GET` returns paginated `PublicSignatureSerializer` list filtered to `anonymous=False, name_status=published`, newest first.
  - `SignatureCountView` at `GET /api/signatures/count/` → `{"count": <int>}` (all signatures).

- [ ] **Step 1: Write the failing tests**

Create `backend/petition/tests/test_signature_api.py`:

```python
import pytest
from rest_framework.test import APIClient

from petition.models import Message, ModerationStatus, Signature

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


def test_submit_creates_signature(client):
    resp = client.post(
        "/api/signatures/",
        {"name": "Ana", "email": "ana@example.com", "consent": True},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.json() == {"status": "ok"}
    sig = Signature.objects.get()
    assert sig.name == "Ana"
    assert sig.name_status == ModerationStatus.PUBLISHED
    assert sig.ip_address is not None


def test_submit_with_message_creates_linked_message(client):
    client.post(
        "/api/signatures/",
        {
            "name": "Ana",
            "email": "ana@example.com",
            "consent": True,
            "message": {"recipient": "Mijič", "text": "Odstopi."},
        },
        format="json",
    )
    msg = Message.objects.get()
    assert msg.recipient == "Mijič"
    assert msg.status == ModerationStatus.PUBLISHED


def test_message_with_url_is_held_pending(client):
    client.post(
        "/api/signatures/",
        {
            "name": "Ana",
            "email": "ana@example.com",
            "consent": True,
            "message": {"recipient": "Mijič", "text": "glej https://spam.example"},
        },
        format="json",
    )
    assert Message.objects.get().status == ModerationStatus.PENDING


def test_duplicate_email_is_silent_noop(client):
    payload = {"name": "Ana", "email": "dup@example.com", "consent": True}
    first = client.post("/api/signatures/", payload, format="json")
    second = client.post(
        "/api/signatures/",
        {"name": "Someone Else", "email": "DUP@example.com", "consent": True,
         "message": {"recipient": "Mijič", "text": "hi"}},
        format="json",
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json() == {"status": "ok"}
    assert Signature.objects.count() == 1
    assert Message.objects.count() == 0


def test_consent_false_returns_400(client):
    resp = client.post(
        "/api/signatures/",
        {"name": "Ana", "email": "ana@example.com", "consent": False},
        format="json",
    )
    assert resp.status_code == 400
    assert "consent" in resp.json()


def test_missing_name_returns_400(client):
    resp = client.post(
        "/api/signatures/",
        {"email": "ana@example.com", "consent": True},
        format="json",
    )
    assert resp.status_code == 400
    assert "name" in resp.json()


def test_count_endpoint(client):
    Signature.objects.create(name="A", email="a@example.com", consent=True)
    Signature.objects.create(name="B", email="b@example.com", consent=True)
    resp = client.get("/api/signatures/count/")
    assert resp.status_code == 200
    assert resp.json() == {"count": 2}


def test_list_excludes_anonymous_and_non_published(client):
    Signature.objects.create(name="Visible", email="v@example.com", consent=True)
    Signature.objects.create(
        name="Anon", email="anon@example.com", consent=True, anonymous=True
    )
    Signature.objects.create(
        name="Held", email="held@example.com", consent=True,
        name_status=ModerationStatus.PENDING,
    )
    resp = client.get("/api/signatures/")
    assert resp.status_code == 200
    names = [row["name"] for row in resp.json()["results"]]
    assert names == ["Visible"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/bin/pytest petition/tests/test_signature_api.py -v`
Expected: FAIL (no views / 404s).

- [ ] **Step 3: Write the views**

Create `backend/petition/views.py`:

```python
from django.db import IntegrityError
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import ModerationStatus, Signature
from .moderation import screen
from .serializers import (
    PublicSignatureSerializer,
    SignatureCreateSerializer,
)


def get_client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _status_for(text):
    return ModerationStatus.PENDING if screen(text) else ModerationStatus.PUBLISHED


class SignatureListCreateView(generics.ListCreateAPIView):
    serializer_class = PublicSignatureSerializer

    def get_queryset(self):
        return Signature.objects.filter(
            anonymous=False, name_status=ModerationStatus.PUBLISHED
        )

    def get_throttles(self):
        if self.request.method == "POST":
            self.throttle_scope = "signature"
            return [ScopedRateThrottle()]
        return []

    def create(self, request, *args, **kwargs):
        serializer = SignatureCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Silent dedupe: never reveal whether the email already signed.
        if Signature.objects.filter(email__iexact=data["email"]).exists():
            return Response({"status": "ok"}, status=status.HTTP_201_CREATED)

        try:
            signature = Signature.objects.create(
                name=data["name"],
                email=data["email"],
                newsletter=data["newsletter"],
                anonymous=data["anonymous"],
                consent=data["consent"],
                name_status=_status_for(data["name"]),
                ip_address=get_client_ip(request),
            )
        except IntegrityError:
            # Race on the unique email — treat as the same silent no-op.
            return Response({"status": "ok"}, status=status.HTTP_201_CREATED)

        message = data.get("message")
        if message:
            signature.messages.create(
                recipient=message["recipient"],
                text=message["text"],
                status=_status_for(message["text"]),
            )
        return Response({"status": "ok"}, status=status.HTTP_201_CREATED)


class SignatureCountView(APIView):
    def get(self, request):
        return Response({"count": Signature.objects.count()})
```

- [ ] **Step 4: Wire the URLs**

Replace `backend/petition/urls.py` with:

```python
from django.urls import path

from . import views

urlpatterns = [
    path("signatures/", views.SignatureListCreateView.as_view(), name="signature-list"),
    path("signatures/count/", views.SignatureCountView.as_view(), name="signature-count"),
]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && .venv/bin/pytest petition/tests/test_signature_api.py -v`
Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
cd backend
git add -A
git commit -m "feat: add signature submit/list/count endpoints"
```

---

### Task 6: Public messages endpoint

**Files:**
- Modify: `backend/petition/views.py` (add view)
- Modify: `backend/petition/urls.py` (add route)
- Create: `backend/petition/tests/test_message_api.py`

**Interfaces:**
- Consumes: `PublicMessageSerializer`, `Message`, `ModerationStatus`.
- Produces: `PublicMessageListView` at `GET /api/messages/` → paginated `published`-only messages, newest first.

- [ ] **Step 1: Write the failing tests**

Create `backend/petition/tests/test_message_api.py`:

```python
import pytest
from rest_framework.test import APIClient

from petition.models import Message, ModerationStatus, Signature

pytestmark = pytest.mark.django_db


@pytest.fixture
def sig():
    return Signature.objects.create(name="Ana", email="ana@example.com", consent=True)


def test_lists_only_published_messages(sig):
    Message.objects.create(signature=sig, recipient="Mijič", text="visible")
    Message.objects.create(
        signature=sig, recipient="Mijič", text="held",
        status=ModerationStatus.PENDING,
    )
    Message.objects.create(
        signature=sig, recipient="Mijič", text="hidden",
        status=ModerationStatus.HIDDEN,
    )
    resp = APIClient().get("/api/messages/")
    assert resp.status_code == 200
    texts = [row["text"] for row in resp.json()["results"]]
    assert texts == ["visible"]


def test_message_shape(sig):
    Message.objects.create(signature=sig, recipient="Mijič", text="hi")
    row = APIClient().get("/api/messages/").json()["results"][0]
    assert set(row.keys()) == {"recipient", "text", "created_at"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/bin/pytest petition/tests/test_message_api.py -v`
Expected: FAIL (404 / no route).

- [ ] **Step 3: Add the view**

In `backend/petition/views.py`, add the import and view. Change the import block:

```python
from .serializers import (
    PublicMessageSerializer,
    PublicSignatureSerializer,
    SignatureCreateSerializer,
)
```

Add `Message` to the models import:

```python
from .models import Message, ModerationStatus, Signature
```

Append at the end of the file:

```python
class PublicMessageListView(generics.ListAPIView):
    serializer_class = PublicMessageSerializer

    def get_queryset(self):
        return Message.objects.filter(status=ModerationStatus.PUBLISHED)
```

- [ ] **Step 4: Add the route**

In `backend/petition/urls.py`, add to `urlpatterns`:

```python
    path("messages/", views.PublicMessageListView.as_view(), name="message-list"),
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && .venv/bin/pytest petition/tests/test_message_api.py -v`
Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
cd backend
git add -A
git commit -m "feat: add public messages endpoint"
```

---

### Task 7: Moderation via Django admin

**Files:**
- Create: `backend/petition/admin.py`
- Create: `backend/petition/tests/test_admin.py`

**Interfaces:**
- Consumes: `Signature`, `Message`, `ModerationStatus`.
- Produces: registered `SignatureAdmin` (with inline messages, list filters, search, and `publish_names`/`hide_names` actions) and `MessageAdmin` (list filters, search, `publish_messages`/`hide_messages` actions).

- [ ] **Step 1: Write the failing tests**

Create `backend/petition/tests/test_admin.py`:

```python
import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import Client

from petition.models import Message, ModerationStatus, Signature

pytestmark = pytest.mark.django_db


def test_models_registered():
    assert Signature in admin.site._registry
    assert Message in admin.site._registry


def test_changelist_requires_auth():
    resp = Client().get("/admin/petition/signature/")
    assert resp.status_code == 302
    assert "/admin/login/" in resp.headers["Location"]


def test_superuser_can_view_changelist():
    get_user_model().objects.create_superuser("mod", "mod@example.com", "pw12345!")
    client = Client()
    client.login(username="mod", password="pw12345!")
    resp = client.get("/admin/petition/signature/")
    assert resp.status_code == 200


def test_hide_names_action_sets_status():
    from petition.admin import hide_names

    sig = Signature.objects.create(name="Ana", email="a@example.com", consent=True)
    hide_names(None, None, Signature.objects.all())
    sig.refresh_from_db()
    assert sig.name_status == ModerationStatus.HIDDEN


def test_hide_messages_action_sets_status():
    from petition.admin import hide_messages

    sig = Signature.objects.create(name="Ana", email="a@example.com", consent=True)
    msg = Message.objects.create(signature=sig, recipient="Mijič", text="hi")
    hide_messages(None, None, Message.objects.all())
    msg.refresh_from_db()
    assert msg.status == ModerationStatus.HIDDEN
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/bin/pytest petition/tests/test_admin.py -v`
Expected: FAIL (models not registered / import errors).

- [ ] **Step 3: Write the admin**

Create `backend/petition/admin.py`:

```python
from django.contrib import admin

from .models import Message, ModerationStatus, Signature


@admin.action(description="Publish selected names")
def publish_names(modeladmin, request, queryset):
    queryset.update(name_status=ModerationStatus.PUBLISHED)


@admin.action(description="Hide selected names")
def hide_names(modeladmin, request, queryset):
    queryset.update(name_status=ModerationStatus.HIDDEN)


@admin.action(description="Publish selected messages")
def publish_messages(modeladmin, request, queryset):
    queryset.update(status=ModerationStatus.PUBLISHED)


@admin.action(description="Hide selected messages")
def hide_messages(modeladmin, request, queryset):
    queryset.update(status=ModerationStatus.HIDDEN)


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    fields = ("recipient", "text", "status", "created_at")
    readonly_fields = ("created_at",)


@admin.register(Signature)
class SignatureAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "name_status", "anonymous", "newsletter", "created_at")
    list_filter = ("name_status", "anonymous", "newsletter", "created_at")
    search_fields = ("name", "email")
    readonly_fields = ("created_at", "ip_address")
    inlines = [MessageInline]
    actions = [publish_names, hide_names]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("recipient", "text", "status", "signature", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("recipient", "text")
    readonly_fields = ("created_at",)
    actions = [publish_messages, hide_messages]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && .venv/bin/pytest petition/tests/test_admin.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Run the full suite**

Run: `cd backend && .venv/bin/pytest -v`
Expected: every test across all files PASSES.

- [ ] **Step 6: Commit**

```bash
cd backend
git add -A
git commit -m "feat: add admin moderation for signatures and messages"
```

---

### Task 8: README and frontend integration notes

**Files:**
- Create: `backend/README.md`

**Interfaces:**
- Consumes: everything above. No code/tests — deliverable is documentation. Verification is `manage.py check` still passing plus presence of required sections.

- [ ] **Step 1: Write the README**

Create `backend/README.md`:

````markdown
# Petition API

Django REST API backing the "Mijič, odstopi takoj!" petition page. Serves the
public count/names/messages and captures signatures + optional public messages.
Moderation is done through the Django admin. The static `index.html` is served
separately; this API is CORS-enabled for its origin.

## Setup

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
cp .env.example .env          # edit SECRET_KEY and CORS_ALLOWED_ORIGINS
.venv/bin/python manage.py migrate
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py runserver
```

Admin/moderation: http://127.0.0.1:8000/admin/

## Configuration (.env)

| Var | Purpose |
|---|---|
| `SECRET_KEY` | Django secret. Set a long random value in production. |
| `DEBUG` | `True`/`False`. |
| `ALLOWED_HOSTS` | Comma-separated hostnames. |
| `CORS_ALLOWED_ORIGINS` | Comma-separated origins allowed to call the API (the static site's origin). |

## Endpoints

| Method | Path | Body / Result |
|---|---|---|
| `POST` | `/api/signatures/` | `{name, email, newsletter?, anonymous?, consent, message?: {recipient, text}}` → `201 {"status":"ok"}`. Duplicate email returns the same success silently. |
| `GET` | `/api/signatures/count/` | `{"count": N}` |
| `GET` | `/api/signatures/` | Paginated public names `{results: [{name, created_at}], ...}` (excludes anonymous + non-published). |
| `GET` | `/api/messages/` | Paginated published messages `{results: [{recipient, text, created_at}], ...}`. |

## Moderation

Post-moderation: content is public immediately unless `petition/moderation.py`
`screen()` flags it (default: any URL) — flagged items become `pending` and are
withheld until approved in admin. Use the admin list filters and the
publish/hide bulk actions. Deleting a signature removes it from the count and
cascades its message.

## Production notes

Run `.venv/bin/python manage.py collectstatic` before serving admin behind
gunicorn; WhiteNoise serves the collected admin static files.

## Frontend integration

Replace the `localStorage` stubs in `../index.html` (marked with `TODO`) with
`fetch()` calls to this API. Set a base URL, e.g.
`const API = "http://127.0.0.1:8000/api";`.

- **Load count** — replaces `loadSignatureCount()` / `SEED_COUNT`:

  ```js
  const { count } = await (await fetch(`${API}/signatures/count/`)).json();
  ```

- **Submit signature (+ optional message)** — replaces `saveSignature()` /
  `saveComment()` in the form submit handler:

  ```js
  await fetch(`${API}/signatures/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name, email,
      newsletter: document.getElementById("consentNewsletter").checked,
      anonymous: document.getElementById("signAnonymous").checked,
      consent: document.getElementById("consentRequired").checked,
      message: text ? { recipient, text } : undefined,
    }),
  });
  ```

- **Load messages** — replaces `loadComments()` in `renderComments()`:

  ```js
  const { results } = await (await fetch(`${API}/messages/`)).json();
  // each: { recipient, text, created_at }  — render created_at as the time
  ```

- **Public names (optional new section)**:

  ```js
  const { results } = await (await fetch(`${API}/signatures/`)).json();
  // each: { name, created_at }
  ```
````

- [ ] **Step 2: Verify the project still checks**

Run: `cd backend && .venv/bin/python manage.py check && .venv/bin/pytest -q`
Expected: no issues; all tests pass.

- [ ] **Step 3: Commit**

```bash
cd backend
git add -A
git commit -m "docs: add backend README and frontend integration notes"
```

---

## Self-Review Notes

- **Spec coverage:** models (T2), `screen()` (T3), submit + silent dedupe + count + names list (T5), messages (T6), admin moderation (T7), CORS/throttle/env (T1), README + frontend notes (T8). All spec sections mapped.
- **Statuses** consistent as `published`/`pending`/`hidden` via `ModerationStatus` across models, views, admin, tests.
- **Signature always counts:** `SignatureCountView` counts all rows; status only filters the public names list.
- **Silent dedupe** verified by `test_duplicate_email_is_silent_noop` (also asserts no stray message).
- No placeholders; every code step contains full content.
