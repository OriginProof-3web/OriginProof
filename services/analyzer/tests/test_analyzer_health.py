from httpx import ASGITransport, AsyncClient
from originproof_analyzer.main import app


async def test_live_healthcheck() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "live"}
