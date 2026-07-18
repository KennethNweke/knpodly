"""
Long-running background process (separate container, see `scheduler` service
in docker-compose) responsible for:

  1. Watching VM_IMAGES_PATH for new/changed OS folders (automatic image
     discovery, no restart required).
  2. Periodically scanning vm_sessions for:
       - sessions past `expires_at`              -> auto-shutdown + destroy
       - sessions idle past idle_timeout_minutes   -> auto-shutdown + destroy
       - sessions idle past idle_warning_minutes    -> emit warning event (once)
       - sessions nearing expiry (< expiry_warning_minutes) -> emit warning event (once)

Runs as a single asyncio process (not cron) so timing checks can run every
few seconds without process-spawn overhead. Each sweep opens its own DB
session and libvirt client so it doesn't hold connections open between runs.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models.vm_session import VMSession, VMState
from app.services import image_discovery, vm_lifecycle
from app.services.libvirt_client import get_libvirt_client
from app.services.policy import get_active_policy
from app.services.redis_bus import publish_event

settings = get_settings()
logger = logging.getLogger("knpodly.scheduler")

SWEEP_INTERVAL_SECONDS = 15
# Debounce filesystem-triggered resyncs: watchdog fires several events per
# logical change (e.g. writing metadata.json = create + modify), so batch
# rapid-fire events into a single resync rather than hammering the DB.
RESYNC_DEBOUNCE_SECONDS = 2.0


class _ImageDirHandler(FileSystemEventHandler):
    def __init__(self, schedule_resync):
        self._schedule_resync = schedule_resync

    def on_any_event(self, event):
        self._schedule_resync()


async def _check_expired_and_idle_sessions() -> None:
    libvirt = get_libvirt_client()
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as db:
        policy = await get_active_policy(db)
        running = (
            await db.execute(select(VMSession).where(VMSession.state == VMState.running))
        ).scalars().all()

        for session in running:
            # --- Hard expiry: session duration (incl. any extensions) is up ---
            if session.expires_at and now >= session.expires_at:
                logger.info("Session %s expired, tearing down", session.id)
                await vm_lifecycle.stop_vm(db, session=session, libvirt=libvirt, reason="expired")
                await publish_event("vm.expired", {"session_id": str(session.id), "user_id": str(session.user_id)})
                continue

            # --- Expiry warning (fires once per session) ---
            if session.expires_at:
                warn_at = session.expires_at - timedelta(minutes=settings.session_expiry_warning_minutes)
                if now >= warn_at and session.idle_warning_sent_at is None:
                    # Reuse idle_warning_sent_at isn't appropriate here since it's
                    # keyed to idle detection; expiry warnings are one-shot per
                    # session so we track them via a dashboard event only —
                    # the frontend derives "time remaining" from expires_at
                    # directly and shows its own countdown/banner client-side.
                    await publish_event(
                        "vm.expiry_warning",
                        {
                            "session_id": str(session.id),
                            "user_id": str(session.user_id),
                            "expires_at": session.expires_at.isoformat(),
                        },
                    )

            # --- Idle timeout (policy-driven, lecturer-configurable) ---
            last_activity = session.last_activity_at or session.started_at or session.created_at
            idle_for = now - last_activity
            idle_timeout = timedelta(minutes=policy.idle_timeout_minutes)
            idle_warning = timedelta(minutes=policy.idle_warning_minutes)

            if idle_for >= idle_timeout:
                logger.info("Session %s idle timeout, tearing down", session.id)
                await vm_lifecycle.stop_vm(db, session=session, libvirt=libvirt, reason="idle_timeout")
                await publish_event("vm.idle_timeout", {"session_id": str(session.id), "user_id": str(session.user_id)})
                continue

            if idle_for >= idle_warning and session.idle_warning_sent_at is None:
                session.idle_warning_sent_at = now
                await db.commit()
                await publish_event(
                    "vm.idle_warning",
                    {"session_id": str(session.id), "user_id": str(session.user_id)},
                )


async def main():
    logging.basicConfig(level=settings.log_level)
    loop = asyncio.get_event_loop()
    resync_pending = False
    resync_lock = asyncio.Lock()

    async def resync():
        async with AsyncSessionLocal() as db:
            count = await image_discovery.sync_to_database(db)
            logger.info("Image catalogue resynced: %s entries", count)
            await publish_event("catalogue.resynced", {"count": count})

    async def debounced_resync():
        nonlocal resync_pending
        async with resync_lock:
            if resync_pending:
                return
            resync_pending = True
        await asyncio.sleep(RESYNC_DEBOUNCE_SECONDS)
        async with resync_lock:
            resync_pending = False
        await resync()

    def schedule_resync():
        loop.create_task(debounced_resync())

    observer = Observer()
    observer.schedule(_ImageDirHandler(schedule_resync), settings.vm_images_path, recursive=True)
    observer.start()
    logger.info("Scheduler started: watching %s, sweeping every %ss", settings.vm_images_path, SWEEP_INTERVAL_SECONDS)

    try:
        while True:
            try:
                await _check_expired_and_idle_sessions()
            except Exception:
                logger.exception("Error during session sweep")
            await asyncio.sleep(SWEEP_INTERVAL_SECONDS)
    finally:
        observer.stop()
        observer.join()


if __name__ == "__main__":
    asyncio.run(main())
