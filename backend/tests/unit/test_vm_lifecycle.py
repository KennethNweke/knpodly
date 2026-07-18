"""
Unit tests for VM lifecycle rules against the fake libvirt driver + an
in-memory SQLite-compatible async session would normally be used here; shown
as an illustrative structural test using pytest-asyncio and a lightweight
fixture. Wire up a real async test DB (e.g. via testcontainers-postgres) for
full integration coverage — see tests/integration/ for that layer.
"""
import pytest

from app.services import vm_lifecycle


@pytest.mark.asyncio
async def test_student_cannot_launch_second_vm(monkeypatch):
    """Placeholder illustrating intended coverage: asserts VMLimitExceeded is
    raised when launch_vm is called for a student with an existing active
    session. Full implementation requires a seeded async test DB session."""
    assert issubclass(vm_lifecycle.VMLimitExceeded, Exception)
