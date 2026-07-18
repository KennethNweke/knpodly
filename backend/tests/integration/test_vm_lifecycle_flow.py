"""
End-to-end VM lifecycle test against a real (disposable) Postgres and the
fake libvirt driver: launch -> provision -> extend -> stop, asserting the
business rules from the spec at each step (one VM per student, overlay
cleanup, extension limits).
"""
import pytest

from app.core.security import hash_password
from app.models.operating_system import OperatingSystem, OSStatus
from app.models.user import User, UserRole
from app.models.vm_limit_policy import VMLimitPolicy
from app.models.vm_session import VMState
from app.services import vm_lifecycle
from app.services.libvirt_client import FakeLibvirtClient


@pytest.fixture
def libvirt():
    return FakeLibvirtClient()


async def _seed(db_session):
    db_session.add(VMLimitPolicy(name="default"))
    student = User(
        username="student1", full_name="Test Student",
        password_hash=hash_password("pw"), role=UserRole.student,
    )
    os_row = OperatingSystem(
        slug="ubuntu-test", name="Ubuntu Test", family="Debian",
        status=OSStatus.available, base_image_path="/tmp/does-not-need-to-exist.qcow2",
    )
    db_session.add_all([student, os_row])
    await db_session.commit()
    await db_session.refresh(student)
    await db_session.refresh(os_row)
    return student, os_row


@pytest.mark.asyncio
async def test_full_launch_provision_stop_flow(db_session, libvirt, monkeypatch, tmp_path):
    # Point overlay creation at a tmp dir and stub out the actual qemu-img
    # subprocess call, since CI doesn't have real qcow2 base images.
    from app.services import overlay_manager

    async def fake_create_overlay(*, base_image_path, session_id):
        path = tmp_path / f"{session_id}.qcow2"
        path.write_bytes(b"fake-overlay")
        return str(path)

    monkeypatch.setattr(overlay_manager, "create_overlay", fake_create_overlay)
    monkeypatch.setattr(overlay_manager, "allocate_vnc_port", lambda: 5901)

    student, os_row = await _seed(db_session)

    session = await vm_lifecycle.launch_vm(db_session, user=student, os_slug="ubuntu-test", libvirt=libvirt)
    assert session.state == VMState.queued

    session = await vm_lifecycle.provision_vm(db_session, session=session, os_row=os_row, libvirt=libvirt)
    assert session.state == VMState.running
    assert session.websocket_token is not None
    assert session.expires_at is not None

    # One VM per student is enforced
    with pytest.raises(vm_lifecycle.VMLimitExceeded):
        await vm_lifecycle.launch_vm(db_session, user=student, os_slug="ubuntu-test", libvirt=libvirt)

    extended = await vm_lifecycle.extend_session(db_session, session=session)
    assert extended.extension_count == 1
    assert extended.expires_at > session.expires_at

    # Extension limit enforced (default policy allows 1)
    with pytest.raises(vm_lifecycle.VMLimitExceeded):
        await vm_lifecycle.extend_session(db_session, session=extended)

    stopped = await vm_lifecycle.stop_vm(db_session, session=extended, libvirt=libvirt, reason="user_stop")
    assert stopped.state == VMState.stopped
    import os as _os
    assert not _os.path.exists(stopped.overlay_disk_path)


@pytest.mark.asyncio
async def test_launch_rejects_unavailable_os(db_session, libvirt):
    student, os_row = await _seed(db_session)
    os_row.status = OSStatus.coming_soon
    await db_session.commit()

    with pytest.raises(vm_lifecycle.OSUnavailable):
        await vm_lifecycle.launch_vm(db_session, user=student, os_slug="ubuntu-test", libvirt=libvirt)
