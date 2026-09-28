"""Verify the synthetic MVP through the running public API endpoint."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
API_URL = os.environ.get("MVP_API_URL", "http://127.0.0.1:8000")
FIELDS = (
    "issuer_name",
    "masked_card",
    "amount_minor",
    "currency",
    "merchant",
    "approved_at",
    "transaction_id",
    "proof_id",
)


def verification_request(fixture_name: str, request_id: str) -> dict[str, object]:
    fixture = json.loads((ROOT / "fixtures/mvp" / fixture_name).read_text(encoding="utf-8"))
    return {
        "proof_id": fixture["proof_id"],
        "request_id": request_id,
        "candidate": {
            **{field: fixture[field] for field in FIELDS},
            "confidence": 1,
            "missing_fields": [],
        },
    }


async def wait_until_ready(client: httpx.AsyncClient) -> None:
    for _ in range(20):
        try:
            response = await client.get("/health/ready")
            if response.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        await asyncio.sleep(0.5)
    raise RuntimeError("API did not become ready")


async def verify(
    client: httpx.AsyncClient, fixture_name: str, request_id: str
) -> dict[str, object]:
    response = await client.post(
        "/v1/mvp/card-notices/verify",
        json=verification_request(fixture_name, request_id),
    )
    response.raise_for_status()
    return response.json()


async def main() -> None:
    async with httpx.AsyncClient(base_url=API_URL, timeout=5, trust_env=False) as client:
        await wait_until_ready(client)
        normal = await verify(client, "card_notice_valid.json", "req_e2e_valid")
        tampered = await verify(client, "card_notice_amount_tampered.json", "req_e2e_tampered")

    assert normal["verification_status"] == "VERIFIED"
    assert normal["lifecycle_status"] == "ACTIVE"
    assert normal["reason_codes"] == []
    assert normal["checks"]["signature"] == "PASS"
    assert tampered["verification_status"] == "TAMPERED"
    assert tampered["lifecycle_status"] == "ACTIVE"
    assert tampered["reason_codes"] == ["AMOUNT_MISMATCH"]
    print("MVP HTTP E2E passed: VERIFIED + ACTIVE; TAMPERED + AMOUNT_MISMATCH")


if __name__ == "__main__":
    asyncio.run(main())
