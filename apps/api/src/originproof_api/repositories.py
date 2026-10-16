from __future__ import annotations

from originproof_core import DependencyUnavailableError, SignedProofEnvelope
from sqlalchemy.exc import SQLAlchemyError

from .database import SignedProofRow


class SqlAlchemyProofRepository:
    """Trusted server-side Signed Proof storage; raw candidate input is never persisted here."""

    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    async def get_proof(self, proof_id: str) -> SignedProofEnvelope | None:
        try:
            async with self._session_factory() as session:
                row = await session.get(SignedProofRow, proof_id)
        except SQLAlchemyError as error:
            raise DependencyUnavailableError("proof repository is unavailable") from error

        if row is None:
            return None
        try:
            return SignedProofEnvelope.model_validate(row.envelope)
        except ValueError as error:
            raise DependencyUnavailableError("stored proof is malformed") from error

    async def upsert(self, envelope: SignedProofEnvelope) -> None:
        serialized = envelope.model_dump(mode="json")
        try:
            async with self._session_factory() as session:
                row = await session.get(SignedProofRow, envelope.proof_id)
                if row is None:
                    session.add(
                        SignedProofRow(
                            proof_id=envelope.proof_id,
                            issuer_id=envelope.issuer_id,
                            key_id=envelope.key_id,
                            payload_hash=envelope.payload_hash,
                            envelope=serialized,
                        )
                    )
                else:
                    row.issuer_id = envelope.issuer_id
                    row.key_id = envelope.key_id
                    row.payload_hash = envelope.payload_hash
                    row.envelope = serialized
                await session.commit()
        except SQLAlchemyError as error:
            raise DependencyUnavailableError("proof repository is unavailable") from error
