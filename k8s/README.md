# Kubernetes manifests (optional)

Docker Compose (see `docker-compose.prod.yml` and `docs/INSTALL_UBUNTU.md`)
is the primary, fully-documented deployment path for Knpodly — a single
Ubuntu Server host with libvirt is the common case for a university lab.

These manifests are a **starting point** for teams that want to run Knpodly
on an existing Kubernetes cluster instead — most realistically with
[KubeVirt](https://kubevirt.io/) providing the actual VM runtime in place of
directly-managed libvirt, since raw libvirt/KVM access doesn't fit the pod
sandboxing model cleanly. That KubeVirt integration is **not implemented
here** — swapping `app/services/libvirt_client.py`'s `QemuLibvirtClient` for
a `KubeVirtClient` implementing the same `BaseLibvirtClient` interface is
the intended extension point (see docs/architecture.md's future-proofing
table).

What's included below covers the stateless pieces (API, frontend, workers)
assuming Postgres/Redis are either external managed services or your own
StatefulSets, and libvirt itself is reachable some other way (e.g. a
dedicated libvirt host reachable over TCP with TLS, `qemu+tls://...`).

## Contents
- `namespace.yaml`
- `configmap.yaml` — non-secret settings (mirrors `.env.example`)
- `secret.example.yaml` — template for JWT/DB secrets (do not commit real values)
- `backend-deployment.yaml`, `backend-service.yaml`
- `vm-worker-deployment.yaml`
- `scheduler-deployment.yaml`
- `frontend-deployment.yaml`, `frontend-service.yaml`
- `ingress.yaml` — TLS via cert-manager annotations (adjust to your cluster's setup)

## Usage

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
cp k8s/secret.example.yaml k8s/secret.yaml   # fill in real values, keep out of git
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/backend-deployment.yaml -f k8s/backend-service.yaml
kubectl apply -f k8s/vm-worker-deployment.yaml
kubectl apply -f k8s/scheduler-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml -f k8s/frontend-service.yaml
kubectl apply -f k8s/ingress.yaml
```

## Image tags

Build and push versioned images rather than `latest` for anything beyond
local testing:

```bash
docker build -t your-registry/knpodly-backend:v0.1.0 ./backend --target prod
docker build -t your-registry/knpodly-frontend:v0.1.0 ./frontend --target prod
docker push your-registry/knpodly-backend:v0.1.0
docker push your-registry/knpodly-frontend:v0.1.0
```

Then set that tag in `configmap.yaml`/the deployment manifests' `image:`
fields (or template them with Kustomize/Helm if you adopt one). The GitHub
Actions workflow (`.github/workflows/ci.yml`) currently only builds images
for CI validation — wire in a push step with your registry credentials and
a tag derived from `git describe`/the release tag once you're ready to
publish images.
