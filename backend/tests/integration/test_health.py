"""
Integration smoke test: boots the FastAPI app with LIBVIRT_DRIVER=fake and
hits /api/v1/health. Requires DATABASE_URL pointed at a real (test) Postgres
instance since app startup runs the catalogue sync on lifespan startup.
"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
