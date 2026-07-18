"""
Unit tests for the image discovery service, exercising the metadata.json
schema described in the spec directly against a temp directory — no DB or
libvirt involved.
"""
import json
import os

import pytest

from app.services import image_discovery


@pytest.fixture
def fake_images_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(image_discovery.settings, "vm_images_path", str(tmp_path))
    monkeypatch.setattr(image_discovery.settings, "vm_icons_path", str(tmp_path / "_icons"))
    os.makedirs(tmp_path / "_icons", exist_ok=True)
    return tmp_path


def _write_os(base_dir, slug, metadata: dict, with_image=True):
    os_dir = base_dir / slug
    os_dir.mkdir()
    (os_dir / "metadata.json").write_text(json.dumps(metadata))
    if with_image:
        (os_dir / "base.qcow2").write_bytes(b"fake-qcow2-data")


def test_valid_os_is_discovered(fake_images_dir):
    _write_os(fake_images_dir, "ubuntu-24.04", {
        "name": "Ubuntu 24.04", "family": "Debian", "packageManager": "apt",
        "ram": "2GB", "architecture": "x86_64",
        "description": "Ubuntu LTS", "status": "Available",
    })
    found = image_discovery.scan_directory("ubuntu-24.04")
    assert found is not None
    assert found.name == "Ubuntu 24.04"
    assert found.ram_mb == 2048
    assert found.status.value == "available"


def test_missing_metadata_is_skipped(fake_images_dir):
    (fake_images_dir / "broken-os").mkdir()
    assert image_discovery.scan_directory("broken-os") is None


def test_available_without_base_image_downgrades_to_validating(fake_images_dir):
    _write_os(fake_images_dir, "kali", {
        "name": "Kali Linux", "family": "Debian", "status": "Coming Soon",
    }, with_image=False)
    found = image_discovery.scan_directory("kali")
    assert found is not None
    assert found.status.value == "coming_soon"
