"""HEALTH-01: GET /health returns 200 with {"status": "ok"}."""

from httpx import AsyncClient


async def test_health_returns_ok(app_client: AsyncClient):
    resp = await app_client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
