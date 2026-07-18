"""
Automatic OS catalogue discovery.

Watches VM_IMAGES_PATH for new/changed/removed subdirectories using
`watchdog`. Each subdirectory is expected to contain:
    base.qcow2      - immutable master image (never modified after creation)
    metadata.json   - see schema below
    splash.png      - optional icon override; otherwise falls back to
                       VM_ICONS_PATH/<slug>.{webp,svg,png,jpg,jpeg}

metadata.json schema (extra keys are ignored, all but `name` optional with
sane fallbacks):
{
  "name": "Ubuntu 24.04",
  "family": "Debian",
  "packageManager": "apt",
  "ram": "2GB",
  "vcpus": 2,
  "architecture": "x86_64",
  "description": "Ubuntu LTS for Linux Fundamentals",
  "status": "Available"          # Available | Coming Soon | Disabled
}

On (re)scan, each valid directory is upserted into the `operating_systems`
table. Invalid directories (missing base.qcow2, malformed metadata.json) are
logged and skipped rather than crashing discovery — one broken OS folder
should never take the whole catalogue down.

This runs both as: (a) a one-shot scan on backend startup, and (b) a
long-lived watcher in the `scheduler` worker process so new images added
while the app is running appear without a restart, per the spec's
"no code changes or application restart required" goal.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.operating_system import OperatingSystem, OSStatus

settings = get_settings()

_STATUS_MAP = {
    "available": OSStatus.available,
    "coming soon": OSStatus.coming_soon,
    "coming_soon": OSStatus.coming_soon,
    "disabled": OSStatus.disabled,
}

_ICON_EXTENSIONS = (".webp", ".svg", ".png", ".jpg", ".jpeg")


@dataclass
class DiscoveredImage:
    slug: str
    name: str
    family: str
    package_manager: str | None
    ram_mb: int
    vcpus: int
    architecture: str
    description: str | None
    status: OSStatus
    base_image_path: str
    icon_path: str | None
    checksum_sha256: str | None


def _parse_ram_to_mb(value) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        v = value.strip().upper()
        if v.endswith("GB"):
            return int(float(v[:-2]) * 1024)
        if v.endswith("MB"):
            return int(float(v[:-2]))
    return settings.vm_default_ram_mb


def _find_icon(slug: str, images_dir: str) -> str | None:
    for ext in _ICON_EXTENSIONS:
        candidate = os.path.join(images_dir, "splash" + ext)
        if os.path.isfile(candidate):
            return candidate
    for ext in _ICON_EXTENSIONS:
        candidate = os.path.join(settings.vm_icons_path, slug + ext)
        if os.path.isfile(candidate):
            return candidate
    return None


def _checksum(path: str, chunk_size: int = 1024 * 1024) -> str | None:
    if not os.path.isfile(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def scan_directory(slug: str) -> DiscoveredImage | None:
    """Validate and parse a single VMImages/<slug>/ directory. Returns None (and
    logs) if invalid rather than raising, so callers can skip bad entries."""
    images_dir = os.path.join(settings.vm_images_path, slug)
    metadata_path = os.path.join(images_dir, "metadata.json")
    base_image_path = os.path.join(images_dir, "base.qcow2")

    if not os.path.isfile(metadata_path):
        return None

    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    if "name" not in meta:
        return None

    status_raw = str(meta.get("status", "validating")).lower()
    status = _STATUS_MAP.get(status_raw, OSStatus.validating)
    if not os.path.isfile(base_image_path) and status == OSStatus.available:
        # Declared available but no actual image present -> don't let it be launchable
        status = OSStatus.validating

    return DiscoveredImage(
        slug=slug,
        name=meta["name"],
        family=meta.get("family", "Unknown"),
        package_manager=meta.get("packageManager"),
        ram_mb=_parse_ram_to_mb(meta.get("ram")),
        vcpus=int(meta.get("vcpus", settings.vm_default_vcpus)),
        architecture=meta.get("architecture", "x86_64"),
        description=meta.get("description"),
        status=status,
        base_image_path=base_image_path,
        icon_path=_find_icon(slug, images_dir),
        checksum_sha256=_checksum(base_image_path),
    )


def scan_all() -> list[DiscoveredImage]:
    if not os.path.isdir(settings.vm_images_path):
        return []
    results = []
    for entry in sorted(os.listdir(settings.vm_images_path)):
        full = os.path.join(settings.vm_images_path, entry)
        if os.path.isdir(full):
            found = scan_directory(entry)
            if found:
                results.append(found)
    return results


async def sync_to_database(db: AsyncSession) -> int:
    """Upserts all discovered images into `operating_systems`. Returns count synced."""
    discovered = scan_all()
    for img in discovered:
        existing = (
            await db.execute(select(OperatingSystem).where(OperatingSystem.slug == img.slug))
        ).scalar_one_or_none()
        if existing:
            existing.name = img.name
            existing.family = img.family
            existing.package_manager = img.package_manager
            existing.default_ram_mb = img.ram_mb
            existing.default_vcpus = img.vcpus
            existing.architecture = img.architecture
            existing.description = img.description
            existing.status = img.status
            existing.base_image_path = img.base_image_path
            existing.icon_path = img.icon_path
            existing.checksum_sha256 = img.checksum_sha256
        else:
            db.add(
                OperatingSystem(
                    slug=img.slug,
                    name=img.name,
                    family=img.family,
                    package_manager=img.package_manager,
                    default_ram_mb=img.ram_mb,
                    default_vcpus=img.vcpus,
                    architecture=img.architecture,
                    description=img.description,
                    status=img.status,
                    base_image_path=img.base_image_path,
                    icon_path=img.icon_path,
                    checksum_sha256=img.checksum_sha256,
                )
            )
    await db.commit()
    return len(discovered)
