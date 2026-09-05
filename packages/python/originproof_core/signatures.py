from __future__ import annotations

from typing import Any

from eth_keys import keys
from eth_keys.exceptions import BadSignature, ValidationError

from .canonicalization import payload_hash
from .models import SignedProofEnvelope


def signing_payload(envelope: SignedProofEnvelope) -> dict[str, Any]:
    """The versioned, domain-separated message committed by an issuer signature."""
    return {
        "app_domain": envelope.app_domain,
        "chain_id": envelope.chain_id,
        "expires_at": envelope.expires_at,
        "issued_at": envelope.issued_at,
        "issuer_id": envelope.issuer_id,
        "key_id": envelope.key_id,
        "metadata_hash": envelope.metadata_hash,
        "nonce": envelope.nonce,
        "payload_hash": envelope.payload_hash,
        "proof_id": envelope.proof_id,
        "proof_type": envelope.proof_type,
        "schema_version": envelope.schema_version,
        "signature_scheme": envelope.signature_scheme,
        "single_use": envelope.single_use,
        "subject_binding_hash": envelope.subject_binding_hash,
    }


def signing_digest(envelope: SignedProofEnvelope) -> str:
    return payload_hash(signing_payload(envelope))


def signer_address(envelope: SignedProofEnvelope) -> str | None:
    """Recover the Ethereum signer address from a 65-byte secp256k1 signature."""
    try:
        signature_bytes = bytes.fromhex(envelope.signature.removeprefix("0x"))
        if len(signature_bytes) != 65:
            return None
        recovery_id = signature_bytes[-1]
        if recovery_id in (27, 28):
            signature_bytes = signature_bytes[:-1] + bytes([recovery_id - 27])
        if signature_bytes[-1] not in (0, 1):
            return None
        message_hash = bytes.fromhex(signing_digest(envelope).removeprefix("0x"))
        return (
            keys.Signature(signature_bytes=signature_bytes)
            .recover_public_key_from_msg_hash(message_hash)
            .to_checksum_address()
        )
    except (BadSignature, TypeError, ValidationError, ValueError):
        return None


def signature_matches(envelope: SignedProofEnvelope, expected_signer: str) -> bool:
    actual = signer_address(envelope)
    return actual is not None and actual.lower() == expected_signer.lower()
