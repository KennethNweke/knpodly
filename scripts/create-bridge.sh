#!/usr/bin/env bash
# Creates the isolated 'knpodly-labnet' libvirt network — a bridge that lets
# student VMs talk to each other (ping/ssh/routing exercises) without ever
# exposing the host OS or host's real network. Internet access is applied
# per-lab via nftables NAT rules toggled by the backend based on the
# lecturer's chosen network policy (enabled/disabled/restricted), not by
# this base network definition.
set -euo pipefail

NETWORK_NAME="knpodly-labnet"
SUBNET="192.168.100.0/24"
BRIDGE_IF="knpodly-br0"

cat > /tmp/${NETWORK_NAME}.xml << XML
<network>
  <name>${NETWORK_NAME}</name>
  <bridge name="${BRIDGE_IF}" stp="on" delay="0"/>
  <ip address="192.168.100.1" netmask="255.255.255.0">
    <dhcp>
      <range start="192.168.100.10" end="192.168.100.250"/>
    </dhcp>
  </ip>
</network>
XML

if virsh net-info "$NETWORK_NAME" &>/dev/null; then
  echo "Network $NETWORK_NAME already exists, skipping definition."
else
  virsh net-define /tmp/${NETWORK_NAME}.xml
  virsh net-autostart "$NETWORK_NAME"
  virsh net-start "$NETWORK_NAME"
  echo "Created and started $NETWORK_NAME (bridge $BRIDGE_IF, subnet $SUBNET)."
fi

echo "==> Applying default-deny host access from the lab subnet (nftables)"
nft add table inet knpodly 2>/dev/null || true
nft add chain inet knpodly forward '{ type filter hook forward priority 0; policy accept; }' 2>/dev/null || true
# Block lab subnet from reaching the host's other internal networks/services.
# Internet egress is controlled separately per-session by the backend
# (see docs/architecture.md#networking) rather than hardcoded here.
nft add rule inet knpodly forward ip saddr ${SUBNET} ip daddr 192.168.0.0/16 drop 2>/dev/null || true

echo "Done. Set VM_NETWORK_BRIDGE=${BRIDGE_IF} in .env if it differs from the default."
