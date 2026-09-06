from __future__ import annotations

import asyncio
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import httpx
from originproof_api.database import Database
from originproof_api.repositories import SqlAlchemyProofRepository
from originproof_api.settings import Settings
from originproof_core import (
    CardPaymentNoticeCandidate,
    IssuerRecord,
    IssuerTrustStatus,
    KeyRecord,
    KeyTrustStatus,
    VerificationRequest,
    VerificationService,
    VerificationStatus,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "build" / "seed_manifest.json"


class SeededChainReader:
    """Test-only chain port using the synthetic issuer recorded by the seed."""

    def __init__(self, issuer_id: str, key_id: str, signer: str) -> None:
        self._issuer_id = issuer_id
        self._key_id = key_id
        self._signer = signer

    async def get_issuer(self, issuer_id: str) -> IssuerRecord | None:
        if issuer_id != self._issuer_id:
            return None
        return IssuerRecord(issuer_id=issuer_id, status=IssuerTrustStatus.ACTIVE)

    async def get_key(self, key_id: str) -> KeyRecord | None:
        if key_id != self._key_id:
            return None
        return KeyRecord(
            key_id=key_id,
            issuer_id=self._issuer_id,
            signer=self._signer,
            status=KeyTrustStatus.ACTIVE,
            valid_from=datetime(2020, 1, 1, tzinfo=UTC),
            valid_until=datetime(2030, 1, 1, tzinfo=UTC),
        )

    async def is_key_valid(self, key_id: str, at: datetime) -> bool:
        return key_id == self._key_id and datetime(2020, 1, 1, tzinfo=UTC) <= at <= datetime(
            2030, 1, 1, tzinfo=UTC
        )


async def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    database = Database(os.environ.get("SEED_DATABASE_URL", Settings().database_url))
    repository = SqlAlchemyProofRepository(database.session_factory)
    try:
        envelope = await repository.get_proof(manifest["proof_id"])
        if envelope is None:
            raise RuntimeError("seeded proof was not found in PostgreSQL")

        candidate = CardPaymentNoticeCandidate(
            **envelope.payload.model_dump(),
            proof_id=envelope.proof_id,
            confidence=1,
        )
        verifier = VerificationService(
            repository,
            SeededChainReader(manifest["issuer_id"], manifest["key_id"], manifest["signer"]),
        )
        verified = await verifier.verify(
            VerificationRequest(
                proof_id=envelope.proof_id,
                candidate=candidate,
                request_id="req_db_smoke_verified",
            )
        )
        if verified.verification_status is not VerificationStatus.VERIFIED:
            raise RuntimeError(f"expected VERIFIED, received {verified.verification_status}")

        tampered = await verifier.verify(
            VerificationRequest(
                proof_id=envelope.proof_id,
                candidate=candidate.model_copy(update={"amount_minor": candidate.amount_minor + 1}),
                request_id="req_db_smoke_tampered",
            )
        )
        if tampered.verification_status is not VerificationStatus.TAMPERED:
            raise RuntimeError(f"expected TAMPERED, received {tampered.verification_status}")
    finally:
        await database.dispose()

    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=10) as client:
        response = await client.post(
            "/v1/mvp/card-notices/verify",
            json=VerificationRequest(
                proof_id=envelope.proof_id,
                candidate=candidate,
                request_id="req_api_storage_smoke",
            ).model_dump(mode="json"),
        )
    response.raise_for_status()
    body = response.json()
    if body["verification_status"] != "INCONCLUSIVE":
        raise RuntimeError("API must be INCONCLUSIVE until the M4 blockchain reader is connected")
    if body["checks"].get("proof_repository") != "FOUND":
        raise RuntimeError("API did not read the seeded proof from PostgreSQL")
    print("Proof storage smoke check passed.")


if __name__ == "__main__":
    asyncio.run(main())
