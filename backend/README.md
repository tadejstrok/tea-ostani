> **RETIREMENT IN PROGRESS, started 2026-10-15.** The petition closed, and the
> site now reads static JSON written by `freeze_petition` instead of this API.
> `kustomize/kustomization.yaml` no longer references it, but its deployment
> and PVC have not been deleted yet, and `api.mijic.djnd.si` still resolves —
> that happens at the irreversible deletion step of
> `docs/petition-erasure-runbook.md`. See
> `docs/superpowers/specs/2026-10-15-petition-pii-erasure-design.md` for the
> full erasure design.
>
> The code is kept deliberately: it is the record of what was collected and how
> it will be destroyed. Do not redeploy it.

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
