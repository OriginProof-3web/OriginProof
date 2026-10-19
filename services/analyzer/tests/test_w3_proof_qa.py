"""D independent core QA; synthetic trust is not RPC/API/browser acceptance."""

import hashlib
import importlib.util
import json
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from originproof_core import IssuerRecord, KeyRecord, payload_hash, signer_address, signing_digest
from originproof_core.finals import FinalsSignedProofEnvelope
from originproof_core.finals_verification import evaluate_finals
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[3]
DATA = json.loads((ROOT / "fixtures/finals/w3_cases.json").read_text())


@pytest.mark.parametrize("case", DATA["cases"], ids=lambda c: c["id"])
def test_w3_case(case):
    profile = DATA["profiles"][case["profile"]]
    path = ROOT / profile["golden"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == profile["sha256"]
    vector = json.loads(path.read_text())
    raw = deepcopy(vector["envelope"])
    changes = case["changes"]
    raw.update(changes.get("envelope_patch", {}))
    raw["payload"].update(changes.get("payload_patch", {}))
    if changes.get("rehash_payload"):
        raw["payload_hash"] = payload_hash(raw["payload"])
    if case["layer"] == "input_model":
        with pytest.raises(ValidationError):
            FinalsSignedProofEnvelope.model_validate(raw)
        return
    envelope = FinalsSignedProofEnvelope.model_validate(raw)
    key_values = {
        "key_id": envelope.key_id,
        "issuer_id": envelope.issuer_id,
        "signer": vector["signer"],
        "status": "ACTIVE",
        "valid_from": envelope.issued_at,
        "valid_until": envelope.expires_at,
    }
    key_values.update(changes.get("key_patch", {}))
    candidate = envelope.payload.model_dump(mode="json")
    candidate.update(changes.get("candidate_patch", {}))
    for field in changes.get("omit_candidate", []):
        candidate.pop(field)
    if "candidate" in changes:
        candidate = changes["candidate"]
    result = evaluate_finals(
        envelope,
        request_id="req_" + case["id"],
        chain_id=changes.get("chain_id", 31337),
        issuer=None
        if "issuer" in changes
        else IssuerRecord(issuer_id=envelope.issuer_id, status="ACTIVE"),
        key=None if "key" in changes else KeyRecord.model_validate(key_values),
        candidate=candidate,
        now=datetime.fromisoformat(changes["now"])
        if "now" in changes
        else envelope.issued_at + timedelta(hours=1),
    )
    expected = case["expected"]
    assert result.verification_status == expected["verification_status"]
    assert result.scope == expected["scope"]
    assert result.reason_codes == expected["reason_codes"]
    for name, state in expected["checks"].items():
        assert result.checks[name] == state
    assert result.lifecycle_status is None and result.checks["proof_status"] == "NOT_RUN"
    assert case["live_execution_status"] == "NOT_RUN"


def test_w3_manifest_reproduces_and_preserves_signed_goldens():
    spec = importlib.util.spec_from_file_location(
        "w3_qa_builder", ROOT / "fixtures/finals/build_w3_cases.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.build_cases() == DATA
    assert DATA["source"] == "synthetic"
    assert len({case["id"] for case in DATA["cases"]}) == len(DATA["cases"])
    for profile in DATA["profiles"].values():
        vector = json.loads((ROOT / profile["golden"]).read_text())
        envelope = FinalsSignedProofEnvelope.model_validate(vector["envelope"])
        assert payload_hash(envelope.payload) == envelope.payload_hash
        assert signing_digest(envelope) == vector["signing_digest"]
        assert signer_address(envelope) == vector["signer"]
    for case in DATA["cases"]:
        if "candidate_patch" in case["changes"] and "single_field_changed" in case["id"]:
            assert len(case["changes"]["candidate_patch"]) == 1
