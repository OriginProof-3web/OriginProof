"""More demo documents for local Anvil: 10 payment notices (bank) + 10 official documents (office).

Run after rc_local.sh first setup (bank already active). Reuses wallet_demo_flow helpers.
Writes build/rc-local/bulk-docs.jsonl (document_id, issuer, content) for test cases.
Synthetic data only; never for real networks.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path

import httpx
from infrastructure.blockchain.network import chain_target
from infrastructure.blockchain.wallet_adapter import WalletRegistryReadAdapter
from infrastructure.blockchain.wallet_deployment import load_wallet_deployment
from infrastructure.blockchain.wallet_recovery import calldata
from infrastructure.blockchain.wallet_rpc import WalletRpc
from originproof_core.wallet_contract import GovernanceProposal, KeyProofMessage, SigningRequest
from originproof_core.wallet_signatures import identifier_hash
from wallet_demo_flow import Api, Signers, ok, post, say, settle

ISSUERS = {
    "bank": dict(issuer="iss_origin_mock_bank", name="Origin Mock Bank", user="v5_bank",
                 approver="v5_bank_approver", email="staff@bank.example.invalid",
                 wallet="institution"),
    "office": dict(issuer="iss_origin_mock_office", name="Origin Mock Office", user="v5_office",
                   approver="v5_office_approver", email="staff@office.example.invalid",
                   wallet="office"),
}

# (금액, 계좌, 예금주, 목적) — 금액·계좌가 서로 달라야 원본 찾기(금액+계좌)가 한 건만 맞는다.
PAYMENTS = [
    (32500, "001234500001", "합성 기관(Origin Mock Bank)", "합성 자동차세 납부 안내"),
    (48000, "001234500002", "합성 기관(Origin Mock Bank)", "합성 재산세 1기분 납부 안내"),
    (85000, "001234500003", "합성 기관(Origin Mock Bank)", "합성 카드 대금 청구 안내"),
    (12900, "001234500004", "합성 기관(Origin Mock Bank)", "합성 통신 요금 납부 안내"),
    (210000, "001234500005", "합성 기관(Origin Mock Bank)", "합성 대출 이자 납입 안내"),
    (67300, "001234500006", "합성 기관(Origin Mock Bank)", "합성 건강보험료 납부 안내"),
    (5500, "001234500007", "합성 기관(Origin Mock Bank)", "합성 과태료 납부 안내"),
    (1250000, "001234500008", "합성 기관(Origin Mock Bank)", "합성 등록금 납부 안내"),
    (99000, "001234500009", "합성 기관(Origin Mock Bank)", "합성 연회비 청구 안내"),
    (430000, "001234500010", "합성 기관(Origin Mock Bank)", "합성 보험료 납입 안내"),
]
OFFICIALS = [
    ("민원회신", "OMO-2026-0101", "합성 민원 처리 결과 회신", "접수하신 합성 민원의 처리 결과를 알려 드립니다."),
    ("통지서", "OMO-2026-0102", "합성 주정차 위반 사전 통지", "합성 차량의 주정차 위반 사실을 사전 통지합니다."),
    ("안내문", "OMO-2026-0103", "합성 건강검진 대상자 안내", "올해 합성 건강검진 대상자임을 안내합니다."),
    ("고지서", "OMO-2026-0104", "합성 주민세 고지", "합성 주민세 고지 내용을 안내합니다."),
    ("확인서", "OMO-2026-0105", "합성 전입 신고 확인", "합성 전입 신고가 처리되었음을 확인합니다."),
    ("안내문", "OMO-2026-0106", "합성 예비군 훈련 안내", "합성 예비군 훈련 일정을 안내합니다."),
    ("통지서", "OMO-2026-0107", "합성 보조금 지급 결정 통지", "신청하신 합성 보조금 지급이 결정되었습니다."),
    ("회신", "OMO-2026-0108", "합성 정보공개 청구 회신", "합성 정보공개 청구에 대한 결과를 회신합니다."),
    ("안내문", "OMO-2026-0109", "합성 선거 투표소 안내", "합성 선거의 투표소 위치를 안내합니다."),
    ("통지서", "OMO-2026-0110", "합성 체납 처분 예고 통지", "합성 체납액 처분 예고를 통지합니다."),
]


def payment(amount, account, holder, purpose):
    return {"notice_type": "PAYMENT_REQUEST", "amount_minor": amount, "currency": "KRW",
            "payee_bank_name": "합성 은행", "payee_account_number": account,
            "payee_account_holder": holder, "payment_purpose": purpose,
            "due_at": int(time.time()) + 14 * 86400,
            "official_url": "https://bank.example.invalid/pay"}


def official(kind, number, title, summary):
    return {"notice_type": "OFFICIAL_DOCUMENT", "institution_code": "ORIGIN_MOCK_OFFICE", "document_type": kind,
            "document_number": number, "title": title, "summary": summary,
            "official_url": "https://office.example.invalid/docs"}


async def onboard(api, signers, chain_client, reader, who):
    """Application → demo email → internal approval → KeyProof → 2-of-3 activation (skip if ACTIVE)."""
    spec = ISSUERS[who]
    inst = await api.as_(spec["user"])
    apps = (await inst.get("/v1/issuer-applications/mine")).json()
    app_id = apps["application_id"] if isinstance(apps, dict) and apps else None
    if not app_id:
        app_id = ok(await post(inst, "/v1/issuer-applications",
                               json={"issuer_name": spec["name"]}), 201)["application_id"]
    view = await inst.get(f"/v3/issuer-applications/{app_id}")
    view = view.json() if view.status_code == 200 else {}
    if not view.get("email_verified"):
        ok(await post(inst, f"/v3/issuer-applications/{app_id}/email-codes",
                      json={"email": spec["email"]}), 201)
        code = ok(await inst.get(f"/v3/issuer-applications/{app_id}/demo-inbox"), 200)["code"]
        ok(await post(inst, f"/v3/issuer-applications/{app_id}/email-verifications",
                      json={"code": code}), 200)
    checks = ok(await inst.get(f"/v3/issuer-applications/{app_id}"), 200)
    if not checks.get("internally_approved"):
        internal = await api.as_(spec["approver"])
        checks = ok(await post(internal, f"/v3/issuer-applications/{app_id}/internal-approvals",
                               json={"decision": "APPROVE", "reason": "합성 시연 내부 승인"}), 200)
    issuer_hash = identifier_hash(spec["issuer"])
    issuer = await WalletRegistryReadAdapter(reader).issuer(issuer_hash)
    if issuer is not None and issuer.state == "ACTIVE":
        say(f"{spec['name']} 이미 활성")
        return inst
    stamp = int(time.time())
    wallet = signers.addresses[spec["wallet"]]
    challenge = SigningRequest.model_validate(ok(await post(inst, "/v3/key-challenges", json={
        "request_id": f"req_key_{who}_{stamp}", "application_id": app_id,
        "signer": wallet.lower()}), 201))
    sig = await signers.sign(chain_client, spec["wallet"], challenge)
    ok(await post(inst, "/v3/key-proofs", json={
        "request_id": f"req_proof_{who}_{stamp}",
        "signing_request_id": challenge.signing_request_id, "signature": sig}), 200)
    op1, op2 = await api.as_("v5_operator1"), await api.as_("v5_operator2")
    prepared = ok(await post(op1, "/v3/proposals", json={
        "request_id": f"req_proposal_{who}_{stamp}",
        "key_proof_request_id": challenge.signing_request_id,
        "proposal": {"action": 1, "issuerId": issuer_hash,
                     "keyId": identifier_hash(f"key_{who}_demo_{stamp}"),
                     "signer": wallet.lower(), "metadataHash": checks["metadata_hash"],
                     "nonce": issuer.governance_nonce if issuer else "0",
                     "deadline": challenge.message.deadline}}), 201)
    pid = prepared["proposal_id"]
    proposal = GovernanceProposal.model_validate(prepared["proposal"])
    proof = KeyProofMessage.model_validate(prepared["key_proof"])
    propose = calldata(reader, "propose", {
        "proposal": proposal.model_dump(by_alias=True) | {"nonce": int(proposal.nonce)},
        "proof": proof.model_dump(by_alias=True), "signature": prepared["key_proof_signature"]})
    tx = await signers.send(chain_client, "approver1", "0x" + propose.hex())
    ok(await post(op1, f"/v3/proposals/{pid}/transactions",
                  json={"request_id": f"req_propose_{who}_{stamp}", "tx_hash": tx}), 202)
    approve = "0x" + calldata(reader, "approve", {"proposalId": pid}).hex()
    for name, client in (("approver1", op1), ("approver2", op2)):
        tx = await signers.send(chain_client, name, approve)
        ok(await post(client, f"/v3/proposals/{pid}/approvals",
                      json={"request_id": f"req_{name}_{who}_{stamp}", "tx_hash": tx}), 202)
    say(f"{spec['name']} 활성화 완료")
    return inst


async def publish(inst, signers, chain_client, reader, who, label, content):
    stamp = time.time_ns()
    doc_key = identifier_hash(f"bulk_{who}_{label}_{stamp}")
    draft = ok(await post(inst, "/v3/document-drafts", json={
        "request_id": f"req_draft_{who}_{stamp}", "doc_key": doc_key, "expected_version": 1,
        "expires_at": int(time.time()) + 30 * 86400, "content": content}), 201)
    signing = SigningRequest.model_validate(draft)
    wallet = ISSUERS[who]["wallet"]
    sig = await signers.sign(chain_client, wallet, signing)
    ok(await post(inst, "/v3/publications", json={
        "request_id": f"req_publish_{who}_{stamp}",
        "signing_request_id": signing.signing_request_id, "signature": sig}), 202)
    data = calldata(reader, "publish", {
        "message": signing.message.model_dump(by_alias=True) | {"nonce": int(signing.message.nonce)},
        "signature": sig})
    tx = await signers.send(chain_client, wallet, "0x" + data.hex())
    op = ok(await post(inst, f"/v3/signing-requests/{signing.signing_request_id}/transactions",
                       json={"request_id": f"req_direct_{who}_{stamp}",
                             "signing_request_id": signing.signing_request_id, "tx_hash": tx}), 202)
    await settle(inst, op)
    return {"issuer": ISSUERS[who]["issuer"], "document_id": signing.message.document_id,
            "version": 1, "content": draft["content"], "tx": tx}


async def run(args):
    target = chain_target("anvil")
    password = json.loads(Path(args.credentials).read_text())["password"]
    deployment, _ = load_wallet_deployment(args.manifest, chain_id=target.chain_id,
                                           address=args.registry)
    api = Api(args.api, password)
    out = []
    async with httpx.AsyncClient(timeout=30, trust_env=False) as chain_client:
        reader = WalletRpc(chain_client, args.rpc_url, **deployment)
        signers = Signers("rpc", args.rpc_url, reader.address,
                          {"approver1": args.approver1, "approver2": args.approver2,
                           "institution": args.institution, "office": args.office}, {})
        try:
            plan = (("bank", PAYMENTS, payment), ("office", OFFICIALS, official))
            for who, rows, make in (r for r in plan if r[0] in args.only.split(",")):
                inst = await onboard(api, signers, chain_client, reader, who)
                for i, row in enumerate(rows, 1):
                    doc = await publish(inst, signers, chain_client, reader, who, i, make(*row))
                    out.append(doc)
                    say(f"{who} #{i} 발행 확정 · {doc['document_id'][:12]}…")
        finally:
            await api.close()
            with open(args.out, "a", encoding="utf-8") as handle:
                for doc in out:
                    handle.write(json.dumps(doc, ensure_ascii=False) + "\n")
    say(f"완료 {len(out)}건 → {args.out}")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("--api", "--rpc-url", "--registry", "--manifest", "--credentials", "--out",
                 "--approver1", "--approver2", "--institution", "--office"):
        p.add_argument(name, required=True)
    p.add_argument("--only", default="bank,office")
    asyncio.run(run(p.parse_args(argv)))


if __name__ == "__main__":
    main()
