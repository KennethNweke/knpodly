# Administrator Guide

Administrators have full system access on top of everything Lecturers can do.

## Responsibilities

- System-wide configuration (`.env`, `docker-compose.prod.yml`)
- Managing storage (VMImages, overlays, Postgres volume growth)
- Monitoring host health (CPU/RAM/disk — Lecturer Dashboard, `/admin/host-stats`)
- Reviewing logs and the audit trail (`/admin/audit-logs`)
- Managing platform updates (`scripts/upgrade.sh`)
- Creating the first Lecturer accounts (Lecturers can then create Students)

## Creating additional admins

Only an existing admin can create another admin account (enforced in
`app/api/v1/routers/users.py`):

```
POST /api/v1/users
{ "username": "...", "full_name": "...", "password": "...", "role": "admin" }
```

## Storage management

- `VMImages/` — master images, grows only when you add new distros
- `overlays/` (VM_OVERLAY_PATH) — should stay near-empty; overlays are
  deleted on VM shutdown. Large or growing overlay storage usually indicates
  the scheduler's expiry/idle sweep isn't running — check the `scheduler`
  container logs.
- Postgres volume — grows with audit logs and session history over time;
  consider a retention/archival policy for `audit_logs` and `system_logs`
  once you have long production history.

## Monitoring host health

`GET /api/v1/admin/host-stats` (also rendered on the Lecturer Dashboard)
reports live CPU/RAM figures from libvirt plus running/queued VM counts.
For OS-level monitoring (disk usage, container health), standard tools like
`docker compose ps`, `df -h`, and `journalctl -u knpodly` work alongside the
app's own dashboard.

## Maintenance mode

`POST /api/v1/admin/maintenance/enable` with a message broadcasts a
maintenance banner to connected dashboards (via `/ws/dashboard`) and should
be used before planned upgrades or host reboots. Disable with
`POST /api/v1/admin/maintenance/disable`.
