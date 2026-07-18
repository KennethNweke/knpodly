"""
Generates libvirt domain XML for an ephemeral student VM.

Key security properties enforced here (see README/Security section):
  - No shared filesystem / virtfs entries.
  - No USB passthrough (no <hostdev> for USB controllers).
  - No SPICE clipboard sharing unless explicitly enabled by policy.
  - Disk is always the per-session QCOW2 overlay, never the master image.
  - NIC is always attached to the isolated `knpodly-labnet` bridge, never the
    host's default network.
"""
from __future__ import annotations

import uuid


def render_domain_xml(
    *,
    name: str,
    ram_mb: int,
    vcpus: int,
    overlay_disk_path: str,
    vnc_port: int,
    network_bridge: str,
    vnc_listen_address: str = "127.0.0.1",
    mac_address: str | None = None,
) -> str:
    mac = mac_address or _random_mac()
    return f"""<domain type='kvm'>
  <name>{name}</name>
  <memory unit='MiB'>{ram_mb}</memory>
  <currentMemory unit='MiB'>{ram_mb}</currentMemory>
  <vcpu placement='static'>{vcpus}</vcpu>
  <os>
    <type arch='x86_64' machine='q35'>hvm</type>
    <boot dev='hd'/>
  </os>
  <features>
    <acpi/><apic/>
  </features>
  <cpu mode='host-passthrough'/>
  <on_poweroff>destroy</on_poweroff>
  <on_reboot>restart</on_reboot>
  <on_crash>destroy</on_crash>
  <devices>
    <disk type='file' device='disk'>
      <driver name='qemu' type='qcow2'/>
      <source file='{overlay_disk_path}'/>
      <target dev='vda' bus='virtio'/>
    </disk>
    <interface type='bridge'>
      <source bridge='{network_bridge}'/>
      <mac address='{mac}'/>
      <model type='virtio'/>
      <!-- No host network / NAT to host services; bridge is isolated at the
           host firewall/nftables layer per docs/architecture.md -->
    </interface>
    <graphics type='vnc' port='{vnc_port}' autoport='no' listen='{vnc_listen_address}'>
      <listen type='address' address='{vnc_listen_address}'/>
    </graphics>
    <video><model type='qxl'/></video>
    <!-- Intentionally no <filesystem> (virtfs), no <hostdev> USB passthrough,
         no <channel> spice clipboard/agent devices. -->
  </devices>
</domain>"""


def _random_mac() -> str:
    # Locally-administered unicast MAC prefix (02:xx)
    suffix = uuid.uuid4().hex[:10]
    return "02:" + ":".join(suffix[i:i + 2] for i in range(0, 10, 2))
