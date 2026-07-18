# VMImages/

Each subdirectory here represents one entry in the OS catalogue. The backend
auto-discovers new subdirectories without a restart (see
`app/services/image_discovery.py`).

Required layout:

```
VMImages/
  <slug>/
    base.qcow2      # immutable master image — the platform NEVER writes to this file
    metadata.json    # see schema below
    splash.png       # optional; falls back to VMIcons/<slug>.{webp,svg,png,jpg}
```

## metadata.json schema

| Field            | Type   | Required | Notes                                      |
|------------------|--------|----------|---------------------------------------------|
| `name`           | string | yes      | Display name, e.g. "Ubuntu 24.04"          |
| `family`         | string | no       | e.g. Debian, RHEL, Arch                    |
| `packageManager` | string | no       | e.g. apt, dnf, pacman                      |
| `ram`            | string/number | no | e.g. "2GB" or megabytes as a number       |
| `vcpus`          | number | no       | defaults to `VM_DEFAULT_VCPUS`             |
| `architecture`   | string | no       | defaults to `x86_64`                       |
| `description`    | string | no       | shown on the catalogue card                |
| `status`         | string | no       | `Available` \| `Coming Soon` \| `Disabled` |

Note: `base.qcow2` and `splash.png` are intentionally excluded from git (see
`.gitignore`) — they're large binary artifacts that belong on the server's
disk, not in version control. `metadata.json` files ARE committed as
documentation/examples for the three sample distros included here.

## Building a base image

```bash
qemu-img create -f qcow2 VMImages/ubuntu-24.04/base.qcow2 20G
# Boot it once with an installer ISO attached, complete OS install + any
# baseline packages/hardening, shut down cleanly, then treat it as read-only.
# The platform only ever reads this file to create per-session overlays.
```
