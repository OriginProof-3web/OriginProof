"""Opt-in disposable Anvil integration. No private keys, production DB or existing node."""

import asyncio
import hashlib
import json
import os
import shutil
import socket
import subprocess
from pathlib import Path

import httpx
import pytest
from eth_abi import encode
from eth_utils import keccak
from infrastructure.blockchain.errors import BlockchainDependencyError
from infrastructure.blockchain.wallet_reconciliation import WalletReconciler
from infrastructure.blockchain.wallet_recovery import WalletRecovery, calldata
from infrastructure.blockchain.wallet_rpc import WalletRpc, hex_bytes, named
from originproof_core.canonicalization import canonical_json_bytes
from originproof_core.wallet_contract import (
    GovernanceProposal,
    KeyProofMessage,
    OfficialContent,
    PublishMessage,
    RevokeMessage,
    WalletDomain,
)
from originproof_core.wallet_signatures import (
    CONTENT_SCHEMAS,
    SIGNATURE_SCHEMA,
    document_id,
    identifier_hash,
    original_bytes,
    proposal_id,
    typed_data,
    validate_content,
    wallet_signer,
)
from originproof_indexer.wallet_projection import WalletProjection
from sqlalchemy import create_engine

ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = ROOT / "packages/contracts"
pytestmark = pytest.mark.skipif(
    os.environ.get("ORIGINPROOF_WALLET_LIVE") != "1",
    reason="disposable wallet EVM opt-in",
)


class LostSendReply(httpx.AsyncBaseTransport):
    def __init__(self):
        self.inner = httpx.AsyncHTTPTransport(trust_env=False)

    async def handle_async_request(self, request):
        response = await self.inner.handle_async_request(request)
        body = json.loads(await response.aread())
        await response.aclose()
        assert "error" not in body and len(hex_bytes(body["result"], 32)) == 32, (
            "local send must be accepted before simulating response loss"
        )
        raise httpx.ReadTimeout("synthetic loss after local node accepted request", request=request)

    async def aclose(self):
        await self.inner.aclose()


async def test_disposable_wallet_registry_recovery_and_reorg(tmp_path):
    anvil, forge = shutil.which("anvil"), shutil.which("forge")
    assert anvil and forge, "Foundry is required for this opt-in test"
    await asyncio.to_thread(
        subprocess.run, [forge, "build"], cwd=CONTRACTS, check=True, capture_output=True
    )
    artifact = json.loads(
        (CONTRACTS / "out/OriginProofWalletRegistry.sol/OriginProofWalletRegistry.json").read_text()
    )
    abi = artifact["abi"]
    assert abi == json.loads((CONTRACTS / "abi/OriginProofWalletRegistry.json").read_text())
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    process = subprocess.Popen(
        [anvil, "--host", "127.0.0.1", "--port", str(port), "--chain-id", "31337", "--silent"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    engine = None
    report = {
        "scope": "disposable-local-EVM; no API/DB/browser/G07 completion",
        "source_sha": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "scenarios": [],
        "transactions": {},
    }
    try:
        async with httpx.AsyncClient(timeout=5, trust_env=False) as client:

            async def rpc(method, params):
                response = await client.post(
                    url, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
                )
                response.raise_for_status()
                result = response.json()
                assert "error" not in result, "disposable RPC rejected request"
                return result["result"]

            for _ in range(100):
                try:
                    assert process.poll() is None, "disposable Anvil exited during startup"
                    assert await rpc("eth_chainId", []) == "0x7a69"
                    break
                except httpx.TransportError:
                    await asyncio.sleep(0.05)
            else:
                pytest.fail("disposable Anvil did not start")
            accounts = await rpc("eth_accounts", [])
            approvers, institution, relayer = accounts[:3], accounts[3], accounts[4]

            async def receipt(tx_hash):
                for _ in range(100):
                    result = await rpc("eth_getTransactionReceipt", [tx_hash])
                    if result is not None:
                        return result
                    await asyncio.sleep(0.05)
                pytest.fail("disposable transaction was not mined")

            creation = hex_bytes(artifact["bytecode"]["object"]) + encode(
                ["address[3]"],
                [approvers],
            )
            deploy_hash = await rpc(
                "eth_sendTransaction",
                [{"from": approvers[0], "data": "0x" + creation.hex(), "gas": "0xc00000"}],
            )
            deployed = await receipt(deploy_hash)
            assert deployed["status"] == "0x1"
            address = deployed["contractAddress"]
            runtime = await rpc("eth_getCode", [address, deployed["blockNumber"]])
            config = dict(
                chain_id=31337,
                address=address,
                deployment_block=int(deployed["blockNumber"], 16),
                deployment_hash=deployed["blockHash"],
                runtime_code_hash="0x" + keccak(hex_bytes(runtime)).hex(),
                abi=abi,
            )
            reader = WalletRpc(client, url, **config)
            reconciler, recovery = WalletReconciler(reader), WalletRecovery(reader)
            assert (await reader.snapshot())["hash"] == deployed["blockHash"]
            report["manifest"] = {k: v for k, v in config.items() if k != "abi"}
            report["manifest"].update(
                deployment_tx=deploy_hash,
                constructor_arguments=[approvers],
                contract="OriginProofWalletRegistry",
                non_upgradeable=True,
                chain_kind="disposable-local",
                abi_sha256=hashlib.sha256(
                    (CONTRACTS / "abi/OriginProofWalletRegistry.json").read_bytes()
                ).hexdigest(),
            )
            report["toolchain"] = {
                name: subprocess.check_output([path, "--version"], text=True).splitlines()[0]
                for name, path in [("anvil", anvil), ("forge", forge)]
            }
            compiler_metadata = artifact["metadata"]
            if isinstance(compiler_metadata, str):
                compiler_metadata = json.loads(compiler_metadata)
            report["toolchain"]["solc"] = compiler_metadata["compiler"]["version"]
            report["toolchain"]["dependency_lock_sha256"] = hashlib.sha256(
                (CONTRACTS / "dependencies.lock").read_bytes()
            ).hexdigest()
            domain = WalletDomain(chain_id="31337", verifying_contract=address)
            issuer, key = identifier_hash("synthetic-wallet-live"), identifier_hash("live-key-1")
            metadata = identifier_hash("public-synthetic-metadata")
            now = int((await reader.snapshot())["timestamp"], 16)
            deadline = now + 3600
            assert (await reader.read("getIssuer", [hex_bytes(issuer, 32)]))["values"] is None

            def model_tuple(function, parameter, model):
                field = next(
                    x for x in reader.functions[function]["inputs"] if x["name"] == parameter
                )
                data = model.model_dump(by_alias=True)
                return tuple(
                    hex_bytes(data[x["name"]], 32)
                    if x["type"] == "bytes32"
                    else int(data[x["name"]])
                    if x["type"].startswith("uint")
                    else data[x["name"]]
                    for x in field["components"]
                )

            def arguments(function, values):
                return named(reader.functions[function]["inputs"], values)

            async def sign(message):
                result = await rpc(
                    "eth_signTypedData_v4", [institution, json.dumps(typed_data(domain, message))]
                )
                assert wallet_signer(domain, message, result) == institution
                return hex_bytes(result)

            async def send(label, function, args, sender, *, success=True):
                tx_hash = await rpc(
                    "eth_sendTransaction",
                    [
                        {
                            "from": sender,
                            "to": address,
                            "data": "0x" + calldata(reader, function, args).hex(),
                            "gas": "0x800000",
                        }
                    ],
                )
                mined = await receipt(tx_hash)
                assert mined["status"] == ("0x1" if success else "0x0")
                evidence = await reconciler.transaction(
                    tx_hash, function=function, arguments=args, sender=sender
                )
                assert evidence is not None and evidence["receipt_status"] == int(success)
                report["transactions"][label] = {
                    "hash": tx_hash,
                    "status": mined["status"],
                    "block_number": mined["blockNumber"],
                    "block_hash": mined["blockHash"],
                }
                return tx_hash

            proposal = GovernanceProposal(
                action=1,
                issuer_id=issuer,
                key_id=key,
                signer=institution,
                metadata_hash=metadata,
                nonce="0",
                deadline=deadline,
            )
            proof = KeyProofMessage(
                application_id=identifier_hash("live-application"),
                issuer_id=issuer,
                signer=institution,
                challenge_nonce=identifier_hash("live-challenge"),
                deadline=deadline,
            )
            pid = proposal_id(domain, proposal)
            args = arguments(
                "propose",
                [
                    model_tuple("propose", "proposal", proposal),
                    model_tuple("propose", "proof", proof),
                    await sign(proof),
                ],
            )
            await send("register_proposal", "propose", args, approvers[0])
            approve = arguments("approve", [hex_bytes(pid, 32)])
            await send("approve_first", "approve", approve, approvers[0])
            assert not (await reconciler.proposal(pid))["executed"]
            await send("approve_second", "approve", approve, approvers[1])
            assert (await reconciler.proposal(pid))["approvals"] == approvers[:2]
            report["scenarios"].append("real EIP712 KeyProof, 2-of-3 and canonical approvals")

            doc_key = identifier_hash("live-document-key")
            content = OfficialContent(
                notice_type="OFFICIAL_DOCUMENT",
                institution_code="SYNTHETIC-LIVE",
                document_type="NOTICE",
                document_number="DEMO-001",
                title="Synthetic notice",
                summary="Disposable-chain fixture only",
                official_url=None,
            )
            publish = PublishMessage(
                issuer_id=issuer,
                doc_key=doc_key,
                document_id=document_id(issuer, doc_key),
                version=1,
                key_id=key,
                original_hash=identifier_hash("synthetic-original-1"),
                protected_hash="0x" + hashlib.sha256(canonical_json_bytes(content)).hexdigest(),
                content_schema=CONTENT_SCHEMAS["OFFICIAL_DOCUMENT"],
                signature_schema=SIGNATURE_SCHEMA,
                issued_at=now - 1,
                expires_at=deadline + 3600,
                nonce="0",
                deadline=deadline,
            )
            publish = publish.model_copy(
                update={
                    "original_hash": "0x"
                    + hashlib.sha256(original_bytes(publish, content)).hexdigest(),
                }
            )
            validate_content(publish, content)
            args1 = arguments(
                "publish", [model_tuple("publish", "message", publish), await sign(publish)]
            )
            hash1 = await send("publish_v1", "publish", args1, relayer)
            publish2 = publish.model_copy(
                update={
                    "version": 2,
                    "nonce": "1",
                    "original_hash": identifier_hash("synthetic-original-2"),
                }
            )
            content2 = content.model_copy(update={"summary": "Revised synthetic notice"})
            publish2 = publish2.model_copy(
                update={
                    "protected_hash": "0x"
                    + hashlib.sha256(canonical_json_bytes(content2)).hexdigest(),
                    "original_hash": "0x"
                    + hashlib.sha256(original_bytes(publish2, content2)).hexdigest(),
                }
            )
            validate_content(publish2, content2)
            report["scenarios"].append(
                "shared canonical original/protected SHA256, no raw bytes archived"
            )
            args2 = arguments(
                "publish", [model_tuple("publish", "message", publish2), await sign(publish2)]
            )
            before = await reader.snapshot()
            sender_nonce = await rpc("eth_getTransactionCount", [relayer, "latest"])
            async with httpx.AsyncClient(transport=LostSendReply(), timeout=5) as losing:
                lossy = WalletRpc(losing, url, **config)
                with pytest.raises(BlockchainDependencyError):
                    await lossy.rpc(
                        "eth_sendTransaction",
                        [
                            {
                                "from": relayer,
                                "to": address,
                                "data": "0x" + calldata(reader, "publish", args2).hex(),
                                "gas": "0x800000",
                            }
                        ],
                    )
            recovered = await recovery.find_transaction(
                function="publish", arguments=args2, start_block=int(before["number"], 16)
            )
            report["initial_unknown_scan_matches"] = len(recovered["attempts"])
            for _ in range(100):
                if int(await rpc("eth_blockNumber", []), 16) > int(before["number"], 16):
                    break
                await asyncio.sleep(0.02)
            else:
                pytest.fail("accepted local transaction remained unmined")
            # Recreate clients from serialized intent, as after a client restart.
            # This does not claim an API/Operation database process restart.
            saved_args = json.loads(json.dumps(args2))
            async with httpx.AsyncClient(timeout=5) as restarted_client:
                restarted_rpc = WalletRpc(restarted_client, url, **config)
                recovered = await WalletRecovery(restarted_rpc).find_transaction(
                    function="publish",
                    arguments=saved_args,
                    start_block=int(before["number"], 16),
                )
            assert len(recovered["attempts"]) == 1
            hash2 = recovered["attempts"][0]["tx_hash"]
            assert recovered["attempts"][0]["evidence"]["receipt_status"] == 1
            assert int(await rpc("eth_getTransactionCount", [relayer, "latest"]), 16) == (
                int(sender_nonce, 16) + 1
            )
            await recovery.find_transaction(
                function="publish",
                arguments=args2,
                start_block=config["deployment_block"],
                known_tx_hash=hash2,
            )
            assert int(await rpc("eth_getTransactionCount", [relayer, "latest"]), 16) == (
                int(sender_nonce, 16) + 1
            )
            report["transactions"]["lost_reply_recovered_v2"] = {
                "hash": hash2,
                "status": "0x1",
                "block_hash": recovered["attempts"][0]["evidence"]["block"]["hash"],
            }
            report["scenarios"].append(
                "real accepted-send response loss recovered by fresh client without hash/resend"
            )
            history = await reconciler.transaction(hash1, function="publish", arguments=args1)
            assert history["current_state"]["document"]["state"] == 3
            revoke = RevokeMessage(
                issuer_id=issuer,
                doc_key=doc_key,
                document_id=publish.document_id,
                version=2,
                key_id=key,
                nonce="2",
                deadline=deadline,
            )
            revoke_args = arguments(
                "revoke", [model_tuple("revoke", "message", revoke), await sign(revoke)]
            )
            await send("revoke_v2", "revoke", revoke_args, relayer)
            failed = await send("failed_replay_v2", "publish", args2, relayer, success=False)
            attempts = await recovery.find_transaction(
                function="publish",
                arguments=args2,
                start_block=config["deployment_block"],
                known_tx_hash=failed,
            )
            assert sorted(x["evidence"]["receipt_status"] for x in attempts["attempts"]) == [0, 1]
            assert attempts["observed_next_nonce"] == 3
            report["scenarios"].append(
                "atomic supersession, revoke, failed replay and original success"
            )

            publish3 = publish2.model_copy(update={"version": 3, "nonce": "3"})
            publish3 = publish3.model_copy(
                update={
                    "original_hash": "0x"
                    + hashlib.sha256(original_bytes(publish3, content2)).hexdigest()
                }
            )
            validate_content(publish3, content2)
            args3 = arguments(
                "publish", [model_tuple("publish", "message", publish3), await sign(publish3)]
            )
            hash3 = await send("publish_v3_after_revoked_v2", "publish", args3, relayer)
            evidence3 = await reconciler.transaction(hash3, function="publish", arguments=args3)
            assert len(evidence3["events"]) == 1
            revoked_history = await reader.read(
                "getDocument", [hex_bytes(publish.document_id, 32), 2]
            )
            document_fields = reader.functions["getDocument"]["outputs"][0]["components"]
            assert named(document_fields, revoked_history["values"][0])["state"] == 2
            report["scenarios"].append(
                "publish successor after revoked predecessor without supersession event"
            )

            suspend_args = arguments("suspendIssuer", [hex_bytes(issuer, 32), keccak(text="OTHER")])
            await send("suspend", "suspendIssuer", suspend_args, approvers[0])
            revoke1 = revoke.model_copy(update={"version": 1, "nonce": "4"})
            await send(
                "revoke_old_while_suspended",
                "revoke",
                arguments(
                    "revoke", [model_tuple("revoke", "message", revoke1), await sign(revoke1)]
                ),
                relayer,
            )
            proposal = proposal.model_copy(update={"action": 3, "nonce": "2"})
            zero_proof = (0, b"\0" * 32, b"\0" * 32, "0x" + "00" * 20, b"\0" * 32, 0)
            await send(
                "reactivate_proposal",
                "propose",
                arguments(
                    "propose", [model_tuple("propose", "proposal", proposal), zero_proof, b""]
                ),
                approvers[0],
            )
            pid = proposal_id(domain, proposal)
            approve = arguments("approve", [hex_bytes(pid, 32)])
            await send("reactivate_approve1", "approve", approve, approvers[0])
            await send("reactivate_approve2", "approve", approve, approvers[1])
            report["scenarios"].append("suspension, old-version revoke and joint reactivation")

            engine = create_engine("sqlite:///" + str(tmp_path / "wallet.db"))
            store = WalletProjection(engine, reader)
            store.initialize()
            assert await store.sync() > 0
            safe = await reader.snapshot()
            checkpoint = store.checkpoint()
            engine.dispose()
            engine = create_engine("sqlite:///" + str(tmp_path / "wallet.db"))
            store = WalletProjection(engine, reader)
            assert store.checkpoint() == checkpoint and await store.sync() == 0
            tag = await rpc("evm_snapshot", [])
            compromise = arguments(
                "suspendIssuer", [hex_bytes(issuer, 32), keccak(text="KEY_COMPROMISE")]
            )
            old_fork_hash = await send(
                "orphaned_key_compromise", "suspendIssuer", compromise, approvers[0]
            )
            assert (await reader.read("getKey", [hex_bytes(key, 32)]))["values"][0][4] > 0
            await store.sync()
            orphan = store.checkpoint()
            assert await rpc("evm_revert", [tag])
            with pytest.raises(ValueError):
                await store.sync()
            await store.rewind(int(safe["number"], 16), safe["hash"])
            await send("replacement_suspend", "suspendIssuer", suspend_args, approvers[0])
            with pytest.raises(BlockchainDependencyError):
                await recovery.find_transaction(
                    function="publish",
                    arguments=args2,
                    start_block=orphan[0] + 1,
                    previous_checkpoint=orphan,
                )
            await store.sync()
            assert (await reader.read("getKey", [hex_bytes(key, 32)]))["values"][0][4] == 0
            assert (
                await reconciler.transaction(
                    old_fork_hash,
                    function="suspendIssuer",
                    arguments=compromise,
                    sender=approvers[0],
                )
                is None
            )
            report["scenarios"].append(
                "SQLite restart, actual EVM reorg, explicit rewind and orphan rejection"
            )

            await rpc("evm_setAutomine", [False])
            pending_args = arguments("approve", [keccak(text="nonexistent-pending-proposal")])
            pending = await rpc(
                "eth_sendTransaction",
                [
                    {
                        "from": approvers[0],
                        "to": address,
                        "data": "0x" + calldata(reader, "approve", pending_args).hex(),
                        "gas": "0x800000",
                    }
                ],
            )
            result = await recovery.find_transaction(
                function="approve",
                arguments=pending_args,
                sender=approvers[0],
                known_tx_hash=pending,
                start_block=config["deployment_block"],
            )
            assert not result["attempts"]
            await rpc("evm_mine", [])
            await rpc("evm_setAutomine", [True])
            assert (await receipt(pending))["status"] == "0x0"
            report["scenarios"].append(
                "real pending known hash stays unresolved; failed receipt distinct"
            )
            with pytest.raises(BlockchainDependencyError):
                await WalletRpc(client, url, **(config | {"chain_id": 31338})).snapshot()
            process.terminate()
            await asyncio.to_thread(process.wait, 5)
            with pytest.raises(BlockchainDependencyError):
                await reader.snapshot()
            report["scenarios"].append("wrong chain and actual RPC outage fail closed")
            output = os.environ.get("ORIGINPROOF_WALLET_LIVE_OUTPUT")
            if output:
                target = Path(output)
                assert not target.exists(), "live report is append-only; select a new output path"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(report, indent=2) + "\n")
    finally:
        if engine is not None:
            engine.dispose()
        if process.poll() is None:
            process.terminate()
            try:
                await asyncio.to_thread(process.wait, 5)
            except subprocess.TimeoutExpired:
                process.kill()
                await asyncio.to_thread(process.wait, 5)
