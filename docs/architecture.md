# Knpodly Architecture

## Overview

```
                        ┌─────────────────────┐
                        │        Nginx         │  TLS termination, reverse proxy
                        └──────────┬───────────┘
                 ┌──────────────────┼───────────────────┐
                 ▼                  ▼                    ▼
        ┌────────────────┐ ┌───────────────┐   ┌──────────────────┐
        │ React Frontend │ │ FastAPI Backend│   │  noVNC / WS proxy │
        │ (static, SPA)  │ │  REST + WS API │   │  (via backend)    │
        └────────────────┘ └───────┬────────┘   └──────────────────┘
                                    │
                    ┌───────────────┼────────────────┐
                    ▼               ▼                ▼
             ┌────────────┐  ┌────────────┐   ┌──────────────┐
             │ PostgreSQL │  │   Redis    │   │  vm-worker(s) │
             │  (state,   │  │ (task queue,│  │  (arq jobs:   │
             │  audit)    │  │  pub/sub)  │   │  provision/   │
             └────────────┘  └────────────┘   │  teardown VM) │
                                               └───────┬───────┘
                                                        ▼
                                              ┌───────────────────┐
                                              │   libvirt / KVM    │
                                              │   (host hypervisor)│
                                              └─────────┬──────────┘
                                                         ▼
                                       QCOW2 overlay (per session) <- base.qcow2 (immutable)
```

## Why a task queue between the API and libvirt?

Provisioning a VM (creating a QCOW2 overlay, defining and starting a libvirt
domain) takes real wall-clock time and should never block an HTTP request
thread. `POST /api/v1/vms` returns `202 Accepted` immediately with a
`queued` session row; the `vm-worker` container picks the job up from Redis
via `arq` and drives it through `provisioning -> running`. This also gives a
natural place to enforce fair queuing under load (`max_jobs` in
`WorkerSettings`) and is the seam that will support routing jobs to specific
hosts once multi-host clusters are supported.

## VM lifecycle state machine

```
queued -> provisioning -> running -> stopping -> stopped
                                   -> stopping -> expired   (auto, past expires_at)
             \-> failed (provisioning error)
running -> destroyed (after overlay cleanup + libvirt undefine)
```

## Security boundaries

- Students never get shell/API access to the Docker host, libvirt socket, or
  hypervisor — only a VNC framebuffer stream via noVNC, proxied through the
  backend's console websocket endpoint with a per-session token.
- Domain XML (`app/services/domain_xml.py`) intentionally omits `<filesystem>`
  (virtfs/shared folders), `<hostdev>` USB passthrough, and SPICE
  clipboard/agent channels.
- Every VM's disk is a QCOW2 **overlay**; the backend process never opens
  `base.qcow2` for writing. Overlay files live under `VM_OVERLAY_PATH` and
  are deleted on shutdown by `overlay_manager.destroy_overlay`.
- The lab network (`knpodly-labnet` bridge) is isolated from the host's other
  networks via nftables rules (see `scripts/create-bridge.sh`); internet
  egress is a per-lab, lecturer-configurable policy, not an always-on route
  to the host.

## Idle detection

The frontend's `useVMActivityHeartbeat` hook posts to
`/api/v1/vms/{id}/activity` on keyboard/mouse/focus events (debounced to
30s), which updates `last_activity_at`. The `scheduler` container polls
running sessions and stops any whose `last_activity_at` is older than
`IDLE_TIMEOUT_MINUTES`, issuing a warning event first at
`IDLE_WARNING_MINUTES`.

## Automatic image discovery

`app/services/image_discovery.py` scans `VMImages/<slug>/metadata.json` and
upserts rows into `operating_systems`. It runs once on backend startup and
continuously in the `scheduler` container via a `watchdog` filesystem
observer — new directories appear in the catalogue without restarting
anything, as required by the spec.

## Future-proofing seams already in the code

| Future feature                  | Where the seam lives                                   |
|----------------------------------|----------------------------------------------------------|
| Multi-host clusters / load balancing | `BaseLibvirtClient` — swap for a connection pool keyed by host |
| VM templates / preconfigured labs | `operating_systems` table + `metadata.json` schema is already the template mechanism |
| Session recording                | Extend `vm_sessions` + add a recording proxy in the console websocket path |
| LDAP/SAML/OAuth2 SSO             | `AUTH_LDAP_ENABLED` / `AUTH_OAUTH2_ENABLED` / `AUTH_SAML_ENABLED` flags in config; `app/core/security.py` issues the same internal JWT regardless of upstream auth method |
| Usage analytics / LMS integration | `audit_logs` + `vm_sessions` already capture the raw events; add a reporting API on top |
