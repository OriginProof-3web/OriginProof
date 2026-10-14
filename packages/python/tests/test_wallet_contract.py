from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

import pytest
from eth_keys.constants import SECPK1_N
from originproof_core import wallet_contract as models
from originproof_core.wallet_signatures import (
    EIP712_TYPES,
    document_id,
    original_bytes,
    proposal_id,
    typed_data,
    validate_content,
    wallet_digest,
    wallet_signer,
)
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[3]
GOLDEN = json.loads((ROOT / "fixtures/golden/wallet_contract_v1.json").read_text())
MESSAGE_MODELS = {
    "Publish": models.PublishMessage,
    "Revoke": models.RevokeMessage,
    "KeyProof": models.KeyProofMessage,
}


def objects(vector):
    data = vector["typed_data"]
    return (
        models.WalletDomain.model_validate(data["domain"]),
        MESSAGE_MODELS[data["primaryType"]].model_validate(data["message"]),
    )


@pytest.mark.parametrize("vector", GOLDEN["vectors"], ids=lambda v: v["label"])
def test_fixed_signing_vectors_and_domain_separation(vector):
    domain, message = objects(vector)
    assert typed_data(domain, message) == vector["typed_data"]
    assert wallet_digest(domain, message) == vector["digest"]
    assert wallet_signer(domain, message, vector["signature"]) == vector["expected_signer"]
    changed_chain = domain.model_copy(update={"chain_id": "1"})
    changed_contract = domain.model_copy(update={"verifying_contract": "0x" + "34" * 20})
    assert wallet_signer(changed_chain, message, vector["signature"]) != vector["expected_signer"]
    assert (
        wallet_signer(changed_contract, message, vector["signature"]) != vector["expected_signer"]
    )
    changed_deadline = message.model_copy(update={"deadline": message.deadline + 1})
    assert wallet_signer(domain, changed_deadline, vector["signature"]) != vector["expected_signer"]


@pytest.mark.parametrize("vector", GOLDEN["vectors"][:2], ids=lambda v: v["label"])
def test_original_and_protected_content_are_separate_commitments(vector):
    _, message = objects(vector)
    model = (
        models.PaymentContent if vector["label"] == "PAYMENT_REQUEST" else models.OfficialContent
    )
    content = model.model_validate(vector["protected_content"])
    validate_content(message, content)
    assert original_bytes(message, content) == base64.b64decode(vector["original_base64"])
    assert message.document_id == document_id(message.issuer_id, message.doc_key)
    assert message.original_hash != message.protected_hash
    changed = content.model_copy(update={"official_url": "https://example.invalid/changed"})
    with pytest.raises(ValueError, match="PROTECTED_HASH_MISMATCH"):
        validate_content(message, changed)
    raw = original_bytes(message, content) + b"\n"
    assert "0x" + hashlib.sha256(raw).hexdigest() != message.original_hash
    with pytest.raises(ValueError, match="DOCUMENT_ID_MISMATCH"):
        validate_content(message.model_copy(update={"document_id": "0x" + "01" * 32}), content)


@pytest.mark.parametrize(
    "field,value",
    [
        ("action", True),
        ("version", True),
        ("version", 0),
        ("version", 2**53),
        ("nonce", "01"),
        ("nonce", str(2**256)),
        ("nonce", 1),
        ("deadline", 1791936000),
        ("deadline", 1792540801),
        ("originalHashAlgorithm", True),
        ("unexpected_field", "ignored"),
    ],
)
def test_protocol_validation_rejects_ambiguous_or_unsafe_inputs(field, value):
    raw = dict(GOLDEN["vectors"][0]["typed_data"]["message"])
    raw[field] = value
    with pytest.raises(ValidationError):
        models.PublishMessage.model_validate(raw)


def test_account_unicode_and_url_boundaries():
    raw = dict(GOLDEN["vectors"][0]["protected_content"])
    raw["payee_account_number"] = "00-1234 567890"
    assert models.PaymentContent.model_validate(raw).payee_account_number == "001234567890"
    for field, value in [
        ("amount_minor", True),
        ("amount_minor", 1.5),
        ("payee_account_number", "００１２３４５６"),
        ("payee_account_number", "　00123456"),
        ("official_url", "http://example.invalid"),
        ("official_url", "https://user:password@example.invalid"),
        ("payee_account_holder", " "),
        ("payment_purpose", chr(0xD800)),
    ]:
        with pytest.raises(ValidationError):
            models.PaymentContent.model_validate({**raw, field: value})
    raw["payee_account_holder"] = "  가  "
    assert models.PaymentContent.model_validate(raw).payee_account_holder == "가"


def test_signature_recovery_rejects_malleability_and_invalid_encoding():
    vector = GOLDEN["vectors"][0]
    domain, message = objects(vector)
    raw = bytes.fromhex(vector["signature"][2:])
    s = int.from_bytes(raw[32:64], "big")
    high_s = raw[:32] + (SECPK1_N - s).to_bytes(32, "big") + raw[64:]
    for signature in ("0x", "0xzz", "0x" + high_s.hex(), "0x" + (raw[:64] + b"\x00").hex()):
        assert wallet_signer(domain, message, signature) is None


def test_scope_prevents_id_lookup_from_claiming_content_input():
    raw = {
        "request_id": "req_scope",
        "document_id": GOLDEN["vectors"][0]["typed_data"]["message"]["documentId"],
        "scope": "ID_ONLY",
    }
    models.VerificationRequest.model_validate(raw)
    for extra in ({"candidate": {"amount_minor": 154000}}, {"original_ref": "artifact_001"}):
        with pytest.raises(ValidationError):
            models.VerificationRequest.model_validate({**raw, **extra})
    with pytest.raises(ValidationError):
        models.VerificationRequest.model_validate({**raw, "scope": "PROTECTED_FIELDS"})


def test_signing_request_preserves_original_and_action_binding():
    vector = GOLDEN["vectors"][0]
    raw = {
        "signing_request_id": "wsr_synthetic",
        "primary_type": "Publish",
        "domain": vector["typed_data"]["domain"],
        "message": vector["typed_data"]["message"],
        "expected_signer": vector["expected_signer"],
        "original_base64": vector["original_base64"],
        "content": vector["protected_content"],
    }
    models.SigningRequest.model_validate(raw)
    for change in (
        {"primary_type": "Revoke"},
        {"original_base64": base64.b64encode(b"changed").decode()},
        {"content": {**raw["content"], "amount_minor": 154001}},
    ):
        with pytest.raises(ValidationError):
            models.SigningRequest.model_validate({**raw, **change})


def test_governance_identifier_and_unexecuted_analysis_are_explicit():
    data = GOLDEN["governance"]
    domain = models.WalletDomain.model_validate(data["domain"])
    proposal = models.GovernanceProposal.model_validate(data["proposal"])
    assert proposal_id(domain, proposal) == data["proposal_id"]
    assert proposal_id(domain, proposal.model_copy(update={"nonce": "1"})) != data["proposal_id"]
    raw = {"risk_level": "UNDETERMINED", "evidence": [], "limitations": ["입력 지원 미정"]}
    with pytest.raises(ValidationError):
        models.AnalysisReport.model_validate(raw)
    models.AnalysisReport.model_validate(
        {**raw, "verification_not_run_reason": "NO_DOCUMENT_REFERENCE"}
    )


def test_evidence_and_identifier_boundaries_preserve_original_quotes():
    raw = {
        "rule_id": "SYNTHETIC",
        "quote": "가",
        "start_offset": 0,
        "end_offset": 2,
        "source": "RULE",
    }
    assert models.AnalysisEvidence.model_validate(raw).quote == "가"
    for change in ({"end_offset": None}, {"end_offset": 0}, {"start_ms": 5, "end_ms": 4}):
        with pytest.raises(ValidationError):
            models.AnalysisEvidence.model_validate({**raw, **change})
    with pytest.raises(ValueError, match="bytes32"):
        document_id("0x" + "01" * 31, "0x" + "02" * 33)
    result = {
        "session_id": "vsn_synthetic",
        "verification_status": "INCONCLUSIVE",
        "comparison_scope": "ID_ONLY",
        "checks": [],
        "reason_codes": ["CONTENT_NOT_COMPARED"],
        "checked_at": 1791936000,
        "chain_id": "31337",
        "verifying_contract": "0x" + "12" * 20,
    }
    models.VerificationResult.model_validate(result)
    with pytest.raises(ValidationError):
        models.VerificationResult.model_validate({**result, "verification_status": "VERIFIED"})


def test_generated_types_openapi_and_abi_share_one_field_order():
    api = json.loads(
        (ROOT / "packages/schemas/generated/openapi/wallet-contract.openapi.json").read_text()
    )
    assert api["info"]["version"] == models.REVISION
    for path in api["paths"].values():
        for operation in path.values():
            assert operation["x-implementation-status"] == "PLANNED"
    abi = json.loads((ROOT / "packages/contracts/abi/IOriginProofWalletRegistry.json").read_text())
    for primary, method in (("Publish", "publish"), ("Revoke", "revoke")):
        function = next(item for item in abi if item.get("name") == method)
        components = function["inputs"][0]["components"]
        assert [(c["name"], c["type"]) for c in components] == EIP712_TYPES[primary]
    proposal = next(item for item in abi if item.get("name") == "propose")
    assert [(c["name"], c["type"]) for c in proposal["inputs"][1]["components"]] == EIP712_TYPES[
        "KeyProof"
    ]
