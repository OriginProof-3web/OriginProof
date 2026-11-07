"""Build unsigned, synthetic ADR 0001 QA inputs; never generate signing keys."""

from __future__ import annotations

import json
from pathlib import Path

from originproof_core import payload_hash

BASE_SHA = "3295a71c10a1a99c523d3cfefde91b5737b737ac"


def build_cases() -> dict:
    profiles = {}
    for kind, issuer, proof, single_use in (
        ("PAYMENT_REQUEST", "iss_origin_mock_bank", "prf_synthetic_payment_001", True),
        ("OFFICIAL_DOCUMENT", "iss_origin_mock_office", "prf_synthetic_document_001", False),
    ):
        context = {
            "binding_domain": "originproof.recipient.v1",
            "app_domain": "originproof.finals",
            "chain_id": 31337,
            "proof_id": proof,
            "recipient_token": "SYNTHETIC_PUBLIC_TEST_TOKEN",
            "salt": "ab" * 32,
        }
        binding = payload_hash(context)
        if single_use:
            payload = {
                "amount_minor": 154000,
                "currency": "KRW",
                "payer_binding": binding,
                "beneficiary_binding": payload_hash(
                    {
                        "binding_domain": "originproof.beneficiary.v1",
                        "app_domain": context["app_domain"],
                        "chain_id": context["chain_id"],
                        "issuer_id": issuer,
                    }
                ),
                "target_hash": payload_hash(
                    {
                        "target_domain": "originproof.target.v1",
                        "target_ref": "SYNTHETIC_REQUEST_001",
                    }
                ),
            }
        else:
            payload = {
                "institution_code": "SYNTHETIC_OFFICE",
                "document_type": "SYNTHETIC_NOTICE",
                "document_number": "SYNTHETIC_DOC_001",
                "subject_token": binding,
                "version": 1,
            }
        profiles[kind] = {
            "issuer_name": "Origin Mock Bank" if single_use else "Origin Mock Office",
            "binding_input": context,
            "envelope_fields": {
                "proof_id": proof,
                "issuer_id": issuer,
                "key_id": "key_" + issuer.removeprefix("iss_") + "_001",
                "proof_type": kind,
                "schema_version": "2.0.0",
                "signature_scheme": "ECDSA_SECP256K1_KECCAK256_V1",
                "chain_id": 31337,
                "app_domain": "originproof.finals",
                "payload": payload,
                "payload_hash": payload_hash(payload),
                "subject_binding_hash": binding,
                "issued_at": "2026-10-01T00:00:00Z",
                "expires_at": "2026-10-02T00:00:00Z",
                "nonce": "SYNTHETIC_NONCE_" + kind,
                "single_use": single_use,
                "metadata_hash": None,
            },
        }
    cases = []

    def add(case_id, acceptance, profile, actor, action, changes, expected, basis):
        cases.append(
            {
                "id": case_id,
                "acceptance": acceptance,
                "profile": profile,
                "actor": actor,
                "action": action,
                "changes": changes,
                "expected": expected,
                "basis": basis,
                "execution_status": "NOT_RUN",
            }
        )

    for kind in profiles:
        add(
            kind + "_normal",
            "F01",
            kind,
            "designated_recipient",
            "full_comparison",
            {},
            {"verification_status": "VERIFIED", "lifecycle_status": "ACTIVE"},
            "ADR 0001 §4",
        )
        field, value, reason = (
            ("amount_minor", 1540000, "AMOUNT_MISMATCH")
            if kind == "PAYMENT_REQUEST"
            else ("document_number", "SYNTHETIC_DOC_002", "FIELD_MISMATCH")
        )
        add(
            kind + "_tampered",
            "F02",
            kind,
            "designated_recipient",
            "full_comparison",
            {"observed_patch": {field: value}},
            {"verification_status": "TAMPERED", "reason_codes": [reason]},
            "ADR 0001 §4",
        )
        add(
            kind + "_missing",
            "F02",
            kind,
            "designated_recipient",
            "partial_comparison",
            {"omitted_observed_fields": [field]},
            {"verification_status": "INCONCLUSIVE", "reason_codes": ["INPUT_INCOMPLETE"]},
            "ADR 0001 §4: no mismatch, missing required comparison",
        )
        for suffix, at, inside in (
            ("at_issue", "2026-10-01T00:00:00Z", True),
            ("before_expiry", "2026-10-01T23:59:59Z", True),
            ("at_expiry", "2026-10-02T00:00:00Z", False),
        ):
            add(
                kind + "_" + suffix,
                "F03",
                kind,
                "designated_recipient",
                "full_comparison",
                {"clock": at},
                {
                    "verification_status": "VERIFIED",
                    "lifecycle_status": "ACTIVE" if inside else "EXPIRED",
                    "usable": inside,
                },
                "ADR 0001 §1/4: [issued_at, expires_at)",
            )
    for target in ("proof", "issuer"):
        add(
            "unknown_" + target,
            "F06",
            "PAYMENT_REQUEST",
            "anonymous",
            "public_lookup",
            {"missing_registry_record": target},
            {"verification_status": "NOT_REGISTERED"},
            "Plan §16 F06; do not label as forgery",
        )
    add(
        "cross_issuer_write",
        "F05",
        "OFFICIAL_DOCUMENT",
        "bank_issuer",
        "revoke",
        {},
        {"decision": "DENY", "target_state_unchanged": True},
        "ADR 0001 §5/6",
    )
    for action in ("issue", "register_key"):
        add(
            "pending_" + action,
            "F09",
            "PAYMENT_REQUEST",
            "bank_issuer",
            action,
            {"application_state": "PENDING"},
            {"decision": "DENY"},
            "Plan §16 F09",
        )
    for actor, action in (
        ("anonymous", "approve"),
        ("recipient", "approve"),
        ("issuer_self", "approve"),
        ("anonymous", "consume"),
    ):
        add(
            actor + "_" + action,
            "F10",
            "PAYMENT_REQUEST",
            actor,
            action,
            {"untrusted_request": {"role": "operator", "issuer_id": "iss_origin_mock_office"}},
            {"decision": "DENY", "target_state_unchanged": True},
            "ADR 0001 §2/6",
        )
    for suffix, changes, reason in (
        (
            "recipient",
            {"authenticated_recipient": "different_recipient"},
            "SUBJECT_BINDING_MISMATCH",
        ),
        ("domain", {"envelope_patch": {"app_domain": "originproof.mvp"}}, "DOMAIN_MISMATCH"),
        ("network", {"envelope_patch": {"chain_id": 31338}}, "NETWORK_MISMATCH"),
    ):
        add(
            "wrong_" + suffix,
            "F14",
            "PAYMENT_REQUEST",
            "designated_recipient",
            "full_comparison",
            changes,
            {"must_not_be_verified": True, "reason_basis": reason},
            "ADR 0001 §4/5; permission rejection may precede verification response",
        )
    for suffix, changes in (
        ("expired_session", {"session_age_seconds": 28800}),
        ("logged_out", {"session_revoked": True}),
        ("missing_csrf", {"csrf_present": False}),
    ):
        add(
            suffix,
            "F10",
            "PAYMENT_REQUEST",
            "bank_issuer",
            "create_application",
            changes,
            {"decision": "DENY", "target_state_unchanged": True},
            "ADR 0001 §2",
        )
    add(
        "document_consume",
        "F04",
        "OFFICIAL_DOCUMENT",
        "designated_recipient",
        "consume",
        {},
        {"decision": "DENY", "target_state_unchanged": True},
        "ADR 0001 §1/6",
    )
    return {
        "source": "synthetic",
        "fixture_version": "1.0.0",
        "target_schema_version": "2.0.0",
        "basis_sha": BASE_SHA,
        "purpose": (
            "W1-D2 unsigned QA inputs; "
            "not generated v2 Schema, signed Golden or live results"
        ),
        "preconditions": [
            "valid owner-generated signature",
            "active issuer and key",
            "registered Proof on matching deployment",
            "authorized actor",
            "valid session and CSRF for mutations",
            "clock inside validity unless overridden",
        ],
        "profiles": profiles,
        "cases": cases,
    }


if __name__ == "__main__":
    Path(__file__).with_name("cases.json").write_text(
        json.dumps(build_cases(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
