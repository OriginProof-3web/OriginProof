"""Pure v2 evaluation; callers must authorize restricted comparison before calling."""

from datetime import UTC, datetime
from uuid import uuid4

from .canonicalization import canonical_json_bytes, payload_hash
from .finals import (
    CheckState,
    FinalsProofType,
    FinalsReasonCode,
    FinalsSignedProofEnvelope,
    FinalsVerificationResult,
    VerificationScope,
    representative_lifecycle,
)
from .models import LifecycleStatus, VerificationStatus
from .ports import IssuerRecord, IssuerTrustStatus, KeyRecord, KeyTrustStatus
from .signatures import signature_matches


def evaluate_finals(
    envelope: FinalsSignedProofEnvelope,
    *,
    request_id: str,
    chain_id: int,
    issuer: IssuerRecord | None,
    key: KeyRecord | None,
    candidate: dict[str, object] | None = None,
    proof_states: set[LifecycleStatus] | None = None,
    now: datetime | None = None,
) -> FinalsVerificationResult:
    """None proof_states is W3 NOT_RUN, never an assertion of current validity."""
    now = now or datetime.now(UTC)
    checks = dict.fromkeys(
        (
            "contract",
            "payload_hash",
            "issuer",
            "issuer_key",
            "signature",
            "proof_status",
            "candidate_match",
        ),
        CheckState.NOT_RUN,
    )
    scope = VerificationScope.PROOF_ONLY
    reasons: list[FinalsReasonCode] = []
    lifecycle = None

    def result(status):
        return FinalsVerificationResult(
            session_id=f"vsn_{uuid4().hex}",
            verification_status=status,
            lifecycle_status=lifecycle,
            scope=scope,
            reason_codes=reasons,
            checks=checks,
            verified_at=now,
            request_id=request_id,
        )

    if envelope.app_domain != "originproof.finals":
        reasons.append(FinalsReasonCode.DOMAIN_MISMATCH)
    if envelope.chain_id != chain_id:
        reasons.append(FinalsReasonCode.NETWORK_MISMATCH)
    if envelope.schema_version != "2.0.0":
        reasons.append(FinalsReasonCode.SCHEMA_UNSUPPORTED)
    if reasons:
        checks["contract"] = CheckState.FAIL
        return result(VerificationStatus.INCONCLUSIVE)
    checks["contract"] = CheckState.PASS
    if payload_hash(envelope.payload) != envelope.payload_hash:
        checks["payload_hash"] = CheckState.FAIL
        reasons.append(FinalsReasonCode.PAYLOAD_HASH_MISMATCH)
        return result(VerificationStatus.TAMPERED)
    checks["payload_hash"] = CheckState.PASS
    if issuer is None or issuer.issuer_id != envelope.issuer_id:
        checks["issuer"] = CheckState.FAIL
        reasons.append(FinalsReasonCode.ISSUER_NOT_FOUND)
        return result(VerificationStatus.NOT_REGISTERED)
    checks["issuer"] = CheckState.PASS
    if key is None or key.key_id != envelope.key_id or key.issuer_id != envelope.issuer_id:
        checks["issuer_key"] = CheckState.FAIL
        reasons.append(FinalsReasonCode.KEY_NOT_FOUND)
        return result(VerificationStatus.INCONCLUSIVE)
    if not key.valid_from <= envelope.issued_at < key.valid_until:
        checks["issuer_key"] = CheckState.FAIL
        reasons.append(FinalsReasonCode.KEY_TIME_INVALID)
        return result(VerificationStatus.INCONCLUSIVE)
    checks["issuer_key"] = CheckState.PASS
    if not signature_matches(envelope, key.signer):
        checks["signature"] = CheckState.FAIL
        reasons.append(FinalsReasonCode.INVALID_SIGNATURE)
        return result(VerificationStatus.TAMPERED)
    checks["signature"] = CheckState.PASS
    states = set(proof_states or ())
    if key.status == KeyTrustStatus.REVOKED:
        states.add(LifecycleStatus.ISSUER_KEY_REVOKED)
    if issuer.status != IssuerTrustStatus.ACTIVE:
        states.add(LifecycleStatus.ISSUER_SUSPENDED)
    if now >= envelope.expires_at:
        states.add(LifecycleStatus.EXPIRED)
    for state in states:
        code = {
            LifecycleStatus.PROOF_REVOKED: FinalsReasonCode.PROOF_REVOKED,
            LifecycleStatus.ISSUER_KEY_REVOKED: FinalsReasonCode.ISSUER_KEY_REVOKED,
            LifecycleStatus.ISSUER_SUSPENDED: FinalsReasonCode.ISSUER_SUSPENDED,
            LifecycleStatus.CONSUMED: FinalsReasonCode.REPLAY_DETECTED,
            LifecycleStatus.EXPIRED: FinalsReasonCode.PROOF_EXPIRED,
        }.get(state)
        if code:
            reasons.append(code)
    if proof_states is not None:
        lifecycle = representative_lifecycle(states)
        checks["proof_status"] = CheckState.PASS
    if candidate is None:
        return result(VerificationStatus.VERIFIED)
    fields = (
        ("amount_minor", "currency", "target_hash")
        if envelope.proof_type == FinalsProofType.PAYMENT_REQUEST
        else ("institution_code", "document_type", "document_number", "version")
    )
    missing = any(candidate.get(field) is None for field in fields)
    scope = VerificationScope.PARTIAL_COMPARISON if missing else VerificationScope.FULL_COMPARISON
    mismatches = [
        field
        for field in fields
        if candidate.get(field) is not None
        and canonical_json_bytes(candidate[field])
        != canonical_json_bytes(getattr(envelope.payload, field))
    ]
    if mismatches:
        checks["candidate_match"] = CheckState.FAIL
        reasons.append(
            FinalsReasonCode.AMOUNT_MISMATCH
            if "amount_minor" in mismatches
            else FinalsReasonCode.FIELD_MISMATCH
        )
        return result(VerificationStatus.TAMPERED)
    if missing:
        reasons.append(FinalsReasonCode.INPUT_INCOMPLETE)
        return result(VerificationStatus.INCONCLUSIVE)
    checks["candidate_match"] = CheckState.PASS
    return result(VerificationStatus.VERIFIED)
