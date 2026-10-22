"""D consumes the fixed C63 verifier/fixtures; synthetic RPC only, no service API or live chain."""

import base64
import hashlib
import importlib.util
import json
import os
import socket
import subprocess
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[2]
C63_SHA = "68ea0c20718937cd0c93d683e3cfa9b3995a9666"
SOURCE_HASHES = {
    "scripts/verify_wallet_document.py": (
        "eb372ece30dfc45f4ae9e42f522d1a0f72e7c2302b2070734fdf5bf9eedd2621"
    ),
    "scripts/ci/test_wallet_independent_verifier.py": (
        "c03dfa765ebdf2f23e7005eddd8a8376e7db5427472cffd132a4aaf9d6e23393"
    ),
    "fixtures/golden/wallet_contract_v1.json": (
        "ada26c10bf4a0efb22c106607198bf8818288421784dfd73b479a84d708ab561"
    ),
    "packages/contracts/abi/IOriginProofWalletRegistry.json": (
        "93c65d4c94b0f44c7864748a2ef824df75f2c0bfa17a098fef48a114066cca1b"
    ),
}


@pytest.fixture(scope="session")
def c63_support(tmp_path_factory):
    supplied = os.environ.get("D_C63_SOURCE_DIR")
    root = Path(supplied) if supplied else tmp_path_factory.mktemp("immutable-c63")
    for path, digest in SOURCE_HASHES.items():
        target = root / path
        if not supplied:
            blob = subprocess.check_output(["git", "show", f"{C63_SHA}:{path}"], cwd=ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(blob)
        assert hashlib.sha256(target.read_bytes()).hexdigest() == digest, "C63 source changed"
    spec = importlib.util.spec_from_file_location(
        "d_c63_fixture_support", root / "scripts/ci/test_wallet_independent_verifier.py"
    )
    support = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(support)
    return support


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(socket.socket, "connect", lambda *a: pytest.fail("no network in D RPC QA"))


@pytest.fixture(params=["PAYMENT_REQUEST", "OFFICIAL_DOCUMENT"])
def source(c63_support, tmp_path, request):
    # Reuse C's synthetic signed original/ABI fixture, keeping its contribution distinct.
    case = c63_support.source.__wrapped__(tmp_path, request)
    case.verifier = c63_support.module
    original = case.transport
    case.urls = []

    async def only_rpc(request):
        case.urls.append(str(request.url))
        assert request.url.host == "rpc.invalid" and request.url.path == "/"
        assert request.method == "POST"
        assert json.loads(request.content)["method"].startswith("eth_")
        return await original.handle_async_request(request)

    case.transport = httpx.MockTransport(only_rpc)
    return case


async def run(source):
    return await source.verifier.verify(source.args, transport=source.transport)


@pytest.mark.parametrize(
    "change,reason",
    [
        ("candidate", "PROTECTED_FIELDS_MISMATCH"),
        ("signature", "INVALID_SIGNATURE"),
        ("chain_hash", "CHAIN_COMMITMENT_MISMATCH"),
        ("key_signer", "INVALID_SIGNATURE"),
    ],
)
async def test_received_fields_signature_and_chain_commitments_are_independent(
    source, change, reason
):
    assert (await run(source)).verification_status == "VERIFIED"
    if change == "candidate":
        value = json.loads(source.paths["candidate"].read_text())
        field = "amount_minor" if "amount_minor" in value else "title"
        value[field] = value[field] + 1 if field == "amount_minor" else "Changed synthetic title"
        source.paths["candidate"].write_text(json.dumps(value))
        source.args.original, source.args.candidate = None, str(source.paths["candidate"])
    elif change == "signature":
        value = json.loads(source.paths["material"].read_text())
        value["signature"] = "0x" + "00" * 65
        source.paths["material"].write_text(json.dumps(value))
    elif change == "chain_hash":
        source.returns["getDocument(bytes32,uint64)"][4] = "0x" + "ed" * 32
    else:
        source.returns["getKey(bytes32)"][1] = "0x" + "34" * 20
    result = await run(source)
    assert result.verification_status == "TAMPERED"
    assert reason in result.reason_codes
    assert any(c.status == "FAILED" and c.reason_code == reason for c in result.checks)


async def test_exported_material_original_is_validated_before_rpc(source):
    material = json.loads(source.paths["material"].read_text())
    material["signing_request"]["original_base64"] = base64.b64encode(
        b"altered synthetic export"
    ).decode()
    source.paths["material"].write_text(json.dumps(material))
    with pytest.raises(ValueError):
        await run(source)
    assert not source.calls


async def test_partial_received_fields_do_not_become_full_comparison(source):
    content = json.loads(source.paths["candidate"].read_text())
    content.pop("amount_minor" if "amount_minor" in content else "title")
    source.paths["candidate"].write_text(json.dumps(content))
    source.args.original, source.args.candidate = None, str(source.paths["candidate"])
    result = await run(source)
    assert result.verification_status == "INCONCLUSIVE"
    assert result.comparison_scope == "PARTIAL_COMPARISON"
    assert "CONTENT_PARTIALLY_COMPARED" in result.reason_codes


@pytest.mark.parametrize("failure", ["offline", "chain_mismatch", "no_code"])
async def test_prior_success_cannot_replace_current_rpc_failure_and_recovery(source, failure):
    assert (await run(source)).verification_status == "VERIFIED"
    before = len(source.calls)
    source.flags[failure] = True
    failed = await run(source)
    assert failed.verification_status == "INCONCLUSIVE"
    assert "CHAIN_UNAVAILABLE" in failed.reason_codes
    assert failed.document is None
    assert len(source.calls) > before
    source.flags.clear()
    assert (await run(source)).verification_status == "VERIFIED"
    assert source.urls and all(url == "http://rpc.invalid/" for url in source.urls)


@pytest.mark.parametrize("state,code", [("REVOKED", 2), ("SUPERSEDED", 3)])
async def test_historical_signature_does_not_reactivate_a_version(source, state, code):
    source.returns["getDocument(bytes32,uint64)"][11] = code
    if state == "SUPERSEDED":
        source.returns["latestVersion(bytes32)"][0] = 2
    result = await run(source)
    assert result.verification_status == "VERIFIED"
    assert result.document.state == state
    assert result.document.latest_version == (2 if state == "SUPERSEDED" else 1)
    assert result.comparison_scope == "FULL_COMPARISON"

