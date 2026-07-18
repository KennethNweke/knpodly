# Knpodly

**Self-hosted educational Linux lab platform.** Lecturers and students
launch isolated, ephemeral Linux VMs directly from a web browser — no local
software, no per-student licensing, no cloud lock-in.

Built for higher-education practical teaching in Linux, networking,
operating systems, and cybersecurity.

## Highlights

- 🖥️ Browser-based Linux VMs via KVM/QEMU + libvirt + noVNC
- 🧊 Ephemeral QCOW2 overlays — master images are never modified
- 🔍 Drop a new distro folder in `VMImages/`, it appears in the catalogue automatically, no restart
- 🔐 Role-based access (Admin / Lecturer / Student) with a full audit trail
- 🌐 Isolated per-class lab network for ping/SSH/routing exercises, host never exposed
- ⏱️ Automatic session expiry, idle detection, one-time extensions
- 📊 Live lecturer dashboard: host health, running VMs, active students
- 🎨 Modern React/Tailwind UI, dark & light mode

## Quick start (development)

```bash
git clone https://github.com/<your-org>/knpodly.git
cd knpodly
cp .env.example .env   # defaults are fine for local dev (LIBVIRT_DRIVER=fake)
docker compose up -d
```

- Frontend: http://localhost:5173
- API docs: http://localhost:8000/api/docs

`LIBVIRT_DRIVER=fake` simulates VM lifecycle in-memory so you can develop
the full stack without a real hypervisor. Switch to `qemu` and follow
[`docs/INSTALL_UBUNTU.md`](docs/INSTALL_UBUNTU.md) for a real deployment.

## Production deployment

See [`docs/INSTALL_UBUNTU.md`](docs/INSTALL_UBUNTU.md) for the full,
start-to-finish guide: host prep, KVM/libvirt install, network isolation,
TLS via Let's Encrypt, systemd service, backups.

## Documentation

| Doc | Audience |
|---|---|
| [Architecture](docs/architecture.md) | Developers/maintainers |
| [Ubuntu Server Install Guide](docs/INSTALL_UBUNTU.md) | Ops/sysadmins |
| [API Reference](docs/API.md) | Integrators/developers |
| [Administrator Guide](docs/ADMIN_GUIDE.md) | Admins |
| [Lecturer Guide](docs/LECTURER_GUIDE.md) | Lecturers |
| [Student Guide](docs/STUDENT_GUIDE.md) | Students |
| [Contributing](CONTRIBUTING.md) | Contributors |

## Project structure

```
knpodly/
├── backend/            FastAPI app (REST + WebSocket API, VM lifecycle, workers)
├── frontend/            React + TypeScript + Tailwind SPA
├── VMImages/            Master OS images (base.qcow2) + metadata.json per distro
├── VMIcons/             Fallback distro icons
├── infra/                nginx, systemd units, Postgres init SQL
├── scripts/              Host setup, backup/upgrade, admin bootstrap scripts
├── docs/                  Architecture + install + role guides
├── docker-compose.yml           Development stack
└── docker-compose.prod.yml      Production stack (+ nginx, certbot)
```

## Tech stack

**Frontend:** React, TypeScript, TailwindCSS, React Query
**Backend:** FastAPI, SQLAlchemy (async), PostgreSQL, Redis, arq (task queue)
**Virtualization:** KVM/QEMU, libvirt, QCOW2 overlays, noVNC
**Deployment:** Docker Compose, Nginx, Let's Encrypt, systemd

See [`docs/architecture.md`](docs/architecture.md) for the reasoning behind
these choices and how the system is designed to scale to multi-host
clusters later without a rewrite.

## Status

This repository is a production-oriented **scaffold**: the schema, API
surface, security model (RBAC, isolated networking, ephemeral overlays),
and deployment tooling are fully defined and wired together end-to-end
(including a `fake` libvirt driver for the whole stack to run without real
hardware). Some pieces are intentionally left as clearly marked extension
points — most notably the WebSocket event broadcasting, the noVNC client
wiring, and the scheduler's expiry/idle sweep body — since finishing them
well depends on decisions (exact event schema, UI polish) best made
alongside real usage. See inline `TODO` comments throughout `backend/app`
and `frontend/src`.

## License

[MIT](LICENSE)
