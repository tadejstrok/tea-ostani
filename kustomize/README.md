> **API retirement in progress, started 2026-10-15.** The petition's personal
> data is being erased per `docs/petition-erasure-runbook.md`; the API pod and
> its PVC are not yet deleted — that happens at that runbook's irreversible
> deletion step. Only the static nginx pod is deployed now: the API manifests
> remain in this directory as a record but are not in `kustomization.yaml`.
> Steps 2 and 4 below applied to the API only and are no longer used.

# Deployment — mijič-sramota

Two pods on the DJND cluster (namespace `mijic-sramota`):

- **static** — nginx serving `index.html` + `public/` at `https://mijic.djnd.si`
- **api** — Django/DRF (gunicorn) at `https://api.mijic.djnd.si`, SQLite on a PVC

There is no CI. Build and push images by hand, then apply the manifests.

## 1. Build and push images

```bash
# static site (context = repo root)
docker build -t rg.fr-par.scw.cloud/djnd/mijic-sramota:latest .
docker push rg.fr-par.scw.cloud/djnd/mijic-sramota:latest

# API (context = backend/)
docker build -t rg.fr-par.scw.cloud/djnd/mijic-sramota-api:latest backend/
docker push rg.fr-par.scw.cloud/djnd/mijic-sramota-api:latest
```

Pin real tags in `kustomization.yaml` (`images[].newTag`) instead of `latest`
for reproducible rollouts.

## 2. Create the secret (once, out of git)

Copy `secrets.example.yaml`, fill in a real `SECRET_KEY`, and apply it. It is
intentionally **not** listed in `kustomization.yaml`.

```bash
kubectl -n mijic-sramota apply -f my-secrets.yaml   # your filled-in copy
```

## 3. Apply the manifests

```bash
kubectl apply -k kustomize/
```

## 4. Create the admin/moderation user (once)

```bash
kubectl -n mijic-sramota exec -it deploy/mijic-sramota-api -- \
  python manage.py createsuperuser
```

Then moderate signatures/messages at `https://api.mijic.djnd.si/admin/`.

## Notes

- DNS: point `mijic.djnd.si` and `api.mijic.djnd.si` at the cluster ingress.
- The API runs `replicas: 1` with `strategy: Recreate` — SQLite is single-writer
  on a ReadWriteOnce volume, so the API does not scale horizontally.
- Migrations run automatically via the `migrate` init container on each rollout.
