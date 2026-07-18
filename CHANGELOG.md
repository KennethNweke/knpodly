# Changelog

All notable changes to this project are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
- Initial production scaffold: FastAPI backend, React/TS/Tailwind frontend,
  KVM/libvirt VM lifecycle, QCOW2 overlay management, automatic OS catalogue
  discovery, RBAC (admin/lecturer/student), audit logging.
- Worker queue (arq) wiring for VM provisioning/teardown; scheduler process
  implementing session expiry and idle-timeout detection against a
  lecturer-configurable `VMLimitPolicy`.
- Redis pub/sub dashboard event bus (`/ws/dashboard`) for real-time host
  stats, VM state changes, and maintenance-mode broadcasts across replicas.
- Console access: TCP↔WebSocket relay (`/console/{token}`) bridging noVNC
  clients to QEMU's VNC socket, with a real `@novnc/novnc` RFB client on the
  frontend.
- Persisted maintenance mode and VM limit policy, editable from the Lecturer
  Dashboard; student launches are blocked while maintenance is active.
- Redis-backed VNC port allocation and login rate limiting (fixes races/abuse
  under multi-replica deployment).
- OS image/icon upload endpoints (`/operating-systems/{slug}/upload-image`,
  `.../upload-icon`) with streamed, size-capped writes.
- Full Ubuntu Server install guide, architecture doc, API reference, and
  role-specific guides (admin/lecturer/student).
- Frontend polish: toast notifications, confirmation dialogs on destructive
  actions, loading skeletons, catalogue search/filter, expiry/idle warning
  banners, maintenance banner — all driven by the live dashboard socket.
- Integration test suite exercising the full launch→provision→extend→stop
  flow against a real (disposable) Postgres and the fake libvirt driver.
- CI: backend lint/type-check/test + frontend lint/build + Docker image
  build, all on GitHub Actions.

### Known gaps (tracked for follow-up)
- No LDAP/SAML/OAuth2 SSO yet (config flags exist as a seam; not implemented).
- No multi-host hypervisor cluster support (single-host `qemu:///system` only).
- No session recording or command-history capture.
- Kubernetes manifests (`k8s/`) are a minimal starting point, not
  production-hardened (no HPA, no NetworkPolicy, no PodSecurityStandards yet).
