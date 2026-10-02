import json
from pathlib import Path

import pytest
from originproof_core import canonical_json_bytes, signer_address, signing_digest
from originproof_core.finals import FinalsSignedProofEnvelope
from originproof_core.signatures import signing_payload
from pydantic import ValidationError

GOLDEN = Path(__file__).resolve().parents[3] / "fixtures/golden"
VECTORS = (
    "payment_request_signing_v2.json",
    "official_document_signing_v2.json",
)


@pytest.fixture(params=VECTORS)
def vector(request):
    data = json.loads((GOLDEN / request.param).read_text())
    return FinalsSignedProofEnvelope.model_validate(data["envelope"]), data


def test_v2_golden_canonical_digest_and_signer_match(vector):
    envelope, data = vector
    assert (
        canonical_json_bytes(signing_payload(envelope)).decode() == data["signing_canonical_json"]
    )
    assert signing_digest(envelope) == data["signing_digest"]
    assert signer_address(envelope) == data["signer"]


def test_chain_id_reuse_changes_digest_and_invalidates_signature(vector):
    envelope, data = vector
    changed = envelope.model_copy(update={"chain_id": 1})
    assert signing_digest(changed) != data["signing_digest"]
    assert signer_address(changed) != data["signer"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("app_domain", "originproof.other"),
        ("schema_version", "2.0.1"),
        ("proof_type", "OFFICIAL_DOCUMENT"),
    ],
)
def test_domain_schema_and_proof_type_reuse_is_rejected(vector, field, value):
    envelope, _ = vector
    raw = envelope.model_dump(mode="json")
    if field == "proof_type" and raw["proof_type"] == value:
        value = "PAYMENT_REQUEST"
    raw[field] = value
    with pytest.raises(ValidationError):
        FinalsSignedProofEnvelope.model_validate(raw)
