from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from .canonicalization import canonical_json_bytes, payload_hash
from .models import (
    CardPaymentNoticeCandidate,
    LifecycleStatus,
    ReasonCode,
    SignedProofEnvelope,
    VerificationRequest,
    VerificationResult,
    VerificationStatus,
)
from .ports import (
    BlockchainReader,
    DependencyUnavailableError,
    IssuerTrustStatus,
    KeyTrustStatus,
    ProofRepository,
)
from .signatures import signature_matches


class VerificationService:
    """Deterministic verifier. Extraction and infrastructure stay outside this core."""

    def __init__(self, proofs: ProofRepository, chain: BlockchainReader) -> None:
        self._proofs = proofs
        self._chain = chain

    async def verify(self, request: VerificationRequest) -> VerificationResult:
        now = datetime.now(UTC)
        checks: dict[str, str] = {}
        try:
            envelope = await self._proofs.get_proof(request.proof_id)
        except DependencyUnavailableError:
            return self._inconclusive(request.request_id, now, checks, "proof_repository")

        if envelope is None:
            return VerificationResult(
                session_id=self._session_id(),
                verification_status=VerificationStatus.NOT_REGISTERED,
                reason_codes=[ReasonCode.PROOF_NOT_FOUND],
                checks={"proof_repository": "NOT_FOUND"},
                verified_at=now,
                request_id=request.request_id,
            )

        checks["proof_repository"] = "FOUND"
        computed_hash = payload_hash(envelope.payload)
        if computed_hash != envelope.payload_hash:
            checks["payload_hash"] = "FAIL"
            return self._tampered(
                request.request_id,
                now,
                checks,
                ReasonCode.PAYLOAD_HASH_MISMATCH,
            )
        checks["payload_hash"] = "PASS"

        if envelope.expires_at is not None and envelope.expires_at <= now:
            checks["expiry"] = "EXPIRED"
            return VerificationResult(
                session_id=self._session_id(),
                verification_status=VerificationStatus.INCONCLUSIVE,
                lifecycle_status=LifecycleStatus.EXPIRED,
                reason_codes=[ReasonCode.PROOF_EXPIRED],
                checks=checks,
                verified_at=now,
                request_id=request.request_id,
            )
        checks["expiry"] = "PASS"

        mismatch_reason = self._candidate_mismatch(envelope, request.candidate)
        if mismatch_reason is not None:
            checks["candidate_match"] = "FAIL"
            return self._tampered(request.request_id, now, checks, mismatch_reason)
        checks["candidate_match"] = "PASS"

        try:
            issuer = await self._chain.get_issuer(envelope.issuer_id)
            key = await self._chain.get_key(envelope.key_id)
            key_valid = await self._chain.is_key_valid(envelope.key_id, envelope.issued_at)
        except DependencyUnavailableError:
            return self._inconclusive(request.request_id, now, checks, "blockchain_reader")

        if issuer is None:
            checks["issuer"] = "NOT_FOUND"
            return VerificationResult(
                session_id=self._session_id(),
                verification_status=VerificationStatus.NOT_REGISTERED,
                reason_codes=[ReasonCode.ISSUER_NOT_FOUND],
                checks=checks,
                verified_at=now,
                request_id=request.request_id,
            )
        if issuer.status is not IssuerTrustStatus.ACTIVE:
            checks["issuer"] = issuer.status
            return self._inconclusive(
                request.request_id,
                now,
                checks,
                "issuer",
                LifecycleStatus.ISSUER_SUSPENDED,
            )
        checks["issuer"] = "ACTIVE"

        if key is None or key.issuer_id != envelope.issuer_id:
            checks["issuer_key"] = "NOT_FOUND"
            return self._inconclusive(
                request.request_id,
                now,
                checks,
                "issuer_key",
                LifecycleStatus.ISSUER_KEY_REVOKED,
            )
        if key.status is not KeyTrustStatus.ACTIVE or not key_valid:
            checks["issuer_key"] = "INVALID"
            return self._inconclusive(
                request.request_id,
                now,
                checks,
                "issuer_key",
                LifecycleStatus.ISSUER_KEY_REVOKED,
            )
        checks["issuer_key"] = "ACTIVE"

        if not signature_matches(envelope, key.signer):
            checks["signature"] = "FAIL"
            return self._tampered(request.request_id, now, checks, ReasonCode.INVALID_SIGNATURE)
        checks["signature"] = "PASS"

        return VerificationResult(
            session_id=self._session_id(),
            verification_status=VerificationStatus.VERIFIED,
            lifecycle_status=LifecycleStatus.ACTIVE,
            checks=checks,
            verified_at=now,
            request_id=request.request_id,
        )

    @staticmethod
    def _candidate_mismatch(
        envelope: SignedProofEnvelope, candidate: CardPaymentNoticeCandidate
    ) -> ReasonCode | None:
        payload = envelope.payload
        for field in (
            "issuer_name",
            "masked_card",
            "currency",
            "merchant",
            "approved_at",
            "transaction_id",
        ):
            candidate_value = getattr(candidate, field)
            is_present_and_different = candidate_value is not None and (
                canonical_json_bytes(candidate_value)
                != canonical_json_bytes(getattr(payload, field))
            )
            if is_present_and_different:
                return ReasonCode.FIELD_MISMATCH
        if candidate.amount_minor is not None and candidate.amount_minor != payload.amount_minor:
            return ReasonCode.AMOUNT_MISMATCH
        if candidate.proof_id is not None and candidate.proof_id != envelope.proof_id:
            return ReasonCode.FIELD_MISMATCH
        return None

    def _tampered(
        self,
        request_id: str,
        now: datetime,
        checks: dict[str, str],
        reason: ReasonCode,
    ) -> VerificationResult:
        return VerificationResult(
            session_id=self._session_id(),
            verification_status=VerificationStatus.TAMPERED,
            lifecycle_status=LifecycleStatus.ACTIVE,
            reason_codes=[reason],
            checks=checks,
            verified_at=now,
            request_id=request_id,
        )

    def _inconclusive(
        self,
        request_id: str,
        now: datetime,
        checks: dict[str, str],
        dependency: str,
        lifecycle_status: LifecycleStatus | None = None,
    ) -> VerificationResult:
        checks[dependency] = "UNAVAILABLE"
        return VerificationResult(
            session_id=self._session_id(),
            verification_status=VerificationStatus.INCONCLUSIVE,
            lifecycle_status=lifecycle_status,
            reason_codes=[ReasonCode.DEPENDENCY_UNAVAILABLE],
            checks=checks,
            verified_at=now,
            request_id=request_id,
        )

    @staticmethod
    def _session_id() -> str:
        return f"vsn_{uuid4().hex}"
