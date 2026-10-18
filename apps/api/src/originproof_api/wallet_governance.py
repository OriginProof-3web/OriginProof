"""Durable key proofs and governance tx intake; only verified chain evidence advances state."""

import secrets
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from originproof_core.canonicalization import canonical_json_bytes
from originproof_core.wallet_contract import (
    GovernanceTransaction,
    KeyChallengeRequest,
    KeyProofMessage,
    KeyProofReceipt,
    OperationView,
    ProposalRequest,
    ProposalView,
    SignedSubmission,
    SigningRequest,
)
from originproof_core.wallet_signatures import identifier_hash, proposal_id, wallet_signer
from sqlalchemy import select

from .accounts import current_session
from .database import IssuerApplicationRow, OperationRow
from .operations import input_fingerprint
from .wallet_database import WalletProposalRow, WalletSigningRow
from .wallet_onboarding import approved_application
from .wallet_runtime import now, runtime, sha256

router = APIRouter(prefix="/v3", tags=["wallet governance"])
Identity = Annotated[tuple, Depends(current_session)]


@router.post("/key-challenges", response_model=SigningRequest, status_code=201)
async def challenge(body: KeyChallengeRequest, request: Request, identity: Identity):
    service = runtime(request)
    account = service.authorize(request, identity, "issuer")
    async with service.database.session_factory() as db:
        await service.lock_account(db, account)
        retry = await service.signing_retry(db, account, "KeyProof", body)
        if retry:
            return SigningRequest.model_validate(retry.payload)
        app, _ = await approved_application(db, body.application_id, account.issuer_id)
        if app.applicant_account_id != account.account_id:
            raise HTTPException(403, "APPLICANT_REQUIRED")
        signing = SigningRequest(
            signing_request_id=f"wsr_{uuid4().hex}",
            primary_type="KeyProof",
            domain=service.domain,
            expected_signer=body.signer,
            message=KeyProofMessage(
                applicationId=identifier_hash(app.application_id),
                issuerId=service.issuer_id(account),
                signer=body.signer,
                challengeNonce="0x" + secrets.token_hex(32),
                deadline=now() + 300,
            ),
        )
        return await service.save_signing(db, account, "KeyProof", body, signing)


@router.post("/key-proofs", response_model=KeyProofReceipt)
async def key_proof(body: SignedSubmission, request: Request, identity: Identity):
    service = runtime(request)
    account = service.authorize(request, identity, "issuer")
    async with service.database.session_factory() as db:
        await service.lock_account(db, account)
        row, signing = await service.owned_signing(db, account, body.signing_request_id, "KeyProof")
        if row.verified_at is not None:
            if row.signature != body.signature or row.verified_request_id != body.request_id:
                raise HTTPException(409, "CHALLENGE_ALREADY_USED")
        else:
            if now() >= row.expires_at:
                raise HTTPException(410, "SIGNATURE_EXPIRED")
            if (
                wallet_signer(signing.domain, signing.message, body.signature)
                != signing.expected_signer
            ):
                raise HTTPException(422, "INVALID_SIGNATURE")
            row.signature, row.verified_request_id = body.signature, body.request_id
            row.verified_at = now()
            service.audit(db, account, "wallet_key_proof", row.signing_request_id, "VERIFIED")
            await service.commit(db)
        return KeyProofReceipt(
            signing_request_id=row.signing_request_id,
            verified_at=row.verified_at,
            expires_at=row.expires_at,
        )


async def proposal_view(service, row):
    if row.domain != service.domain.model_dump(by_alias=True):
        raise HTTPException(409, "DEPLOYMENT_CHANGED")
    saved = ProposalView.model_validate(row.payload)
    chain = await service.rpc("proposal", row.proposal_id)
    if chain:
        if chain.proposal.proposal != saved.proposal:
            raise HTTPException(422, "PROPOSAL_CONTENT_MISMATCH")
        return chain.proposal
    return (
        saved.model_copy(update={"status": "EXPIRED"})
        if now() >= saved.proposal.deadline
        else saved
    )


@router.post("/proposals", response_model=ProposalView, status_code=201)
async def propose(body: ProposalRequest, request: Request, identity: Identity):
    service = runtime(request)
    account, _ = await service.operator(request, identity)
    async with service.database.session_factory() as db:
        await service.lock_account(db, account)
        retry = await db.scalar(
            select(WalletProposalRow).where(
                WalletProposalRow.account_id == account.account_id,
                WalletProposalRow.request_id == body.request_id,
            )
        )
        if retry:
            if retry.input_hash != input_fingerprint(body.model_dump(mode="json")):
                raise HTTPException(409, "REQUEST_ID_CONFLICT")
            return await proposal_view(service, retry)
        proposal = body.proposal
        stamp = now()
        if proposal.deadline <= stamp:
            raise HTTPException(410, "PROPOSAL_EXPIRED")
        issuer = await service.rpc("issuer", proposal.issuer_id)
        nonce = issuer.governance_nonce if issuer else "0"
        if proposal.nonce != nonce:
            raise HTTPException(409, "PROPOSAL_STALE")
        proof_row, proof = None, None
        if proposal.action in (1, 2):
            proof_row = await db.scalar(
                select(WalletSigningRow)
                .where(
                    WalletSigningRow.signing_request_id == body.key_proof_request_id,
                )
                .with_for_update()
            )
            if proof_row is None or proof_row.kind != "KeyProof" or proof_row.verified_at is None:
                raise HTTPException(409, "KEY_PROOF_REQUIRED")
            proof = SigningRequest.model_validate(proof_row.payload)
            if (
                proof.domain != service.domain
                or proof.message.issuer_id != proposal.issuer_id
                or (proof.expected_signer != proposal.signer)
            ):
                raise HTTPException(422, "KEY_PROOF_MISMATCH")
            if proposal.deadline > proof.message.deadline or stamp >= proof.message.deadline:
                raise HTTPException(410, "SIGNATURE_EXPIRED")
            apps = list(
                await db.scalars(
                    select(IssuerApplicationRow).where(
                        IssuerApplicationRow.applicant_account_id == proof_row.account_id,
                    )
                )
            )
            app = next(
                (
                    a
                    for a in apps
                    if identifier_hash(a.application_id) == proof.message.application_id
                ),
                None,
            )
            if app is None:
                raise HTTPException(409, "INSTITUTION_CHECKS_REQUIRED")
            _, checks = await approved_application(db, app.application_id, app.issuer_id)
            if sha256(canonical_json_bytes(checks.metadata_value)) != proposal.metadata_hash:
                raise HTTPException(422, "METADATA_HASH_MISMATCH")
            if (proposal.action == 1 and issuer is not None) or (
                proposal.action == 2 and issuer is None
            ):
                raise HTTPException(409, "ISSUER_STATE_CONFLICT")
            if await service.rpc("key", proposal.key_id) is not None:
                raise HTTPException(409, "KEY_ID_ALREADY_USED")
            maximum = 300
        else:
            if body.key_proof_request_id is not None:
                raise HTTPException(422, "UNEXPECTED_KEY_PROOF")
            if (
                issuer is None
                or issuer.state != "SUSPENDED"
                or (
                    issuer.key_id != proposal.key_id
                    or issuer.signer != proposal.signer
                    or issuer.metadata_hash != proposal.metadata_hash
                )
            ):
                raise HTTPException(409, "ISSUER_STATE_CONFLICT")
            key = await service.rpc("key", issuer.key_id)
            if key is None or key.compromise_block is not None:
                raise HTTPException(409, "KEY_COMPROMISED")
            maximum = 86400
        if proposal.deadline > stamp + maximum:
            raise HTTPException(422, "PROPOSAL_DEADLINE_TOO_LONG")
        pid = proposal_id(service.domain, proposal)
        if proof_row:
            if proof_row.consumed_by:
                raise HTTPException(409, "CHALLENGE_ALREADY_USED")
            proof_row.consumed_by = pid
        result = ProposalView(
            proposal_id=pid,
            proposal=proposal,
            status="PREPARED",
            approvals=[],
            key_proof=proof.message if proof else None,
            key_proof_signature=proof_row.signature if proof_row else None,
        )
        db.add(
            WalletProposalRow(
                proposal_id=pid,
                account_id=account.account_id,
                request_id=body.request_id,
                input_hash=input_fingerprint(body.model_dump(mode="json")),
                domain=service.domain.model_dump(by_alias=True),
                payload=result.model_dump(mode="json"),
            )
        )
        service.audit(db, account, "wallet_proposal_prepared", pid, "PREPARED")
        await service.commit(db)
        return result


@router.get("/proposals/{proposal_id}", response_model=ProposalView)
async def get_proposal(proposal_id: str, request: Request, identity: Identity):
    service = runtime(request)
    await service.operator(request, identity, mutation=False)
    async with service.database.session_factory() as db:
        row = await db.get(WalletProposalRow, proposal_id)
        if row is None:
            raise HTTPException(404, "PROPOSAL_NOT_FOUND")
        return await proposal_view(service, row)


def match_transaction(tx, intent):
    return (
        tx.action == intent["action"]
        and tx.arguments == intent["arguments"]
        and (not intent.get("actor") or tx.sender == intent["actor"])
    )


async def accept_transaction(service, db, row, tx_hash):
    # Persist the receipt lookup intent before any RPC; recovery never submits a transaction.
    row.tx_hash, row.status = tx_hash, "UNKNOWN"
    await service.commit(db)
    tx = await service.rpc("transaction", tx_hash)
    if tx is None:
        return service.operation_view(row)
    if tx.tx_hash != tx_hash or not match_transaction(tx, row.input_body):
        row.status, row.error_code = "FAILED", "DIRECT_TX_MISMATCH"
        await service.commit(db)
        raise HTTPException(422, "DIRECT_TX_MISMATCH")
    row.status = tx.status
    row.chain_evidence = {"block_number": tx.block_number, "block_hash": tx.block_hash}
    if row.status == "CONFIRMED" and row.input_body["action"] in ("Propose", "Approve"):
        pid = row.target_id
        proposal = await db.get(WalletProposalRow, pid)
        state = await proposal_view(service, proposal)
        if state.status == "PREPARED" or (
            row.input_body["action"] == "Approve" and tx.sender not in state.approvals
        ):
            row.status = "UNKNOWN"
    if row.status == "CONFIRMED" and row.input_body["action"] == "Suspend":
        issuer = await service.rpc("issuer", row.target_id)
        if issuer is None or issuer.state != "SUSPENDED":
            row.status = "UNKNOWN"
    await service.commit(db)
    return service.operation_view(row)


@router.post("/proposals/{proposal_id}/transactions", response_model=OperationView, status_code=202)
@router.post("/proposals/{proposal_id}/approvals", response_model=OperationView, status_code=202)
async def proposal_transaction(
    proposal_id: str,
    body: GovernanceTransaction,
    request: Request,
    identity: Identity,
):
    service = runtime(request)
    account, address = await service.operator(request, identity)
    approving = request.url.path.endswith("/approvals")
    action = "wallet_approve" if approving else "wallet_propose"
    async with service.database.session_factory() as db:
        await service.lock_account(db, account)
        bound = body.model_copy()
        # target is part of the fingerprint, so one request ID cannot accept another proposal.
        fingerprint = input_fingerprint(body.model_dump() | {"proposal_id": proposal_id})
        retry = await db.scalar(
            select(OperationRow)
            .where(
                OperationRow.account_id == account.account_id,
                OperationRow.action == action,
                OperationRow.request_id == body.request_id,
            )
            .with_for_update()
        )
        if retry:
            if retry.input_hash != fingerprint:
                raise HTTPException(409, "REQUEST_ID_CONFLICT")
            return service.operation_view(retry)
        row = await db.get(WalletProposalRow, proposal_id)
        if row is None:
            raise HTTPException(404, "PROPOSAL_NOT_FOUND")
        view = await proposal_view(service, row)
        arguments = (
            {"proposalId": proposal_id}
            if approving
            else {
                "proposal": view.proposal.model_dump(by_alias=True),
                "proof": view.key_proof.model_dump(by_alias=True)
                if view.key_proof
                else {
                    "action": 0,
                    "applicationId": "0x" + "00" * 32,
                    "issuerId": "0x" + "00" * 32,
                    "signer": "0x" + "00" * 20,
                    "challengeNonce": "0x" + "00" * 32,
                    "deadline": 0,
                },
                "signature": view.key_proof_signature or "0x",
            }
        )
        operation = service.operation(
            db,
            account,
            action,
            bound,
            proposal_id,
            {
                "action": "Approve" if approving else "Propose",
                "actor": address,
                "arguments": arguments,
            },
        )
        operation.input_hash = fingerprint
        await service.commit(db)
        return await accept_transaction(service, db, operation, body.tx_hash)


@router.post("/issuers/{issuer_id}/suspensions", response_model=OperationView, status_code=202)
async def suspension(
    issuer_id: str, body: GovernanceTransaction, request: Request, identity: Identity
):
    service = runtime(request)
    account = service.authorize(request, identity)
    if account.role == "operator":
        _, actor = await service.operator(request, identity)
    elif account.role == "issuer" and service.issuer_id(account) == issuer_id:
        issuer = await service.rpc("issuer", issuer_id)
        if issuer is None:
            raise HTTPException(404, "ISSUER_NOT_FOUND")
        actor = issuer.signer
    else:
        raise HTTPException(403, "FORBIDDEN")
    async with service.database.session_factory() as db:
        await service.lock_account(db, account)
        retry = await service.operation_retry(db, account, "wallet_suspend", body)
        if retry:
            if retry.target_id != issuer_id:
                raise HTTPException(409, "REQUEST_ID_CONFLICT")
            return service.operation_view(retry)
        tx = await service.rpc("transaction", body.tx_hash)
        if (
            tx is None
            or tx.arguments.get("issuerId") != issuer_id
            or (
                tx.arguments.get("reasonCode")
                not in {identifier_hash(x) for x in ("KEY_COMPROMISE", "ABUSE_REPORT", "OTHER")}
            )
        ):
            raise HTTPException(422, "DIRECT_TX_MISMATCH")
        operation = service.operation(
            db,
            account,
            "wallet_suspend",
            body,
            issuer_id,
            {"action": "Suspend", "actor": actor, "arguments": tx.arguments},
        )
        await service.commit(db)
        return await accept_transaction(service, db, operation, body.tx_hash)
