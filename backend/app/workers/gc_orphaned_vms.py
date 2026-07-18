"""
One-shot reconciliation script (see infra/systemd/knpodly-vm-gc.timer):
compares libvirt's actual running domains against vm_sessions rows in
`running`/`stopping` state and cleans up any mismatch — e.g. a domain that's
still defined in libvirt but whose DB row never got marked stopped because
the scheduler container was down (host reboot, crash, etc).

Run manually with: python -m app.workers.gc_orphaned_vms
"""
import asyncio

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.vm_session import VMSession, VMState
from app.services import vm_lifecycle
from app.services.libvirt_client import get_libvirt_client


async def main():
    libvirt = get_libvirt_client()
    async with AsyncSessionLocal() as db:
        sessions = (
            await db.execute(
                select(VMSession).where(VMSession.state.in_([VMState.running, VMState.stopping]))
            )
        ).scalars().all()

        for session in sessions:
            if not session.libvirt_domain_name:
                continue
            info = await libvirt.get_domain_info(session.libvirt_domain_name)
            if info is None or info.state == "shutoff":
                await vm_lifecycle.stop_vm(db, session=session, libvirt=libvirt, reason="error")


if __name__ == "__main__":
    asyncio.run(main())
