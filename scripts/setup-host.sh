#!/usr/bin/env bash
# Installs KVM/QEMU/libvirt and Docker on a bare Ubuntu Server 22.04/24.04
# host, and prepares the directories Knpodly expects. Run as root (or with
# sudo). See docs/INSTALL_UBUNTU.md for the full walkthrough this script
# automates.
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Please run as root: sudo bash scripts/setup-host.sh"
  exit 1
fi

echo "==> Checking hardware virtualization support"
if ! egrep -q '(vmx|svm)' /proc/cpuinfo; then
  echo "ERROR: CPU does not report vmx/svm virtualization flags. Enable"
  echo "  virtualization in BIOS/hypervisor settings (nested virt if this"
  echo "  is itself a VM) before continuing."
  exit 1
fi

echo "==> Installing KVM/QEMU/libvirt"
apt-get update
apt-get install -y \
  qemu-kvm libvirt-daemon-system libvirt-clients bridge-utils virtinst \
  qemu-utils cpu-checker nftables

echo "==> Verifying KVM acceleration"
kvm-ok || { echo "kvm-ok failed — virtualization not usable on this host."; exit 1; }

echo "==> Installing Docker Engine + Compose plugin"
if ! command -v docker &>/dev/null; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
    $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
    tee /etc/apt/sources.list.d/docker.list > /dev/null
  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

echo "==> Enabling and starting libvirtd + docker"
systemctl enable --now libvirtd
systemctl enable --now docker

echo "==> Creating application directories"
mkdir -p /srv/knpodly/VMImages /srv/knpodly/VMIcons /srv/knpodly/overlays
chown -R "${SUDO_USER:-root}":libvirt /srv/knpodly

echo "==> Adding deploying user to libvirt and docker groups"
if [[ -n "${SUDO_USER:-}" ]]; then
  usermod -aG libvirt,kvm,docker "$SUDO_USER"
  echo "NOTE: log out/in (or run 'newgrp libvirt') for group membership to take effect."
fi

echo "==> Reporting libvirt group GID (needed for LIBVIRT_GID in .env)"
getent group libvirt | cut -d: -f3

echo "==> Done. Next: run scripts/create-bridge.sh, then follow docs/INSTALL_UBUNTU.md"
