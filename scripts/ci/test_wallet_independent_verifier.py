"""Direct-RPC verifier checks using synthetic ABI replies, no service API or paid provider."""

import base64
import hashlib
import json
import time
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from eth_keys import keys
from originproof_core.canonicalization import canonical_json_bytes
from originproof_core.wallet_contract import (
    OfficialContent,
    PaymentContent,
    PublishMessage,
    SigningRequest,
    VerificationMaterial,
    WalletDomain,
)
from originproof_core.wallet_signatures import keccak_bytes, original_bytes, wallet_digest

from scripts import verify_wallet_document as module

ROOT = Path(__file__).resolve().parents[2]


def word(value):
    if isinstance(value, int):
        return value.to_bytes(32)
    raw = bytes.fromhex(value[2:])
    return raw.rjust(32, b"\x00")


@pytest.fixture(params=["PAYMENT_REQUEST", "OFFICIAL_DOCUMENT"])
def source(tmp_path, request):
    golden = json.loads((ROOT / "fixtures/golden/wallet_contract_v1.json").read_text())
    vector = next(v for v in golden["vectors"] if v["label"] == request.param)
    stamp = int(time.time()) - 60
    model = PaymentContent if request.param == "PAYMENT_REQUEST" else OfficialContent
    data = dict(vector["protected_content"])
    if "due_at" in data:
        data["due_at"] = stamp + 1800
    content = model.model_validate(data)
    message = PublishMessage.model_validate(vector["typed_data"]["message"]).model_copy(
        update={
            "issued_at": stamp,
            "expires_at": stamp + 3600,
            "deadline": stamp + 300,
            "protected_hash": "0x" + hashlib.sha256(canonical_json_bytes(content)).hexdigest(),
        }
    )
    raw = original_bytes(message, content)
    message = message.model_copy(update={"original_hash": "0x" + hashlib.sha256(raw).hexdigest()})
    key = keys.PrivateKey((1).to_bytes(32, "big"))
    signer = key.public_key.to_checksum_address().lower()
    domain = WalletDomain.model_validate(vector["typed_data"]["domain"])
    signature = key.sign_msg_hash(bytes.fromhex(wallet_digest(domain, message)[2:])).to_bytes()
    signature = "0x" + (signature[:64] + bytes([signature[64] + 27])).hex()
    material = VerificationMaterial(
        signing_request=SigningRequest(
            signing_request_id="wsr_independent",
            primary_type="Publish",
            domain=domain,
            message=message,
            expected_signer=signer,
            content=content,
            original_base64=base64.b64encode(raw).decode(),
        ),
        signature=signature,
        block_number="10",
        block_hash="0x" + "ab" * 32,
    )
    metadata = {"issuer_id": message.issuer_id, "name": "Synthetic", "domain": "example.invalid"}
    paths = {name: tmp_path / name for name in ("material", "original", "candidate", "metadata")}
    paths["material"].write_text(material.model_dump_json())
    paths["original"].write_bytes(raw)
    paths["candidate"].write_text(content.model_dump_json())
    paths["metadata"].write_text(json.dumps(metadata))
    returns = {
        "getDocument(bytes32,uint64)": [
            message.issuer_id,
            message.doc_key,
            message.version,
            message.key_id,
            message.original_hash,
            message.protected_hash,
            message.content_schema,
            message.issued_at,
            message.expires_at,
            message.issued_at + 1,
            10,
            1,
        ],
        "latestVersion(bytes32)": [message.version],
        "getIssuer(bytes32)": [
            1,
            message.key_id,
            signer,
            "0x" + hashlib.sha256(canonical_json_bytes(metadata)).hexdigest(),
        ],
        "getKey(bytes32)": [message.issuer_id, signer, 2, 0, 0],
        "nextNonce(bytes32)": [1],
        "governanceNonce(bytes32)": [1],
    }
    calls = []
    flags = {}

    def rpc(request):
        body = json.loads(request.content)
        method, params = body["method"], body["params"]
        calls.append(body)
        tag = hex(flags.get("height", 10))
        if flags.get("offline"):
            return httpx.Response(503)
        if method == "eth_chainId":
            result = hex(int(domain.chain_id) + int(flags.get("chain_mismatch", False)))
        elif method == "eth_getBlockByNumber":
            result = {
                "number": tag,
                "hash": "0x"
                + ("cd" if flags.get("reorg") and params[0] != "latest" else "ab") * 32,
                "timestamp": hex(int(time.time())),
            }
        elif method == "eth_getCode":
            assert params == [domain.verifying_contract, tag]
            result = "0x" if flags.get("no_code") else "0x6000"
        else:
            assert method == "eth_call" and params[1] == tag
            call = params[0]
            assert call["to"] == domain.verifying_contract
            signature = next(
                s for s in returns if call["data"][2:10] == keccak_bytes(s.encode())[:4].hex()
            )
            fields = returns[signature]
            if flags.get("not_registered") and signature.startswith("getDocument"):
                fields = [0] * 12
            if signature.startswith("getDocument"):
                assert call["data"][10:74] == message.document_id[2:]
                assert int(call["data"][74:], 16) == message.version
            result = "0x" + b"".join(word(v) for v in fields).hex()
            if flags.get("malformed_abi"):
                result = "0x01"
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": True if flags.get("bad_id") else body["id"],
                "result": result,
            },
        )

    args = SimpleNamespace(
        material=str(paths["material"]),
        original=str(paths["original"]),
        candidate=None,
        metadata=str(paths["metadata"]),
        registry=domain.verifying_contract,
        chain_id=domain.chain_id,
        rpc_url="http://rpc.invalid",
    )
    return SimpleNamespace(
        args=args,
        paths=paths,
        transport=httpx.MockTransport(rpc),
        flags=flags,
        returns=returns,
        calls=calls,
    )


async def test_original_and_protected_comparison_without_service_api(source):
    result = await module.verify(source.args, transport=source.transport)
    assert result.verification_status == "VERIFIED" and result.comparison_scope == "FULL_COMPARISON"
    assert result.block_number == "10"
    source.args.original, source.args.candidate = None, str(source.paths["candidate"])
    assert (
        await module.verify(source.args, transport=source.transport)
    ).verification_status == "VERIFIED"
    assert all(call["method"].startswith("eth_") for call in source.calls)


@pytest.mark.parametrize(
    "case,expected",
    [
        ("changed_original", "TAMPERED"),
        ("no_metadata", "INCONCLUSIVE"),
        ("id_only", "INCONCLUSIVE"),
        ("offline", "INCONCLUSIVE"),
        ("reorg", "INCONCLUSIVE"),
        ("no_code", "INCONCLUSIVE"),
        ("malformed_abi", "INCONCLUSIVE"),
        ("chain_mismatch", "INCONCLUSIVE"),
        ("not_registered", "NOT_REGISTERED"),
        ("bad_id", "INCONCLUSIVE"),
        ("changed_metadata", "TAMPERED"),
        ("invalid_url", "INCONCLUSIVE"),
    ],
)
async def test_missing_mismatched_and_unavailable_evidence_never_succeeds(source, case, expected):
    if case == "changed_original":
        source.paths["original"].write_bytes(b"synthetic altered original")
    elif case == "no_metadata":
        source.args.metadata = None
    elif case == "id_only":
        source.args.original = None
    elif case == "changed_metadata":
        source.paths["metadata"].write_text('{"name":"changed synthetic name"}')
    elif case == "invalid_url":
        source.args.rpc_url = "http://rpc.invalid:bad"
    else:
        source.flags[case] = True
    result = await module.verify(source.args, transport=source.transport)
    assert result.verification_status == expected
    if case in ("offline", "reorg", "no_code", "malformed_abi", "chain_mismatch"):
        assert "CHAIN_UNAVAILABLE" in result.reason_codes


async def test_incident_warnings_and_retired_historical_key_remain_separate(source):
    source.returns["getIssuer(bytes32)"][0] = 2
    source.flags["height"] = 12
    source.returns["getKey(bytes32)"][3] = 11
    source.returns["getKey(bytes32)"][4] = 10
    result = await module.verify(source.args, transport=source.transport)
    assert result.verification_status == "VERIFIED"
    assert set(result.document.warnings) == {"ISSUER_SUSPENDED", "KEY_COMPROMISED"}
    source.returns["getKey(bytes32)"][3] = 10
    result = await module.verify(source.args, transport=source.transport)
    assert result.verification_status == "INCONCLUSIVE"


async def test_expected_domain_is_independent_of_exported_material(source):
    source.args.registry = "0x" + "34" * 20
    with pytest.raises(ValueError, match="domain mismatch"):
        await module.verify(source.args, transport=source.transport)
    assert not source.calls


@pytest.mark.parametrize("payload", [b'{"DO_NOT_ECHO":"invalid"}', b"x" * 131073])
def test_cli_rejects_invalid_local_material_without_echo(tmp_path, monkeypatch, capsys, payload):
    path = tmp_path / "bad.json"
    path.write_bytes(payload)
    monkeypatch.setattr(
        "sys.argv",
        [
            "verify_wallet_document.py",
            "--material",
            str(path),
            "--rpc-url",
            "http://rpc.invalid",
            "--chain-id",
            "31337",
            "--registry",
            "0x" + "12" * 20,
            "--id-only",
        ],
    )
    assert module.main() == 2
    assert json.loads(capsys.readouterr().out) == {"detail": "INVALID_LOCAL_VERIFICATION_INPUT"}


def test_independent_decoder_tracks_the_compiled_shared_abi():
    abi = json.loads((ROOT / "packages/contracts/abi/IOriginProofWalletRegistry.json").read_text())
    functions = {item["name"]: item for item in abi if item["type"] == "function"}
    expected = {
        "getDocument": [
            "issuerId",
            "docKey",
            "version",
            "keyId",
            "originalHash",
            "protectedHash",
            "contentSchema",
            "issuedAt",
            "expiresAt",
            "publishedAt",
            "publishedBlock",
            "state",
        ],
        "getKey": ["issuerId", "signer", "registeredBlock", "retiredBlock", "compromiseBlock"],
    }
    for name, fields in expected.items():
        assert [v["name"] for v in functions[name]["outputs"][0]["components"]] == fields
    assert [v["type"] for v in functions["getDocument"]["inputs"]] == ["bytes32", "uint64"]
    assert [v["type"] for v in functions["getIssuer"]["outputs"]] == [
        "uint8",
        "bytes32",
        "address",
        "bytes32",
    ]
