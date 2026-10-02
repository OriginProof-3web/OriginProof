import json
from datetime import UTC, datetime

import httpx
import pytest
from infrastructure.blockchain.reader import JsonRpcBlockchainReader, digest
from originproof_core.ports import DependencyUnavailableError

ISSUER = "iss_origin_mock_bank"
KEY = "key_origin_mock_bank_001"
PROOF = "prf_synthetic_w4"
SIGNER = "0x" + "11" * 20
GENESIS_HASH = "0x" + "aa" * 32
DEPLOYMENT_HASH = "0x" + "bb" * 32
CURRENT_HASH = "0x" + "bc" * 32
DEPLOYMENT_ID = "dep_" + "cc" * 32


def word(value):
    return value.to_bytes(32, "big").hex()


@pytest.fixture
def manifest(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(
            {
                "chain_id": 31337,
                "genesis_block_hash": GENESIS_HASH,
                "deployment_id": DEPLOYMENT_ID,
                "deployment_block": 1,
                "deployment_block_hash": DEPLOYMENT_HASH,
                "source_commit_sha": "d" * 40,
                "contracts": {
                    "IssuerRegistry": {
                        "address": "0x" + "22" * 20,
                        "constructor_arguments": ["0x" + "44" * 20],
                        "abi_sha256": "1" * 64,
                    },
                    "IssuerKeyRegistry": {
                        "address": "0x" + "33" * 20,
                        "constructor_arguments": ["0x" + "44" * 20, "0x" + "22" * 20],
                        "abi_sha256": "2" * 64,
                    },
                },
                "roles": {
                    "registry_admin": "0x" + "44" * 20,
                    "issuer_manager": "0x" + "55" * 20,
                    "key_manager": "0x" + "66" * 20,
                    "issuer_account": "0x" + "77" * 20,
                },
            }
        )
    )
    return path


def transport(issuer=1, key=1, fault=None, calls=None):
    current_block_reads = 0

    def handle(request):
        nonlocal current_block_reads
        body = json.loads(request.content)
        method, params = body["method"], body["params"]
        if calls is not None:
            calls.append(body)
        if fault == "transport":
            raise httpx.ConnectError("private RPC details", request=request)
        if fault == "json":
            return httpx.Response(200, text="invalid json")
        if fault == "rpc":
            return httpx.Response(200, json={"id": body["id"], "error": {"code": -1}})
        result = None
        if method == "eth_chainId":
            result = "0x1" if fault == "chain" else hex(31337)
        elif method == "eth_blockNumber":
            result = "0x0" if fault == "stale" else "0x8"
        elif method == "eth_getCode":
            result = "0x" if fault == "code" else "0x6000"
        elif method == "eth_getBlockByNumber":
            expected = {
                "0x0": GENESIS_HASH,
                "0x1": DEPLOYMENT_HASH,
                "0x8": CURRENT_HASH,
            }[params[0]]
            if fault == "deployment" and params[0] == "0x1":
                expected = "0x" + "ff" * 32
            if params[0] == "0x8":
                current_block_reads += 1
                if fault == "snapshot_reorg" and current_block_reads > 1:
                    expected = "0x" + "dd" * 32
            result = None if fault == "current_block" and params[0] == "0x8" else {"hash": expected}
        else:
            selector = params[0]["data"][2:10]
            if selector == digest("issuerStatus(bytes32)")[:4].hex():
                result = "0x" + word(issuer)
            elif selector == digest("keyStatus(bytes32)")[:4].hex():
                result = "0x" + word(key)
            elif selector == digest("getKey(bytes32)")[:4].hex():
                issuer_hash = digest(ISSUER) if fault != "unknown_issuer" else b"x" * 32
                account = "00" * 12 + SIGNER[2:]
                if fault == "address":
                    account = "ff" * 32
                start = 2**64 if fault == "timestamp" else 100
                result = "0x" + issuer_hash.hex() + account + word(start) + word(200) + word(key)
                if fault == "abi":
                    result = "0x1234"
                if fault == "key_enum":
                    result = result[:-64] + word(9)
            elif selector == digest("proofStatus(bytes32)")[:4].hex():
                result = "0x" + word(0 if fault == "proof_absent" else 1)
            elif selector == digest("getProof(bytes32)")[:4].hex():
                result = "0x" + (
                    digest(ISSUER).hex()
                    + digest(KEY).hex()
                    + "11" * 32
                    + "22" * 32
                    + word(0 if fault == "proof_epoch" else 100)
                    + word(200)
                    + word(1)
                    + word(0)
                    + word(0)
                )
            elif selector == digest("isConsumable(bytes32,uint64)")[:4].hex():
                result = "0x" + word(1)
            else:
                raise AssertionError("unexpected selector")
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": body["id"], "result": result})

    return httpx.MockTransport(handle)


@pytest.mark.parametrize("issuer,status", [(1, "ACTIVE"), (2, "SUSPENDED"), (3, "REVOKED")])
async def test_issuer_mapping(manifest, issuer, status):
    async with httpx.AsyncClient(transport=transport(issuer=issuer)) as client:
        reader = JsonRpcBlockchainReader(
            "http://test", manifest, issuer_ids=[ISSUER], client=client
        )
        record = await reader.get_issuer(ISSUER)
        assert record.issuer_id == ISSUER and record.status == status


@pytest.mark.parametrize("key,status", [(1, "ACTIVE"), (2, "REVOKED")])
async def test_key_mapping(manifest, key, status):
    async with httpx.AsyncClient(transport=transport(key=key)) as client:
        reader = JsonRpcBlockchainReader(
            "http://test", manifest, issuer_ids=[ISSUER], client=client
        )
        record = await reader.get_key(KEY)
        assert record.key_id == KEY and record.issuer_id == ISSUER
        assert record.signer.lower() == SIGNER and record.status == status
        assert record.valid_from == datetime.fromtimestamp(100, UTC)
        assert record.valid_until == datetime.fromtimestamp(200, UTC)


async def test_absent_records(manifest):
    async with httpx.AsyncClient(transport=transport(issuer=0, key=0)) as client:
        reader = JsonRpcBlockchainReader(
            "http://test", manifest, issuer_ids=[ISSUER], client=client
        )
        assert await reader.get_issuer(ISSUER) is None
        assert await reader.get_key(KEY) is None
        assert not await reader.is_key_valid(KEY, datetime.fromtimestamp(100, UTC))


@pytest.mark.parametrize(
    "at,issuer,key,valid",
    [
        (99, 1, 1, False),
        (100, 1, 1, True),
        (199, 1, 1, True),
        (200, 1, 1, False),
        (150, 2, 1, False),
        (150, 3, 1, False),
        (150, 1, 2, False),
    ],
)
async def test_validity_and_snapshot(manifest, at, issuer, key, valid):
    calls = []
    async with httpx.AsyncClient(transport=transport(issuer, key, calls=calls)) as client:
        reader = JsonRpcBlockchainReader(
            "http://test", manifest, issuer_ids=[ISSUER], client=client
        )
        assert await reader.is_key_valid(KEY, datetime.fromtimestamp(at, UTC)) is valid
    for call in calls:
        if call["method"] in ("eth_call", "eth_getCode"):
            assert call["params"][-1] == "0x8"


@pytest.mark.parametrize(
    "issuer,key,expected_issuer,expected_key,valid",
    [
        (1, 1, "ACTIVE", "ACTIVE", True),
        (2, 1, "SUSPENDED", "ACTIVE", False),
        (3, 1, "REVOKED", "ACTIVE", False),
        (1, 2, "ACTIVE", "REVOKED", False),
        (0, 0, None, None, False),
    ],
)
async def test_issuer_key_snapshot_uses_one_canonical_block(
    manifest, issuer, key, expected_issuer, expected_key, valid
):
    calls = []
    async with httpx.AsyncClient(transport=transport(issuer, key, calls=calls)) as client:
        reader = JsonRpcBlockchainReader(
            "http://test", manifest, issuer_ids=[ISSUER], client=client
        )
        snapshot = await reader.get_issuer_key_snapshot(
            ISSUER, KEY, datetime.fromtimestamp(150, UTC)
        )
    assert snapshot.deployment_id == DEPLOYMENT_ID
    assert snapshot.chain_id == 31337
    assert snapshot.block_number == 8 and snapshot.block_hash == CURRENT_HASH
    assert (snapshot.issuer.status if snapshot.issuer else None) == expected_issuer
    assert (snapshot.key.status if snapshot.key else None) == expected_key
    assert snapshot.key_valid_at is valid
    state_reads = [call for call in calls if call["method"] == "eth_call"]
    assert state_reads and {call["params"][-1] for call in state_reads} == {"0x8"}


@pytest.mark.parametrize("fault", ["current_block", "chain", "snapshot_reorg"])
async def test_snapshot_failure_is_not_absent(manifest, fault):
    async with httpx.AsyncClient(transport=transport(fault=fault)) as client:
        reader = JsonRpcBlockchainReader(
            "http://test", manifest, issuer_ids=[ISSUER], client=client
        )
        with pytest.raises(DependencyUnavailableError, match="blockchain state unavailable"):
            await reader.get_issuer_key_snapshot(ISSUER, KEY, datetime.fromtimestamp(150, UTC))


@pytest.mark.parametrize(
    "fault", [None, "proof_absent", "proof_epoch", "snapshot_reorg", "chain", "rpc"]
)
async def test_proof_state_distinguishes_absent_and_dependency(manifest, fault):
    data = json.loads(manifest.read_text())
    data["roles"]["gateway"] = "0x" + "88" * 20
    data["contracts"]["ProofStatusRegistry"] = {
        "address": "0x" + "55" * 20,
        "constructor_arguments": [
            data["roles"]["registry_admin"],
            data["roles"]["gateway"],
            data["contracts"]["IssuerRegistry"]["address"],
            data["contracts"]["IssuerKeyRegistry"]["address"],
        ],
        "abi_sha256": "3" * 64,
    }
    manifest.write_text(json.dumps(data))
    async with httpx.AsyncClient(transport=transport(fault=fault)) as client:
        reader = JsonRpcBlockchainReader(
            "http://test", manifest, issuer_ids=[ISSUER], client=client
        )
        if fault in ("snapshot_reorg", "chain", "rpc"):
            with pytest.raises(DependencyUnavailableError):
                await reader.get_proof_state(PROOF, datetime.fromtimestamp(150, UTC))
        else:
            state = await reader.get_proof_state(PROOF, datetime.fromtimestamp(150, UTC))
            if fault == "proof_absent":
                assert state is None
            else:
                assert state.status == "ACTIVE" and state.consumable_at
                assert state.proof_id == PROOF and state.block_hash == CURRENT_HASH


@pytest.mark.parametrize(
    "fault",
    [
        "transport",
        "json",
        "rpc",
        "chain",
        "stale",
        "code",
        "deployment",
        "unknown_issuer",
        "address",
        "timestamp",
        "abi",
        "key_enum",
    ],
)
async def test_failure_is_dependency_unavailable(manifest, fault):
    async with httpx.AsyncClient(transport=transport(fault=fault)) as client:
        reader = JsonRpcBlockchainReader(
            "http://test", manifest, issuer_ids=[ISSUER], client=client
        )
        with pytest.raises(DependencyUnavailableError, match="^blockchain state unavailable$"):
            await reader.get_key(KEY)


async def test_invalid_enum_and_naive_time(manifest):
    async with httpx.AsyncClient(transport=transport(issuer=99)) as client:
        reader = JsonRpcBlockchainReader(
            "http://test", manifest, issuer_ids=[ISSUER], client=client
        )
        with pytest.raises(DependencyUnavailableError):
            await reader.get_issuer(ISSUER)
    async with httpx.AsyncClient(transport=transport()) as client:
        reader = JsonRpcBlockchainReader(
            "http://test", manifest, issuer_ids=[ISSUER], client=client
        )
        with pytest.raises(DependencyUnavailableError):
            await reader.is_key_valid(KEY, datetime(2026, 1, 1))


def test_invalid_manifest(tmp_path):
    with pytest.raises(DependencyUnavailableError):
        JsonRpcBlockchainReader("http://test", tmp_path / "missing", issuer_ids=[ISSUER])


@pytest.mark.parametrize(
    "change",
    ["chain", "address", "block", "same_address", "deployment_id", "abi", "roles", "constructor"],
)
def test_manifest_validation(manifest, change):
    data = json.loads(manifest.read_text())
    if change == "chain":
        data["chain_id"] = 1
    elif change == "block":
        data["deployment_block"] = -1
    elif change == "address":
        data["contracts"]["IssuerRegistry"]["address"] = "0x" + "00" * 20
    elif change == "same_address":
        data["contracts"]["IssuerRegistry"] = data["contracts"]["IssuerKeyRegistry"]
    elif change == "deployment_id":
        data["deployment_id"] = "old-deployment"
    elif change == "abi":
        data["contracts"]["IssuerRegistry"]["abi_sha256"] = "not-a-hash"
    elif change == "constructor":
        data["contracts"]["IssuerKeyRegistry"]["constructor_arguments"][1] = "0x" + "77" * 20
    else:
        data["roles"]["issuer_manager"] = data["roles"]["registry_admin"]
    manifest.write_text(json.dumps(data))
    with pytest.raises(DependencyUnavailableError):
        JsonRpcBlockchainReader("http://test", manifest, issuer_ids=[ISSUER])
