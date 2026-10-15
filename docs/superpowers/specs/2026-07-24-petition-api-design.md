# Petition API — Design

**Date:** 2026-07-24
**Status:** Approved

## Context

`index.html` is a static Slovenian petition landing page ("Mijič, odstopi
takoj!"). It lets visitors sign (name, email), opt into a newsletter, sign
anonymously, and optionally attach a public message addressed to a chosen
recipient. Today the count, signatures, and messages live only in the
browser's `localStorage` (see the `TODO` markers in the page's script). This
project builds a real backend API to replace those stubs.

The frontend is served separately and is owned by the front-end team. This
project delivers an **API-only** backend plus a moderation surface. It does not
modify `index.html`; instead it documents the exact `fetch()` changes the
front-end team will make.

## Goals

- Persist signatures (with the required data-processing consent, optional
  newsletter opt-in, and optional anonymity).
- Persist optional public messages attached to a signature.
- Expose public read endpoints: signature count, recent public signer names,
  and published messages.
- Provide a moderation surface to review/hide/approve names and messages and to
  delete fake/spam signatures.
- Post-moderation by default, with a pluggable auto-hold hook that can flag
  suspicious names/messages for review before they go public.

## Non-goals

- Email verification / double opt-in (emails are trusted as submitted).
- Custom moderation UI (Django admin is used).
- Frontend changes (documented, not implemented here).
- Newsletter delivery/integration (only capturing the opt-in flag).

## Stack

- **Django + Django REST Framework**, **SQLite** file database.
- `django-cors-headers` for CORS (API is a separate origin from the static
  site).
- **WhiteNoise** so `/admin/` static assets serve without a separate web
  server.
- Config via environment variables (`SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`,
  `CORS_ALLOWED_ORIGINS`) with a committed `.env.example`.
- Single Django app: `petition`.

Rationale: Django admin provides the moderation UI essentially for free; DRF
gives clean validation and consistent error shapes for little code. SQLite
keeps deployment to a single file with trivial backups.

## Data model

### Signature

| Field | Type | Notes |
|---|---|---|
| `name` | char | Required. |
| `email` | email | Required, **unique**. |
| `newsletter` | bool | Newsletter opt-in. Default false. |
| `anonymous` | bool | If true, name never appears in the public names list. Default false. |
| `consent` | bool | Data-processing consent. Must be true to submit. |
| `name_status` | enum | `published` / `pending` / `hidden`. Gates public display of the name only. |
| `ip_address` | genericIP | Nullable. Captured for abuse review. |
| `created_at` | datetime | Auto. |

- A signature **always counts** toward the total regardless of `name_status`
  (status gates only public name display). Only deletion removes it from the
  count.
- Anonymous signatures never appear in the public names list, whatever the
  `name_status`.

### Message

| Field | Type | Notes |
|---|---|---|
| `signature` | FK → Signature | Created together in the same submission. |
| `recipient` | char | Free text — a preset name or a custom one. |
| `text` | char/text | Required for a message, max 500 chars. |
| `status` | enum | `published` / `pending` / `hidden`. |
| `created_at` | datetime | Auto. |

## The `screen()` scaffold

A single pluggable function `screen(text) -> bool` returning whether the text is
flagged. On submission it runs against the signer's name and the message text:

- Name flagged → signature `name_status = pending` (name withheld from the
  public list until a moderator approves).
- Message flagged → message `status = pending` (withheld from public until
  approved).
- Not flagged → `published` immediately (post-moderation default).

Ships as a minimal keyword/heuristic stub with a clear extension point. This is
the intended hook for tightening moderation later without touching endpoint or
model code.

## Endpoints (all under `/api/`)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/signatures/` | Submit. Body: `{name, email, newsletter, anonymous, consent, message?: {recipient, text}}`. Runs `screen()`. **Silent dedupe.** |
| `GET` | `/api/signatures/count/` | `{ "count": N }` — all non-deleted signatures. |
| `GET` | `/api/signatures/` | Recent public names: `[{name, created_at}]`. Excludes anonymous and non-`published`. Paginated/limited, newest first. |
| `GET` | `/api/messages/` | `[{recipient, text, created_at}]` — `published` only, newest first. Paginated. |

### POST /api/signatures/ behavior

- Validates: `name` non-empty, `email` valid, `consent` true, and if a message
  is present, `text` non-empty and ≤ 500 chars with a `recipient`.
- Runs `screen()` on name and message text; sets statuses accordingly.
- **Silent dedupe:** if the email already exists, respond with success (same
  shape as a fresh create) **without** creating a new row and **without**
  revealing that the email already signed. No new message is stored in that
  case (a repeat submit is treated as a no-op).
- Captures `ip_address` from the request.
- Response body does not echo personal data beyond what's needed for the
  frontend "thank you" state.

## Moderation

- Django **admin** at `/admin/`, superuser login. No custom UI.
- Signatures list filterable by `name_status`, `anonymous`, `newsletter`,
  `created_at`; searchable by name/email. Bulk admin **actions** to set
  `published` / `hidden`. Deleting a signature removes it from the count (for
  fakes/spam) and cascades its message.
- Messages shown **inline** under their signature and also as a top-level list
  filterable by `status`, with bulk approve/hide actions.

## Errors & validation

- Missing/invalid `name`/`email`, `consent` not true, message `text` > 500, or
  message without `recipient` → `400` with field-level errors.
- Duplicate email → **silent success** (the single exception to normal error
  reporting).
- CORS restricted to the static site's origin plus `localhost` for dev, via
  `CORS_ALLOWED_ORIGINS`.
- Light DRF throttling on `POST /api/signatures/` to blunt spam/double-submits;
  easy to tune or remove.

## Testing (TDD)

pytest-django covering:

- Submit creates a signature; submit with a message creates the linked message.
- Silent dedupe: second submit with same email returns success, creates no new
  signature, stores no new message.
- `GET count` reflects created signatures.
- `GET signatures` excludes anonymous and non-`published` names; newest first.
- `GET messages` returns only `published`, newest first.
- `screen()` flags → name/message held as `pending` and absent from public
  endpoints.
- Validation: missing name/email, consent false, over-long message → 400.
- Admin requires authentication.

## Deliverables

- Django project + `petition` app.
- `requirements.txt`, `.env.example`.
- README: run instructions, `createsuperuser`, CORS/env config, and the exact
  `fetch()` changes the front-end team makes in `index.html` to replace the
  `localStorage` TODOs (submit signature, submit message, load count, load
  signatures, load messages).

## Frontend integration notes (documentation only)

The page's current stubs map to endpoints as follows:

- `loadSignatureCount()` → `GET /api/signatures/count/`.
- `saveSignature()` (submit) → `POST /api/signatures/` with
  `{name, email, newsletter, anonymous, consent, message?}`.
- `saveComment()` → folded into the same `POST` as the optional `message`.
- `renderComments()` source → `GET /api/messages/`.
- New public names section (optional for the frontend) → `GET /api/signatures/`.

`SEED_COUNT` (currently 842) is dropped once the real count endpoint is wired.
