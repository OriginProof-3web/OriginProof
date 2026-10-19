"""Validate D's QA data, not unimplemented v2 API/chain behavior."""

import json
import re
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import pytest
from originproof_core import SignedProofEnvelope, payload_hash

ROOT = Path(__file__).resolve().parents[3]
DATA = json.loads((ROOT / "fixtures/finals/cases.json").read_text())


@pytest.mark.parametrize("kind,profile", DATA["profiles"].items())
def test_unsigned_profiles_obey_adr_binding_and_payload_contract(kind, profile):
    envelope = profile["envelope_fields"]
    payload = envelope["payload"]
    context = profile["binding_input"]
    assert envelope["schema_version"] == "2.0.0"
    assert envelope["app_domain"] == "originproof.finals"
    assert envelope["proof_type"] == kind
    properties = SignedProofEnvelope.model_json_schema()["properties"]
    for field in ("proof_id", "issuer_id", "key_id"):
        assert re.fullmatch(properties[field]["pattern"], envelope[field])
    assert "signature" not in envelope  # C owns signed Golden generation.
    assert envelope["payload_hash"] == payload_hash(payload)
    assert envelope["subject_binding_hash"] == payload_hash(context)
    assert context["proof_id"] == envelope["proof_id"]
    assert len(bytes.fromhex(context["salt"])) == 32
    assert payload_hash({**context, "proof_id": "different_proof"}) != payload_hash(context)
    assert datetime.fromisoformat(envelope["issued_at"]) < datetime.fromisoformat(
        envelope["expires_at"]
    )
    if kind == "PAYMENT_REQUEST":
        assert type(payload["amount_minor"]) is int and payload["amount_minor"] > 0
        assert payload["currency"] == "KRW"
        assert envelope["single_use"] is True
        assert payload["payer_binding"] == envelope["subject_binding_hash"]
        assert payload["beneficiary_binding"] == payload_hash(
            {
                "binding_domain": "originproof.beneficiary.v1",
                "app_domain": envelope["app_domain"],
                "chain_id": envelope["chain_id"],
                "issuer_id": envelope["issuer_id"],
            }
        )
    else:
        assert envelope["single_use"] is False
        assert payload["subject_token"] == envelope["subject_binding_hash"]
        assert type(payload["version"]) is int and payload["version"] > 0
        assert all(
            payload[name].strip()
            for name in ("institution_code", "document_type", "document_number")
        )


@pytest.mark.parametrize("case", DATA["cases"], ids=lambda c: c["id"])
def test_case_inputs_are_reproducible_and_do_not_claim_execution(case):
    assert case["execution_status"] == "NOT_RUN"
    assert case["actor"] and case["action"] and case["basis"]
    envelope = DATA["profiles"][case["profile"]]["envelope_fields"]
    patch = case["changes"].get("observed_patch")
    if patch:
        before = envelope["payload"]
        observed = {**deepcopy(before), **patch}
        assert len(patch) == 1
        assert {k for k in observed if before.get(k) != observed[k]} == set(patch)
        assert payload_hash(observed) != envelope["payload_hash"]
        assert case["expected"]["verification_status"] == "TAMPERED"
    if "clock" in case["changes"]:
        at = datetime.fromisoformat(case["changes"]["clock"])
        start = datetime.fromisoformat(envelope["issued_at"])
        end = datetime.fromisoformat(envelope["expires_at"])
        assert case["expected"]["usable"] == (start <= at < end)
        assert case["expected"]["verification_status"] == "VERIFIED"
    for name in case["changes"].get("omitted_observed_fields", []):
        assert name in envelope["payload"]


def test_manifest_has_unique_cases_and_preserves_both_synthetic_issuers():
    cases = DATA["cases"]
    assert DATA["source"] == "synthetic"
    assert len({c["id"] for c in cases}) == len(cases)
    assert {p["issuer_name"] for p in DATA["profiles"].values()} == {
        "Origin Mock Bank",
        "Origin Mock Office",
    }
    for kind in DATA["profiles"]:
        selected = [c for c in cases if c["profile"] == kind]
        assert any(c["acceptance"] == "F01" for c in selected)
        assert any("observed_patch" in c["changes"] for c in selected)
        boundaries = [c for c in selected if "clock" in c["changes"]]
        assert len(boundaries) == 3
        assert {c["expected"]["usable"] for c in boundaries} == {True, False}
