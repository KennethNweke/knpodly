from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    """Used by Docker healthcheck and load balancers. Deliberately has no DB
    dependency so it stays fast and reports liveness even during a DB blip;
    use /health/ready for a deeper readiness check."""
    return {"status": "ok", "service": "knpodly-backend"}
