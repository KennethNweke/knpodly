"""
Thin abstraction over libvirt so the rest of the codebase never touches the
libvirt SDK directly. This gives us:

  1. A single seam to swap in a multi-host connection pool later
     (Future Feature: multi-host hypervisor clusters / load balancing) —
     `LibvirtClient` can become `LibvirtClientPool` without touching callers.
  2. A `fake` driver (LIBVIRT_DRIVER=fake) that simulates domain lifecycle
     in-memory, so the API/worker/tests can run with zero real virtualization
     for local development and CI.

Real provisioning (domain XML generation, overlay creation via qemu-img,
network attachment) lives in app/services/vm_lifecycle.py, which calls into
this client for the actual libvirt calls.
"""
from __future__ import annotations

import abc
import uuid
from dataclasses import dataclass, field

from app.core.config import get_settings

settings = get_settings()


@dataclass
class DomainInfo:
    name: str
    state: str  # running | shutoff | paused | crashed
    vnc_port: int | None = None


class BaseLibvirtClient(abc.ABC):
    @abc.abstractmethod
    async def define_and_start(self, domain_xml: str, name: str) -> DomainInfo: ...

    @abc.abstractmethod
    async def graceful_shutdown(self, name: str) -> None: ...

    @abc.abstractmethod
    async def force_destroy(self, name: str) -> None: ...

    @abc.abstractmethod
    async def get_domain_info(self, name: str) -> DomainInfo | None: ...

    @abc.abstractmethod
    async def undefine(self, name: str) -> None: ...

    @abc.abstractmethod
    async def host_stats(self) -> dict: ...


class QemuLibvirtClient(BaseLibvirtClient):
    """Real driver: talks to libvirtd over the configured URI (qemu:///system)."""

    def __init__(self, uri: str):
        self._uri = uri
        self._conn = None  # lazily opened; libvirt-python calls are blocking,
        # so in a real implementation these methods run via
        # `asyncio.to_thread` to avoid blocking the event loop.

    def _connect(self):
        import libvirt  # imported lazily; not installed/needed for `fake` driver

        if self._conn is None:
            self._conn = libvirt.open(self._uri)
        return self._conn

    async def define_and_start(self, domain_xml: str, name: str) -> DomainInfo:
        import asyncio

        def _do():
            conn = self._connect()
            dom = conn.defineXML(domain_xml)
            dom.create()
            return DomainInfo(name=name, state="running")

        return await asyncio.to_thread(_do)

    async def graceful_shutdown(self, name: str) -> None:
        import asyncio

        def _do():
            dom = self._connect().lookupByName(name)
            dom.shutdown()

        await asyncio.to_thread(_do)

    async def force_destroy(self, name: str) -> None:
        import asyncio

        def _do():
            dom = self._connect().lookupByName(name)
            if dom.isActive():
                dom.destroy()

        await asyncio.to_thread(_do)

    async def undefine(self, name: str) -> None:
        import asyncio

        def _do():
            dom = self._connect().lookupByName(name)
            dom.undefine()

        await asyncio.to_thread(_do)

    async def get_domain_info(self, name: str) -> DomainInfo | None:
        import asyncio
        import libvirt

        def _do():
            try:
                dom = self._connect().lookupByName(name)
            except libvirt.libvirtError:
                return None
            state, _ = dom.state()
            state_map = {
                libvirt.VIR_DOMAIN_RUNNING: "running",
                libvirt.VIR_DOMAIN_SHUTOFF: "shutoff",
                libvirt.VIR_DOMAIN_PAUSED: "paused",
                libvirt.VIR_DOMAIN_CRASHED: "crashed",
            }
            return DomainInfo(name=name, state=state_map.get(state, "unknown"))

        return await asyncio.to_thread(_do)

    async def host_stats(self) -> dict:
        import asyncio

        def _do():
            conn = self._connect()
            info = conn.getInfo()  # [model, memory(MB), cpus, mhz, ...]
            return {
                "cpu_count": info[2],
                "memory_total_mb": info[1],
                "free_memory_mb": conn.getFreeMemory() // (1024 * 1024),
            }

        return await asyncio.to_thread(_do)


class FakeLibvirtClient(BaseLibvirtClient):
    """In-memory simulation used for LIBVIRT_DRIVER=fake (dev/test/CI)."""

    def __init__(self):
        self._domains: dict[str, DomainInfo] = {}

    async def define_and_start(self, domain_xml: str, name: str) -> DomainInfo:
        info = DomainInfo(name=name, state="running", vnc_port=5900 + len(self._domains))
        self._domains[name] = info
        return info

    async def graceful_shutdown(self, name: str) -> None:
        if name in self._domains:
            self._domains[name].state = "shutoff"

    async def force_destroy(self, name: str) -> None:
        if name in self._domains:
            self._domains[name].state = "shutoff"

    async def undefine(self, name: str) -> None:
        self._domains.pop(name, None)

    async def get_domain_info(self, name: str) -> DomainInfo | None:
        return self._domains.get(name)

    async def host_stats(self) -> dict:
        return {"cpu_count": 8, "memory_total_mb": 32768, "free_memory_mb": 20480}


def get_libvirt_client() -> BaseLibvirtClient:
    if settings.libvirt_driver == "fake":
        return FakeLibvirtClient()
    return QemuLibvirtClient(settings.libvirt_uri)
