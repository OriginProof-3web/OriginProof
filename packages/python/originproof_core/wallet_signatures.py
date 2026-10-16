"""Fixed flat EIP-712 messages for the shared preparation contract, separate from v1/v2."""

from __future__ import annotations

import hashlib

from Crypto.Hash import keccak
from eth_keys import keys
from eth_keys.constants import SECPK1_N
from eth_keys.exceptions import BadSignature, ValidationError

from .canonicalization import canonical_json_bytes
from .wallet_contract import (
    GovernanceProposal,
    KeyProofMessage,
    OfficialContent,
    PaymentContent,
    PublishMessage,
    RevokeMessage,
    WalletDomain,
)

EIP712_TYPES = {
    "EIP712Domain": [
        ("name", "string"),
        ("version", "string"),
        ("chainId", "uint256"),
        ("verifyingContract", "address"),
    ],
    "Publish": [
        ("action", "uint8"),
        ("issuerId", "bytes32"),
        ("docKey", "bytes32"),
        ("documentId", "bytes32"),
        ("version", "uint64"),
        ("keyId", "bytes32"),
        ("originalHash", "bytes32"),
        ("protectedHash", "bytes32"),
        ("contentSchema", "bytes32"),
        ("signatureSchema", "bytes32"),
        ("originalHashAlgorithm", "uint8"),
        ("protectedHashAlgorithm", "uint8"),
        ("issuedAt", "uint64"),
        ("expiresAt", "uint64"),
        ("nonce", "uint256"),
        ("deadline", "uint64"),
    ],
    "Revoke": [
        ("action", "uint8"),
        ("issuerId", "bytes32"),
        ("docKey", "bytes32"),
        ("documentId", "bytes32"),
        ("version", "uint64"),
        ("keyId", "bytes32"),
        ("nonce", "uint256"),
        ("deadline", "uint64"),
    ],
    "KeyProof": [
        ("action", "uint8"),
        ("applicationId", "bytes32"),
        ("issuerId", "bytes32"),
        ("signer", "address"),
        ("challengeNonce", "bytes32"),
        ("deadline", "uint64"),
    ],
}


def keccak_bytes(value: bytes) -> bytes:
    return keccak.new(digest_bits=256, data=value).digest()


def identifier_hash(value: str) -> str:
    return "0x" + keccak_bytes(value.encode("utf-8")).hex()


SIGNATURE_SCHEMA = identifier_hash("originproof.wallet.v1")
CONTENT_SCHEMAS = {
    "PAYMENT_REQUEST": identifier_hash("originproof.content.payment.v1"),
    "OFFICIAL_DOCUMENT": identifier_hash("originproof.content.official.v1"),
}


def document_id(issuer_id: str, doc_key: str) -> str:
    issuer_bytes = bytes.fromhex(issuer_id.removeprefix("0x"))
    key_bytes = bytes.fromhex(doc_key.removeprefix("0x"))
    if len(issuer_bytes) != 32 or len(key_bytes) != 32:
        raise ValueError("issuerId and docKey must each be bytes32")
    return "0x" + keccak_bytes(issuer_bytes + key_bytes).hex()


def proposal_id(domain: WalletDomain, proposal: GovernanceProposal) -> str:
    parts = [
        int(domain.chain_id).to_bytes(32, "big"),
        bytes.fromhex(domain.verifying_contract[2:]).rjust(32, b"\0"),
        proposal.action.to_bytes(32, "big"),
        bytes.fromhex(proposal.issuer_id[2:]),
        bytes.fromhex(proposal.key_id[2:]),
        bytes.fromhex(proposal.signer[2:]).rjust(32, b"\0"),
        bytes.fromhex(proposal.metadata_hash[2:]),
        int(proposal.nonce).to_bytes(32, "big"),
        proposal.deadline.to_bytes(32, "big"),
    ]
    return "0x" + keccak_bytes(b"".join(parts)).hex()


def original_bytes(message: PublishMessage, content: PaymentContent | OfficialContent) -> bytes:
    return canonical_json_bytes(
        {
            "format": "originproof.original.v1",
            "issuer_id": message.issuer_id,
            "doc_key": message.doc_key,
            "document_id": message.document_id,
            "version": message.version,
            "issued_at": message.issued_at,
            "expires_at": message.expires_at,
            "content": content,
        }
    )


def validate_content(message: PublishMessage, content: PaymentContent | OfficialContent) -> None:
    if message.document_id != document_id(message.issuer_id, message.doc_key):
        raise ValueError("DOCUMENT_ID_MISMATCH")
    if message.signature_schema != SIGNATURE_SCHEMA:
        raise ValueError("SIGNATURE_SCHEMA_UNSUPPORTED")
    if message.content_schema != CONTENT_SCHEMAS[content.notice_type]:
        raise ValueError("CONTENT_SCHEMA_MISMATCH")
    if message.protected_hash != "0x" + hashlib.sha256(canonical_json_bytes(content)).hexdigest():
        raise ValueError("PROTECTED_HASH_MISMATCH")
    if message.original_hash != "0x" + hashlib.sha256(original_bytes(message, content)).hexdigest():
        raise ValueError("ORIGINAL_HASH_MISMATCH")
    if (
        isinstance(content, PaymentContent)
        and not message.issued_at < content.due_at <= message.expires_at
    ):
        raise ValueError("PAYMENT_DUE_AT_INVALID")


def type_string(primary_type: str) -> str:
    return (
        primary_type
        + "("
        + ",".join(f"{kind} {name}" for name, kind in EIP712_TYPES[primary_type])
        + ")"
    )


def struct_hash(primary_type: str, value: dict) -> bytes:
    # This contract has only fixed flat structs; no general EIP-712 encoder is introduced.
    encoded = bytearray(keccak_bytes(type_string(primary_type).encode("ascii")))
    for name, kind in EIP712_TYPES[primary_type]:
        item = value[name]
        if kind == "string":
            word = keccak_bytes(item.encode("utf-8"))
        elif kind == "bytes32":
            word = bytes.fromhex(item.removeprefix("0x"))
        elif kind == "address":
            word = bytes.fromhex(item.removeprefix("0x")).rjust(32, b"\0")
        else:
            integer = int(item)
            if not 0 <= integer < 2 ** int(kind[4:]):
                raise ValueError("integer outside EIP-712 type range")
            word = integer.to_bytes(32, "big")
        if len(word) != 32:
            raise ValueError("invalid EIP-712 word width")
        encoded.extend(word)
    return keccak_bytes(bytes(encoded))


def typed_data(
    domain: WalletDomain, message: PublishMessage | RevokeMessage | KeyProofMessage
) -> dict:
    primary_type = {
        PublishMessage: "Publish",
        RevokeMessage: "Revoke",
        KeyProofMessage: "KeyProof",
    }[type(message)]
    return {
        "types": {
            name: [{"name": key, "type": kind} for key, kind in EIP712_TYPES[name]]
            for name in ("EIP712Domain", primary_type)
        },
        "primaryType": primary_type,
        "domain": domain.model_dump(by_alias=True),
        "message": message.model_dump(by_alias=True),
    }


def wallet_digest(
    domain: WalletDomain, message: PublishMessage | RevokeMessage | KeyProofMessage
) -> str:
    data = typed_data(domain, message)
    digest = keccak_bytes(
        b"\x19\x01"
        + struct_hash("EIP712Domain", data["domain"])
        + struct_hash(data["primaryType"], data["message"])
    )
    return "0x" + digest.hex()


def wallet_signer(domain: WalletDomain, message, signature: str) -> str | None:
    try:
        raw = bytes.fromhex(signature.removeprefix("0x"))
        if len(raw) != 65 or raw[64] not in (27, 28):
            return None
        r, s = int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:64], "big")
        if not 0 < r < SECPK1_N or not 0 < s <= SECPK1_N // 2:
            return None
        normalized = raw[:64] + bytes([raw[64] - 27])
        digest = bytes.fromhex(wallet_digest(domain, message)[2:])
        return keys.Signature(normalized).recover_public_key_from_msg_hash(digest).to_address()
    except (BadSignature, ValidationError, ValueError, TypeError):
        return None
