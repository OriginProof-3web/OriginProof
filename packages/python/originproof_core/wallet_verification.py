"""Pure wallet verification: content, signature, current state and warnings stay separate."""

import hashlib
from uuid import uuid4

from .canonicalization import canonical_json_bytes
from .wallet_contract import (
    CheckResult,
    OfficialContent,
    PaymentContent,
    PublishMessage,
    VerificationRequest,
    VerificationResult,
    WalletDomain,
)
from .wallet_ports import WalletDocument, WalletIssuer, WalletKey
from .wallet_signatures import validate_content, wallet_signer


def matches_document(message, document):
    fields = (
        "document_id",
        "issuer_id",
        "doc_key",
        "version",
        "key_id",
        "original_hash",
        "protected_hash",
        "content_schema",
        "issued_at",
        "expires_at",
    )
    return all(getattr(message, field) == getattr(document, field) for field in fields)


def verify_wallet_document(
    request: VerificationRequest,
    domain: WalletDomain,
    *,
    checked_at: int,
    chain: WalletDocument | None,
    issuer: WalletIssuer | None = None,
    key: WalletKey | None = None,
    message: PublishMessage | None = None,
    content: PaymentContent | OfficialContent | None = None,
    signature: str | None = None,
    original: bytes | None = None,
    candidate_original: bytes | None = None,
    metadata: dict | None = None,
    unavailable: bool = False,
    database_tampered: bool = False,
) -> VerificationResult:
    checks = {
        name: CheckResult(name=name, status="NOT_RUN")
        for name in ("signature", "original_hash", "protected_fields", "current_state", "content")
    }
    reasons, scope = [], "ID_ONLY" if request.scope == "ID_ONLY" else "NONE"
    document = (
        chain.document.model_copy(update={"original_available": original is not None})
        if chain
        else None
    )

    def mark(name, status, reason=None):
        checks[name] = CheckResult(name=name, status=status, reason_code=reason)
        if reason:
            reasons.append(reason)

    def result(status):
        return VerificationResult(
            session_id=f"vsn_{uuid4().hex}",
            verification_status=status,
            comparison_scope=scope,
            document=document,
            checks=list(checks.values()),
            reason_codes=list(dict.fromkeys(reasons)),
            checked_at=checked_at,
            chain_id=domain.chain_id,
            verifying_contract=domain.verifying_contract,
            block_number=chain.block_number if chain else None,
            block_hash=chain.block_hash if chain else None,
        )

    if database_tampered:
        mark("content", "FAILED", "STORED_CONTENT_MISMATCH")
        return result("TAMPERED")
    if message is not None and content is not None:
        try:
            validate_content(message, content)
        except ValueError:
            mark("protected_fields", "FAILED", "STORED_CONTENT_MISMATCH")
            return result("TAMPERED")
        if original is not None:
            if "0x" + hashlib.sha256(original).hexdigest() != message.original_hash:
                mark("original_hash", "FAILED", "STORED_ORIGINAL_MISMATCH")
                return result("TAMPERED")
            mark("original_hash", "PASSED")
    if unavailable:
        mark("current_state", "UNAVAILABLE", "CHAIN_UNAVAILABLE")
        return result("INCONCLUSIVE")
    if chain is None:
        reasons.append("DOCUMENT_NOT_REGISTERED")
        return result("NOT_REGISTERED")
    if (
        chain.chain_id != domain.chain_id
        or chain.verifying_contract != domain.verifying_contract
        or (chain.document.document_id != request.document_id)
        or (request.version is not None and chain.document.version != request.version)
    ):
        mark("current_state", "UNAVAILABLE", "CHAIN_RECORD_MISMATCH")
        return result("INCONCLUSIVE")
    if message is None or content is None or signature is None or original is None:
        mark("signature", "UNAVAILABLE", "ORIGINAL_UNAVAILABLE")
        return result("INCONCLUSIVE")
    if not matches_document(message, document):
        mark("content", "FAILED", "CHAIN_COMMITMENT_MISMATCH")
        return result("TAMPERED")
    if (
        issuer is None
        or key is None
        or any(
            snapshot.chain_id != domain.chain_id
            or snapshot.verifying_contract != domain.verifying_contract
            or snapshot.block_number != chain.block_number
            or snapshot.block_hash != chain.block_hash
            for snapshot in (issuer, key)
        )
    ):
        mark("current_state", "UNAVAILABLE", "CHAIN_SNAPSHOT_UNAVAILABLE")
        return result("INCONCLUSIVE")
    if (
        issuer.issuer_id != message.issuer_id
        or key.issuer_id != message.issuer_id
        or (key.key_id != message.key_id)
    ):
        mark("signature", "FAILED", "ISSUER_KEY_MISMATCH")
        return result("TAMPERED")
    if wallet_signer(domain, message, signature) != key.signer:
        mark("signature", "FAILED", "INVALID_SIGNATURE")
        return result("TAMPERED")
    published = int(chain.published_block)
    if published < int(key.registered_block) or (
        key.retired_block is not None and published >= int(key.retired_block)
    ):
        mark("signature", "UNAVAILABLE", "HISTORICAL_KEY_AUTHORITY_UNCERTAIN")
        return result("INCONCLUSIVE")
    mark("signature", "PASSED")
    if metadata is None:
        mark("issuer_metadata", "UNAVAILABLE", "METADATA_UNAVAILABLE")
    elif "0x" + hashlib.sha256(canonical_json_bytes(metadata)).hexdigest() != issuer.metadata_hash:
        mark("issuer_metadata", "FAILED", "METADATA_HASH_MISMATCH")
        return result("TAMPERED")
    else:
        mark("issuer_metadata", "PASSED")
    warnings = []
    if issuer.state == "SUSPENDED":
        warnings.append("ISSUER_SUSPENDED")
    if key.compromise_block is not None:
        warnings.append("KEY_COMPROMISED")
    state = document.state
    if state == "ACTIVE" and checked_at >= document.expires_at:
        state = "EXPIRED"
    document = document.model_copy(update={"state": state, "warnings": warnings})
    mark("current_state", "PASSED")
    if request.scope == "ID_ONLY":
        reasons.append("CONTENT_NOT_COMPARED")
        return result("INCONCLUSIVE")
    if request.scope == "ORIGINAL_BYTES":
        if candidate_original is None:
            mark("content", "UNAVAILABLE", "ORIGINAL_UNAVAILABLE")
            return result("INCONCLUSIVE")
        scope = "FULL_COMPARISON"
        if candidate_original != original:
            mark("content", "FAILED", "ORIGINAL_HASH_MISMATCH")
            return result("TAMPERED")
    else:
        candidate = request.candidate or {}
        expected = content.model_dump()
        if set(candidate) - set(expected):
            reasons.append("COMPARISON_FIELD_UNSUPPORTED")
            return result("INCONCLUSIVE")
        provided = {k: v for k, v in candidate.items() if v is not None}
        try:
            normalized = type(content).model_validate(expected | provided).model_dump()
        except ValueError:
            reasons.append("COMPARISON_INPUT_INVALID")
            return result("INCONCLUSIVE")
        full = all(k in provided for k, v in expected.items() if v is not None)
        scope = "FULL_COMPARISON" if full else "PARTIAL_COMPARISON"
        if any(
            canonical_json_bytes(normalized[k]) != canonical_json_bytes(expected[k])
            for k in provided
        ):
            mark("protected_fields", "FAILED", "PROTECTED_FIELDS_MISMATCH")
            mark("content", "FAILED")
            return result("TAMPERED")
        if not full:
            reasons.append("CONTENT_PARTIALLY_COMPARED")
            return result("INCONCLUSIVE")
        mark("protected_fields", "PASSED")
    mark("content", "PASSED")
    return result("VERIFIED" if metadata is not None else "INCONCLUSIVE")
