"""Demo data for the wallet Registry through the real /v3 API (synthetic institution only).

Flow (same order as docs/api/v5_c_runtime.md "A: 화면에서 사용할 순서"):
  institution application → demo email code → internal approval → key challenge + KeyProof
  signature → operator proposal → approver1 propose tx → approver1/approver2 approve txs
  (2-of-3 activation) → document v1/v2 drafts → institution Publish signature → the institution
  wallet sends publish itself → reconcile until CONFIRMED → /v3/verifications (genuine, tampered).

Signers:
  --signer rpc       disposable Anvil only: unlocked accounts sign/send through the node.
  --signer keystore  real networks: `cast wallet sign --data` and `cast send` with Foundry
                     keystore accounts. cast asks for each keystore password on the terminal;
                     this script never sees a key or password and never takes one as an argument.

The API must already run against the same Registry (CHAIN_TARGET / API_WALLET_REGISTRY_ADDRESS)
with the v5 synthetic accounts seeded (`seed_accounts.py --v5-wallet`). Account passwords are
read from the local synthetic credential file (test-accounts.json, 0600) and never printed.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
from infrastructure.blockchain.network import chain_target
from infrastructure.blockchain.wallet_adapter import WalletRegistryReadAdapter
from infrastructure.blockchain.wallet_deployment import load_wallet_deployment
from infrastructure.blockchain.wallet_recovery import calldata
from infrastructure.blockchain.wallet_rpc import WalletRpc
from originproof_core.wallet_contract import (
    GovernanceProposal,
    KeyProofMessage,
    SigningRequest,
)
from originproof_core.wallet_signatures import identifier_hash, typed_data

ISSUER = "iss_origin_mock_bank"
ISSUER_NAME = "Origin Mock Bank"
EMAIL = "staff@bank.example.invalid"
DOC_KEY_LABEL = "demo_local_tax_notice"


def say(text):
    print(f"• {text}", flush=True)


class Signers:
    """Sign typed data and send Registry calls as approver1/approver2/institution."""

    def __init__(self, mode, rpc_url, registry, addresses, accounts, test_password=None):
        self.mode, self.url, self.registry = mode, rpc_url, registry
        self.addresses, self.accounts = addresses, accounts
        self.test_password = test_password
        self.cast = shutil.which("cast")
        if mode == "keystore" and self.cast is None:
            raise SystemExit("cast(Foundry) must be on PATH")

    def _account(self, who):
        name = self.accounts[who]
        # Absolute path → keystore file (disposable tests); otherwise a ~/.foundry account name.
        return ["--keystore", name] if os.path.sep in name else ["--account", name]

    def _secret(self):
        return ["--password", self.test_password] if self.test_password else []

    async def sign(self, client, who, signing: SigningRequest):
        data = typed_data(signing.domain, signing.message)
        if self.mode == "rpc":
            return await rpc(client, self.url, "eth_signTypedData_v4",
                             [self.addresses[who], json.dumps(data)])
        say(f"{who} 지갑으로 서명합니다 — 보관함 비밀번호를 입력하세요")
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump(data, handle)
            path = handle.name
        try:
            out = subprocess.run(
                [self.cast, "wallet", "sign", "--data", "--from-file", path,
                 *self._account(who), *self._secret()],
                stdout=subprocess.PIPE, text=True, check=True,
            ).stdout.strip().splitlines()[-1]
        finally:
            os.unlink(path)
        return out

    async def send(self, client, who, data_hex):
        if self.mode == "rpc":
            tx = await rpc(client, self.url, "eth_sendTransaction",
                           [{"from": self.addresses[who], "to": self.registry, "data": data_hex}])
        else:
            say(f"{who} 지갑으로 거래를 보냅니다 — 보관함 비밀번호를 입력하세요")
            env = os.environ | {"ETH_RPC_URL": self.url}  # URL only in env, not in arguments
            out = subprocess.run(
                [self.cast, "send", self.registry, data_hex, "--async",
                 *self._account(who), *self._secret()],
                stdout=subprocess.PIPE, text=True, check=True, env=env,
            ).stdout.strip().splitlines()[-1]
            tx = out.strip()
        await mined(client, self.url, tx)
        return tx


async def rpc(client, url, method, params):
    response = await client.post(url, json={"jsonrpc": "2.0", "id": 1, "method": method,
                                            "params": params})
    response.raise_for_status()
    body = response.json()
    if "error" in body:
        raise RuntimeError(f"{method} failed: {body['error'].get('message')}")
    return body["result"]


async def mined(client, url, tx_hash, timeout=240):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        receipt = await rpc(client, url, "eth_getTransactionReceipt", [tx_hash])
        if receipt:
            if receipt["status"] != "0x1":
                raise RuntimeError(f"transaction failed on chain: {tx_hash}")
            return receipt
        await asyncio.sleep(3)
    raise RuntimeError(f"transaction not mined in time: {tx_hash}")


class Api:
    def __init__(self, base, password):
        self.base, self.password, self.clients = base, password, {}

    async def as_(self, username) -> httpx.AsyncClient:
        if username not in self.clients:
            client = httpx.AsyncClient(base_url=self.base, timeout=60, trust_env=False)
            login = await client.post("/v1/auth/login",
                                      json={"username": username, "password": self.password})
            if login.status_code != 200:
                raise SystemExit(f"login failed for {username}: HTTP {login.status_code}")
            me = (await client.get("/v1/auth/me")).json()
            client.headers["X-CSRF-Token"] = me["csrf_token"]
            self.clients[username] = client
        return self.clients[username]

    async def close(self):
        for client in self.clients.values():
            await client.aclose()


def ok(response, *codes):
    if response.status_code not in codes:
        raise SystemExit(f"{response.request.method} {response.request.url.path} → "
                         f"HTTP {response.status_code}: {response.text[:300]}")
    return response.json() if response.content else None


async def settle(api_client, operation, attempts=40):
    """Reconcile an operation until it is CONFIRMED (chain observation, never assumed)."""
    for _ in range(attempts):
        if operation["status"] == "CONFIRMED":
            return operation
        if operation["status"] == "FAILED":
            raise SystemExit(f"operation failed: {operation}")
        await asyncio.sleep(4)
        operation = ok(await api_client.post(
            f"/v3/operations/{operation['operation_id']}/reconcile"), 202)
    raise SystemExit(f"operation not confirmed: {operation['operation_id']}")


def content(amount):
    return {
        "notice_type": "PAYMENT_REQUEST",
        "amount_minor": amount,
        "currency": "KRW",
        "payee_bank_name": "합성 은행",
        "payee_account_number": "001234567890",
        "payee_account_holder": "합성 기관(Origin Mock Bank)",
        "payment_purpose": "합성 지방세 납부 안내",
        "due_at": int(time.time()) + 14 * 86400,
        "official_url": "https://bank.example.invalid/pay",
    }


async def run(args):
    target = chain_target(args.chain_target)
    password = json.loads(Path(args.credentials).read_text())["password"]
    deployment, _ = load_wallet_deployment(args.manifest, chain_id=target.chain_id,
                                           address=args.registry)
    addresses = {"approver1": args.approver1, "approver2": args.approver2,
                 "institution": args.institution}
    accounts = {"approver1": args.approver1_account, "approver2": args.approver2_account,
                "institution": args.institution_account}
    test_password = os.environ.get("WALLET_DEMO_TEST_PASSWORD")
    if test_password and target.name != "anvil":
        raise SystemExit("WALLET_DEMO_TEST_PASSWORD is for disposable Anvil keystores only")
    api = Api(args.api, password)
    async with httpx.AsyncClient(timeout=30, trust_env=False) as chain_client:
        reader = WalletRpc(chain_client, args.rpc_url, **deployment)
        signers = Signers(args.signer, args.rpc_url, reader.address, addresses, accounts,
                          test_password)
        try:
            bank = await api.as_("v5_bank")
            # 1) 기관 신청 → 데모 메일 → 내부 승인
            apps = (await bank.get("/v1/issuer-applications/mine")).json()
            app_id = apps["application_id"] if isinstance(apps, dict) and apps else None
            if not app_id:
                app_id = ok(await bank.post("/v1/issuer-applications",
                                            json={"issuer_name": ISSUER_NAME}), 201)[
                    "application_id"]
            say(f"기관 신청 {app_id}")
            started = await bank.get(f"/v3/issuer-applications/{app_id}")
            view = ok(started, 200, 404) if started.status_code != 404 else {}
            if not view.get("email_verified"):
                ok(await bank.post(f"/v3/issuer-applications/{app_id}/email-codes",
                                   json={"email": EMAIL}), 201)
                code = ok(await bank.get(f"/v3/issuer-applications/{app_id}/demo-inbox"),
                          200)["code"]
                ok(await bank.post(f"/v3/issuer-applications/{app_id}/email-verifications",
                                   json={"code": code}), 200)
                say("업무 이메일 확인 완료(데모 메일)")
            checks = ok(await bank.get(f"/v3/issuer-applications/{app_id}"), 200)
            if not checks.get("internally_approved"):
                internal = await api.as_("v5_bank_approver")
                checks = ok(await internal.post(
                    f"/v3/issuer-applications/{app_id}/internal-approvals",
                    json={"decision": "APPROVE", "reason": "합성 시연 내부 승인"}), 200)
                say("기관 내부 승인 완료")

            issuer_hash = identifier_hash(ISSUER)
            chain = WalletRegistryReadAdapter(reader)
            issuer = await chain.issuer(issuer_hash)
            if issuer is None or issuer.state != "ACTIVE":
                # 2) 키 보유 증명(기관 지갑 서명)
                stamp = int(time.time())
                challenge = SigningRequest.model_validate(ok(await bank.post(
                    "/v3/key-challenges",
                    json={"request_id": f"req_key_{stamp}", "application_id": app_id,
                          "signer": args.institution.lower()}), 201))
                proof_sig = await signers.sign(chain_client, "institution", challenge)
                ok(await bank.post("/v3/key-proofs", json={
                    "request_id": f"req_proof_{stamp}",
                    "signing_request_id": challenge.signing_request_id,
                    "signature": proof_sig}), 200)
                say("기관 키 보유 증명 완료")
                # 3) 운영 승인자 제안 → 체인 propose/approve ×2
                op1, op2 = await api.as_("v5_operator1"), await api.as_("v5_operator2")
                gov_nonce = issuer.governance_nonce if issuer else "0"
                prepared = ok(await op1.post("/v3/proposals", json={
                    "request_id": f"req_proposal_{stamp}",
                    "key_proof_request_id": challenge.signing_request_id,
                    "proposal": {
                        "action": 1, "issuerId": issuer_hash,
                        "keyId": identifier_hash(f"key_bank_demo_{stamp}"),
                        "signer": args.institution.lower(),
                        "metadataHash": checks["metadata_hash"],
                        "nonce": gov_nonce, "deadline": challenge.message.deadline,
                    }}), 201)
                pid = prepared["proposal_id"]
                proposal = GovernanceProposal.model_validate(prepared["proposal"])
                proof = KeyProofMessage.model_validate(prepared["key_proof"])
                propose = calldata(reader, "propose", {
                    "proposal": proposal.model_dump(by_alias=True)
                    | {"nonce": int(proposal.nonce)},
                    "proof": proof.model_dump(by_alias=True),
                    "signature": prepared["key_proof_signature"],
                })
                tx = await signers.send(chain_client, "approver1", "0x" + propose.hex())
                ok(await op1.post(f"/v3/proposals/{pid}/transactions",
                                  json={"request_id": f"req_propose_{stamp}", "tx_hash": tx}),
                   202)
                say(f"승인 노드 #1(KISA 모델) 제안 거래 {tx}")
                approve = "0x" + calldata(reader, "approve", {"proposalId": pid}).hex()
                for who, client in (("approver1", op1), ("approver2", op2)):
                    tx = await signers.send(chain_client, who, approve)
                    ok(await client.post(f"/v3/proposals/{pid}/approvals",
                                         json={"request_id": f"req_{who}_{stamp}",
                                               "tx_hash": tx}), 202)
                    say(f"{who} 승인 거래 {tx}")
                shown = ok(await op1.get(f"/v3/proposals/{pid}"), 200)
                say(f"공동승인 상태: {shown['status']} (승인 {len(shown['approvals'])}/2)")
            else:
                say("기관이 이미 체인에서 활성 상태라 승인 단계는 건너뜁니다")

            # 4) 안내문 v1 → v2(금액 정정) 발행: 기관 지갑 서명 + 기관 지갑 직접 제출
            # 실행마다 새 안내문(같은 실행 안에서 v1 → v2). 다시 실행해도 버전 충돌이 없다.
            doc_key = identifier_hash(f"{DOC_KEY_LABEL}_{int(time.time())}")
            published = {}
            for version, amount in ((1, 154000), (2, 120000)):
                stamp = int(time.time())
                draft = ok(await bank.post("/v3/document-drafts", json={
                    "request_id": f"req_draft_{version}_{stamp}", "doc_key": doc_key,
                    "expected_version": version, "expires_at": stamp + 30 * 86400,
                    "content": content(amount)}), 201)
                signing = SigningRequest.model_validate(draft)
                sig = await signers.sign(chain_client, "institution", signing)
                op = ok(await bank.post("/v3/publications", json={
                    "request_id": f"req_publish_{version}_{stamp}",
                    "signing_request_id": signing.signing_request_id, "signature": sig}), 202)
                publish = calldata(reader, "publish", {
                    "message": signing.message.model_dump(by_alias=True)
                    | {"nonce": int(signing.message.nonce)},
                    "signature": sig,
                })
                tx = await signers.send(chain_client, "institution", "0x" + publish.hex())
                op = ok(await bank.post(
                    f"/v3/signing-requests/{signing.signing_request_id}/transactions",
                    json={"request_id": f"req_direct_{version}_{stamp}",
                          "signing_request_id": signing.signing_request_id, "tx_hash": tx}),
                    202)
                op = await settle(bank, op)
                published[version] = (signing.message.document_id, draft["content"], tx)
                say(f"안내문 v{version}(금액 {amount:,}원) 발행 확정 · 거래 {tx}")

            # 5) 검증: 진짜 v2 / 금액 1원 변조 / 정정 전 v1
            recipient = httpx.AsyncClient(base_url=args.api, timeout=60, trust_env=False)
            try:
                did, genuine, _ = published[2]
                cases = (("정본 v2", did, None, genuine),
                         ("금액 1원 변조", did, None, genuine | {"amount_minor": 120001}),
                         ("정정 전 v1", published[1][0], 1, published[1][1]))
                for label, document_id, version, candidate in cases:
                    result = ok(await recipient.post("/v3/verifications", json={
                        "request_id": f"req_verify_{int(time.time() * 1000)}",
                        "document_id": document_id, "version": version,
                        "scope": "PROTECTED_FIELDS", "candidate": candidate}), 200)
                    state = (result.get("document") or {}).get("state")
                    say(f"검증 [{label}] → {result['verification_status']} · 상태 {state} "
                        f"{','.join(result.get('reason_codes') or [])}")
            finally:
                await recipient.aclose()
            explorer = ("https://sepolia.etherscan.io/address/" + reader.address
                        if target.name == "sepolia" else None)
            say("완료" + (f" · Etherscan: {explorer}" if explorer else ""))
        finally:
            await api.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--chain-target", required=True, choices=["anvil", "sepolia"])
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--rpc-url", default=os.environ.get("WALLET_DEMO_RPC_URL"))
    parser.add_argument("--registry", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--credentials", required=True, help="test-accounts.json (synthetic)")
    parser.add_argument("--signer", required=True, choices=["rpc", "keystore"])
    parser.add_argument("--approver1", required=True)
    parser.add_argument("--approver2", required=True)
    parser.add_argument("--institution", required=True)
    parser.add_argument("--approver1-account", default="op-approver1")
    parser.add_argument("--approver2-account", default="op-approver2")
    parser.add_argument("--institution-account", default="op-institution")
    args = parser.parse_args(argv)
    if not args.rpc_url:
        parser.error("--rpc-url or WALLET_DEMO_RPC_URL is required")
    if args.signer == "rpc" and args.chain_target != "anvil":
        parser.error("--signer rpc is only for disposable Anvil")
    asyncio.run(run(args))


if __name__ == "__main__":
    sys.exit(main())
