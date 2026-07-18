# Installing Knpodly on a Bare Ubuntu Server

This guide takes you from a fresh Ubuntu Server 22.04 or 24.04 install to a
running Knpodly platform. Follow it in order — later steps assume earlier
ones are complete.

**Minimum recommended hardware** (adjust upward for more concurrent VMs):
- CPU with VT-x/AMD-V, 8+ cores
- 32 GB+ RAM (each default student VM uses ~2 GB; plan capacity accordingly)
- SSD storage, 200 GB+ (base images + overlays + Postgres)
- A public IP / DNS name if exposing this beyond your campus LAN

---

## 1. Base OS setup

```bash
sudo apt-get update && sudo apt-get -y upgrade
sudo apt-get install -y curl git ufw
sudo timedatectl set-timezone <Your/Timezone>
sudo timedatectl set-timezone Europe/London

```

Create a non-root deploy user if you're currently on root-only access:

```bash
sudo adduser knpodly-admin
sudo usermod -aG sudo knpodly-admin
su - knpodly-admin
```

## 2. Firewall

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

Only 22 (SSH), 80, and 443 need to be open externally. Postgres, Redis, and
the backend's internal port are only reachable from inside the Docker
network / localhost, never exposed directly.

## 3. Clone the repository

```bash
sudo mkdir -p /srv/knpodly
sudo chown "$USER":"$USER" /srv/knpodly
git clone https://github.com/<your-org>/knpodly.git /srv/knpodly
cd /srv/knpodly
```

## 4. Install KVM, libvirt, and Docker

Run the provided setup script (installs qemu-kvm, libvirt, bridge-utils,
Docker Engine, and creates `/srv/knpodly/{VMImages,VMIcons,overlays}`):

```bash
sudo bash scripts/setup-host.sh
```

Log out and back in (or `newgrp libvirt`) afterward so your group membership
(`libvirt`, `kvm`, `docker`) takes effect. Verify:

```bash
virsh list --all
docker run hello-world
```

The script prints the `libvirt` group's GID at the end — note it down, you
will set it as `LIBVIRT_GID` in `.env` in step 6.

## 5. Create the isolated lab network

```bash
sudo bash scripts/create-bridge.sh
```

This defines the `knpodly-labnet` libvirt network (bridge `knpodly-br0`,
subnet `192.168.100.0/24`) that every student VM joins, and applies nftables
rules preventing that subnet from reaching the host's other networks.

## 6. Configure environment

```bash
cp .env.example .env
nano .env
```

At minimum, set:
- `JWT_SECRET_KEY` — generate with `openssl rand -hex 32`
- `POSTGRES_PASSWORD` — a strong password
- `DATABASE_URL` — update the password to match
- `APP_URL` / `VITE_API_BASE_URL` / `VITE_WS_BASE_URL` — your real domain
- `LIBVIRT_DRIVER=qemu` (production; `fake` is dev-only)
- `LIBVIRT_GID` — the GID printed by `setup-host.sh`

## 7. Add your first VM images

```bash
# Example for Ubuntu — repeat per distro:
cd /srv/knpodly/VMImages/ubuntu-24.04
qemu-img create -f qcow2 base.qcow2 20G
sudo virt-install --name ubuntu-builder --memory 2048 --vcpus 2 \
  --disk base.qcow2 --cdrom /path/to/ubuntu-24.04-live-server-amd64.iso \
  --network network=knpodly-labnet --graphics vnc --os-variant ubuntu24.04
# Complete the OS install through the VNC console, shut the VM down cleanly,
# then undefine the temporary installer domain (the disk stays as your
# read-only base image):
virsh undefine ubuntu-builder
```

`metadata.json` for this distro is already provided under
`VMImages/ubuntu-24.04/`; adjust it to taste. See `VMImages/README.md` for
the full schema and repeat this process for each distro you want to offer.

## 8. Configure DNS and get a TLS certificate

Point your domain's A record at this server's public IP, then edit
`infra/nginx/conf.d/knpodly.conf` to replace `labs.example.edu` with your
real domain. Bring the stack up once first so certbot's webroot path exists:

```bash
docker compose -f docker-compose.prod.yml --env-file .env up -d nginx
sudo docker compose -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot -w /var/www/certbot -d labs.example.edu
docker compose -f docker-compose.prod.yml restart nginx
```

The `certbot` service in `docker-compose.prod.yml` handles automatic
renewal going forward.

## 9. Start the full stack

```bash
docker compose -f docker-compose.prod.yml --env-file .env up -d
docker compose -f docker-compose.prod.yml ps
```

Run database migrations (first boot only creates the schema via
`infra/postgres/init/`; use Alembic for anything after that):

```bash
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

## 10. Create your first admin account

```bash
docker compose -f docker-compose.prod.yml exec backend \
  python /app/../scripts/create-admin.py --username admin --full-name "Site Administrator"
```

Note the generated password it prints, log in at `https://labs.example.edu`,
and change it immediately via account settings.

## 11. Install as a systemd service (start on boot)

```bash
sudo cp infra/systemd/knpodly.service /etc/systemd/system/
sudo cp infra/systemd/knpodly-vm-gc.service /etc/systemd/system/
sudo cp infra/systemd/knpodly-vm-gc.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now knpodly.service
sudo systemctl enable --now knpodly-vm-gc.timer
```

## 12. Backups

Add the provided backup script to cron:

```bash
( crontab -l 2>/dev/null; echo "0 3 * * * /srv/knpodly/scripts/backup.sh >> /var/log/knpodly-backup.log 2>&1" ) | crontab -
```

## Verifying the install

- `https://labs.example.edu` — frontend loads, login page appears
- `https://labs.example.edu/api/docs` — OpenAPI docs render
- Log in as admin -> catalogue shows your uploaded distros -> launch a VM as
  a test student account -> confirm the console connects and the VM is
  reachable on `192.168.100.0/24`

## Upgrading

```bash
sudo bash scripts/upgrade.sh
```

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `kvm-ok` fails | Virtualization not enabled in BIOS, or running inside a VM without nested virt |
| Backend can't reach libvirt | `LIBVIRT_GID` in `.env` doesn't match `getent group libvirt`, or `/var/run/libvirt` bind mount missing |
| VM launches but console won't connect | Check `VM_NETWORK_BRIDGE` matches the bridge from `create-bridge.sh`, and that the nginx `/console/` location proxies correctly |
| New OS doesn't appear in catalogue | Check `metadata.json` is valid JSON and `base.qcow2` exists; check `scheduler` container logs |
