"""OS catalogue endpoints — powers the student/lecturer 'available distros' cards."""
import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, require_lecturer
from app.core.config import get_settings
from app.db.session import get_db
from app.models.operating_system import OperatingSystem
from app.models.user import User
from app.schemas.operating_system import OperatingSystemOut
from app.services import audit, image_discovery

router = APIRouter(prefix="/operating-systems", tags=["operating-systems"])


@router.get("", response_model=list[OperatingSystemOut])
async def list_operating_systems(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return (await db.execute(select(OperatingSystem).order_by(OperatingSystem.name))).scalars().all()


@router.post("/rescan", response_model=dict)
async def rescan_catalogue(db: AsyncSession = Depends(get_db), _: User = Depends(require_lecturer)):
    """Manually trigger a re-scan of VMImages/. Normally unnecessary since the
    scheduler's filesystem watcher does this automatically, but useful right
    after a lecturer uploads a new image via the admin UI."""
    count = await image_discovery.sync_to_database(db)
    return {"synced": count}


@router.post("/{slug}/upload-image", status_code=201)
async def upload_base_image(
    slug: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_lecturer),
):
    """
    Uploads a QCOW2 master image for a new or existing distro slug. Writes
    directly into VMImages/<slug>/base.qcow2 so the existing image_discovery
    scan picks it up on the next sweep (or immediately via /rescan).

    Streamed to disk in chunks rather than read into memory at once — base
    images are commonly several GB, well beyond what should ever sit fully
    in a request handler's memory.
    """
    if not slug.replace("-", "").replace(".", "").isalnum():
        raise HTTPException(status_code=400, detail="Slug must be alphanumeric (dashes/dots allowed)")
    if not file.filename or not file.filename.endswith(".qcow2"):
        raise HTTPException(status_code=400, detail="Expected a .qcow2 file")

    settings = get_settings()
    os_dir = os.path.join(settings.vm_images_path, slug)
    os.makedirs(os_dir, exist_ok=True)
    dest_path = os.path.join(os_dir, "base.qcow2")
    tmp_path = dest_path + ".uploading"

    size = 0
    with open(tmp_path, "wb") as out:
        while chunk := await file.read(8 * 1024 * 1024):
            size += len(chunk)
            if size > settings.max_upload_bytes:
                out.close()
                os.remove(tmp_path)
                raise HTTPException(status_code=413, detail="Image exceeds maximum upload size")
            out.write(chunk)

    os.replace(tmp_path, dest_path)  # atomic rename: never expose a partial file to the catalogue scan

    await audit.record(
        db, actor_id=user.id, actor_role=user.role.value, action="image.uploaded",
        target_type="operating_system", target_id=slug, metadata={"bytes": size},
    )
    return {"detail": f"Uploaded base image for '{slug}' ({size} bytes). Add/update metadata.json, then rescan."}


@router.post("/{slug}/upload-icon", status_code=201)
async def upload_icon(
    slug: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_lecturer),
):
    """Uploads a fallback icon to VMIcons/<slug>.<ext> (webp/svg/png/jpg/jpeg)."""
    settings = get_settings()
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in (".webp", ".svg", ".png", ".jpg", ".jpeg"):
        raise HTTPException(status_code=400, detail="Icon must be webp, svg, png, jpg, or jpeg")

    os.makedirs(settings.vm_icons_path, exist_ok=True)
    dest_path = os.path.join(settings.vm_icons_path, f"{slug}{ext}")
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Icon exceeds 5MB limit")
    with open(dest_path, "wb") as out:
        out.write(data)

    await audit.record(
        db, actor_id=user.id, actor_role=user.role.value, action="icon.uploaded",
        target_type="operating_system", target_id=slug,
    )
    return {"detail": f"Uploaded icon for '{slug}'"}
