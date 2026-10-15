# Design: Kubernetes deployment for mijič-sramota

**Date:** 2026-07-24
**Status:** Approved

## Goal

Deploy the petition project to the DJND Kubernetes cluster as two pods:

- a **static pod** serving `index.html` + `public/` assets, and
- an **API pod** running the Django/DRF backend in `backend/`.

Follow existing DJND conventions from the reference repos
`danesjenovdan/snakes-and-ladders` (static site) and `danesjenovdan/krtk@k8s`
(Python app): multi-stage Docker builds, a `kustomize/` overlay, traefik
ingress with cert-manager `letsencrypt-production` TLS, images in the Scaleway
registry `rg.fr-par.scw.cloud/djnd/`.

## Decisions

| Decision | Value |
|---|---|
| Static site host | `mijic.djnd.si` |
| API host | `api.mijic.djnd.si` (called cross-origin from the site) |
| CI/CD | None — Dockerfiles + kustomize manifests only; image build/push handled manually |
| Static image | `rg.fr-par.scw.cloud/djnd/mijic-sramota` |
| API image | `rg.fr-par.scw.cloud/djnd/mijic-sramota-api` |
| Namespace | `mijic-sramota` |
| DB | SQLite on a PersistentVolumeClaim |

## Repo layout

```
Dockerfile              # static site: nginx:alpine serving index.html + public/
nginx.conf
.dockerignore
backend/Dockerfile      # Django API: python:3.13-slim + gunicorn
backend/.dockerignore
kustomize/
  kustomization.yaml    # namespace: mijic-sramota; 2 images; lists all resources
  static-deployment.yaml
  static-service.yaml
  static-ingress.yaml
  api-deployment.yaml
  api-service.yaml
  api-ingress.yaml
  api-pvc.yaml
  secrets.example.yaml
```

Two build contexts: the root `Dockerfile` builds the static image (context =
repo root, copying only `index.html` + `public/`); `backend/Dockerfile` builds
the API image (context = `backend/`).

## Static pod

No build step — the site is plain HTML with static assets.

- **Dockerfile:** `FROM nginx:alpine`; copy `index.html` and `public/` into
  `/usr/share/nginx/html`; copy `nginx.conf` to
  `/etc/nginx/conf.d/default.conf`.
- **nginx.conf:** minimal `server { listen 80; location / { root
  /usr/share/nginx/html; index index.html; try_files $uri $uri/ =404; } }`.
- **Deployment:** `replicas: 1`, container port 80.
- **Service:** port 80 → targetPort 80.
- **Ingress:** host `mijic.djnd.si`, `ingressClassName: traefik`,
  `cert-manager.io/cluster-issuer: letsencrypt-production`, TLS secret
  `mijic-sramota-tls`.

## API pod

- **Dockerfile (multi-stage, `python:3.13-slim-bookworm`):**
  - Install `requirements.txt` (which now includes `gunicorn`).
  - No system build packages required — SQLite needs no `libpq`/compiler.
  - Run `python manage.py collectstatic --noinput` at build time so whitenoise
    can serve the Django admin CSS/JS (no static volume needed).
  - Create and switch to a non-root user; `EXPOSE 8000`;
    `ENV PYTHONUNBUFFERED=1`.
  - `CMD gunicorn config.wsgi:application -b 0.0.0.0:8000`.
- **Service:** port 8000 → targetPort 8000.
- **Ingress:** host `api.mijic.djnd.si`, traefik + cert-manager TLS secret
  `mijic-sramota-api-tls`.
- **Deployment:**
  - `replicas: 1`, `strategy: { type: Recreate }` (RWO volume + single-writer
    SQLite: never run two pods against the same DB, even mid-rollout).
  - `securityContext.fsGroup: 1000` so the non-root user can write the mounted
    volume.
  - `initContainer` `migrate`: same image, `command: [python, manage.py,
    migrate]`, `envFrom` the secret, mounts the PVC.
  - Main container: `envFrom` the secret, mounts the PVC at `/app/data`.

## SQLite persistence

- **PVC** `api-data`: `ReadWriteOnce`, 1Gi.
- **Settings change:** make the DB path env-driven in
  `backend/config/settings.py`:

  ```python
  "NAME": os.getenv("SQLITE_PATH", BASE_DIR / "db.sqlite3"),
  ```

  Default preserves current local behaviour; in k8s set
  `SQLITE_PATH=/app/data/db.sqlite3`.
- Mount the PVC at `/app/data` (mounting at `/app` would clobber the app code).
  Both the `migrate` initContainer and the app container mount it, so migrations
  and requests hit the same persisted file.

## Config & secrets

A `Secret` named `mijic-sramota-api-secrets`, consumed via `envFrom`:

| Key | Value |
|---|---|
| `SECRET_KEY` | long random string (real value only in-cluster) |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `api.mijic.djnd.si` |
| `CORS_ALLOWED_ORIGINS` | `https://mijic.djnd.si` |
| `USE_X_FORWARDED_FOR` | `True` |
| `SQLITE_PATH` | `/app/data/db.sqlite3` |

`secrets.example.yaml` (placeholders) is committed; the real secret is applied
out-of-band and never committed. Settings already enables
`SECURE_PROXY_SSL_HEADER`, HSTS, and secure-cookie flags when `DEBUG=False`;
traefik terminates TLS and forwards `X-Forwarded-Proto=https`, so
`SECURE_SSL_REDIRECT` does not loop.

## Frontend change

Set the `API` constant in `index.html` from the localhost dev value to the
production origin:

```js
var API = "https://api.mijic.djnd.si/api";
```

Hardcoded (no dev hostname fallback — YAGNI for a single-page static deploy).

## Changes to existing files

- `backend/config/settings.py` — env-driven `SQLITE_PATH`.
- `backend/requirements.txt` — add `gunicorn`.
- `index.html` — production `API` URL.

## Manual / out-of-scope steps (documented, not automated)

- **Superuser:** after the first deploy, create the admin/moderation user via
  `kubectl exec <api-pod> -- python manage.py createsuperuser`.
- **Image build/push:** built and pushed manually (no GitHub Actions), tagged
  under `rg.fr-par.scw.cloud/djnd/`.
- **DNS:** `mijic.djnd.si` and `api.mijic.djnd.si` A/CNAME records point at the
  cluster ingress.

## Verification

- `docker build` both images locally and confirm they start.
- Run the API image with a throwaway `/app/data` volume and env matching the
  secret; confirm `migrate` succeeds, gunicorn serves, and
  `GET /api/signatures/count/` returns `{"count": ...}`.
- `kubectl kustomize kustomize/` (or `kustomize build kustomize/`) renders all
  manifests without error.
- Post-deploy smoke test: site loads over HTTPS at `mijic.djnd.si`; a signature
  POST from the site to `api.mijic.djnd.si` succeeds (CORS allowed) and the
  counter increments.
