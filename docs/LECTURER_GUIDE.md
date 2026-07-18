# Lecturer Guide

## Managing students and lecturers

From the Lecturer Dashboard's user management area (backed by
`/api/v1/users`), you can:

- Create student and lecturer accounts
- Reset a user's password
- Disable/enable accounts
- View all students and their status

## Monitoring labs

The Lecturer Dashboard shows, live:

- Host CPU, RAM, and storage usage
- Currently running VMs and queued launches
- Active students and their session state

## Managing a running class

- **Force-stop a VM**: `POST /api/v1/vms/{id}/force-stop` — use when a
  student needs to be cut off immediately (e.g. end of exam, misuse).
- **Maintenance mode**: broadcast a warning to all students before planned
  downtime.
- **VM limits**: session duration, idle timeout, and extension policy are
  configured via the `vm_limit_policies` table (a settings UI for this is a
  natural next addition on top of the existing `VMLimitPolicy` model).

## Uploading a new OS image

1. Create `VMImages/<slug>/` on the server with `base.qcow2` and
   `metadata.json` (see `VMImages/README.md` for the schema).
2. The catalogue picks it up automatically within moments; if you want it
   immediately, call `POST /api/v1/operating-systems/rescan`.
3. Upload an icon to `VMIcons/<slug>.webp` (or place `splash.png` directly
   in the OS's own folder) if you didn't include one already.

## Networking exercises

All running VMs share the `knpodly-labnet` isolated bridge, so students can
ping, SSH, and route between each other's VMs for networking labs. Internet
access for the lab network is a policy you set per session
(`enabled`/`disabled`/`restricted`) — this never exposes the host itself.

## Audit trail

Every privileged action (VM launches, force-stops, password resets, user
disables, maintenance toggles) is recorded and viewable at
`GET /api/v1/admin/audit-logs`.
