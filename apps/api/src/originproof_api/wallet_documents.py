"""Institution-signed originals and durable submissions; no institution private keys."""

import base64
import hashlib
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from originproof_core.canonicalization import canonical_json_bytes
from originproof_core.wallet_contract import (
    DirectTransaction,
    DocumentDraftRequest,
    DocumentView,
    Hex32,
    OfficialContent,
    OperationView,
    PaymentContent,
    PublishMessage,
    SignedSubmission,
    SigningRequest,
    VerificationMaterial,
    VerificationRequest,
    VerificationResult,
)
from originproof_core.wallet_signatures import (
    CONTENT_SCHEMAS,
    SIGNATURE_SCHEMA,
    document_id,
    original_bytes,
    wallet_signer,
)
from originproof_core.wallet_verification import verify_wallet_document
from sqlalchemy import select

from .accounts import current_session
from .database import IssuerApplicationRow, OperationRow
from .operations import input_fingerprint
from .wallet_database import (
    WalletDocumentRow,
    WalletInputRow,
    WalletOnboardingRow,
    WalletRequestRow,
    WalletSigningRow,
    WalletVerificationRow,
)
from .wallet_governance import accept_transaction
from .wallet_onboarding import approved_application
from .wallet_runtime import now, runtime

router = APIRouter(prefix="/v3", tags=["wallet documents"])
Identity = Annotated[tuple, Depends(current_session)]


async def optional_session(request: Request):
    try:
        return await current_session(request)
    except HTTPException as error:
        if error.status_code != 401:
            raise
        return None


async def issuer_checks(service, db, account, *, publishing=True):
    app = await db.scalar(
        select(IssuerApplicationRow)
        .where(
            IssuerApplicationRow.issuer_id == account.issuer_id,
        )
        .with_for_update()
    )
    if app is None:
        raise HTTPException(409, "INSTITUTION_CHECKS_REQUIRED")
    await approved_application(db, app.application_id, account.issuer_id)
    issuer = await service.rpc("issuer", service.issuer_id(account))
    if issuer is None:
        raise HTTPException(409, "ISSUER_NOT_REGISTERED")
    if publishing and issuer.state != "ACTIVE":
        raise HTTPException(409, "ISSUER_SUSPENDED")
    key = await service.rpc("key", issuer.key_id)
    if (
        key is None
        or key.issuer_id != issuer.issuer_id
        or key.signer != issuer.signer
        or (key.retired_block is not None or key.compromise_block is not None)
    ):
        raise HTTPException(409, "KEY_NOT_ACTIVE")
    return issuer


@router.post("/document-drafts", response_model=SigningRequest, status_code=201)
async def document_draft(body: DocumentDraftRequest, request: Request, identity: Identity):
    service = runtime(request)
    account = service.authorize(request, identity, "issuer")
    async with service.database.session_factory() as db:
        await service.lock_account(db, account)
        retry = await service.signing_retry(db, account, "Publish", body)
        if retry:
            return SigningRequest.model_validate(retry.payload)
        issuer = await issuer_checks(service, db, account)
        if isinstance(body.content, OfficialContent) and (
            body.content.institution_code != account.issuer_id.removeprefix("iss_").upper()
        ):
            raise HTTPException(422, "INSTITUTION_CODE_MISMATCH")
        did = document_id(issuer.issuer_id, body.doc_key)
        current = await service.rpc("document", did, None)
        if current is not None or body.expected_version != 1:
            raise HTTPException(409, "VERSION_CONFLICT")
        issued = now()
        if body.expires_at <= issued:
            raise HTTPException(422, "EXPIRY_IN_PAST")
        values = dict(
            action=1,
            issuerId=issuer.issuer_id,
            docKey=body.doc_key,
            documentId=did,
            version=body.expected_version,
            keyId=issuer.key_id,
            originalHash="0x" + "00" * 32,
            protectedHash="0x" + hashlib.sha256(canonical_json_bytes(body.content)).hexdigest(),
            contentSchema=CONTENT_SCHEMAS[body.content.notice_type],
            signatureSchema=SIGNATURE_SCHEMA,
            issuedAt=issued,
            expiresAt=body.expires_at,
            nonce=issuer.next_nonce,
            deadline=min(issued + 300, body.expires_at),
        )
        message = PublishMessage.model_validate(values)
        raw = original_bytes(message, body.content)
        message = message.model_copy(
            update={"original_hash": "0x" + hashlib.sha256(raw).hexdigest()}
        )
        try:
            signing = SigningRequest(
                signing_request_id=f"wsr_{uuid4().hex}",
                primary_type="Publish",
                domain=service.domain,
                message=message,
                expected_signer=issuer.signer,
                original_base64=base64.b64encode(raw).decode(),
                content=body.content,
            )
        except ValueError:
            raise HTTPException(422, "CONTENT_OR_PERIOD_INVALID") from None
        return await service.save_signing(db, account, "Publish", body, signing)


async def submit_signed(body, request, identity, kind):
    service = runtime(request)
    account = service.authorize(request, identity, "issuer")
    async with service.database.session_factory() as db:
        await service.lock_account(db, account)
        retry = await service.operation_retry(db, account, "wallet_" + kind.lower(), body)
        if retry:
            return service.operation_view(retry)
        saved, signing = await service.owned_signing(db, account, body.signing_request_id, kind)
        if saved.consumed_by:
            operation = await db.get(OperationRow, saved.consumed_by)
            if operation is None:
                raise HTTPException(410, "RESULT_EXPIRED")
            if saved.signature != body.signature:
                raise HTTPException(409, "SIGNATURE_ALREADY_SUBMITTED")
            db.add(
                WalletRequestRow(
                    account_id=account.account_id,
                    action="wallet_" + kind.lower(),
                    request_id=body.request_id,
                    input_hash=input_fingerprint(body.model_dump(mode="json")),
                    resource_id=operation.operation_id,
                )
            )
            await service.commit(db)
            return service.operation_view(operation)
        if now() >= signing.message.deadline:
            raise HTTPException(410, "SIGNATURE_EXPIRED")
        issuer = await issuer_checks(service, db, account, publishing=kind == "Publish")
        if issuer.key_id != signing.message.key_id or issuer.signer != signing.expected_signer:
            raise HTTPException(409, "KEY_NOT_ACTIVE")
        if signing.message.issuer_id != issuer.issuer_id:
            raise HTTPException(403, "DOCUMENT_OWNER_MISMATCH")
        if wallet_signer(signing.domain, signing.message, body.signature) != issuer.signer:
            raise HTTPException(422, "INVALID_SIGNATURE")
        if signing.message.nonce != issuer.next_nonce:
            raise HTTPException(409, "NONCE_ALREADY_USED")
        pending = list(
            await db.scalars(
                select(OperationRow).where(
                    OperationRow.issuer_id == account.issuer_id,
                    OperationRow.action.in_(("wallet_publish", "wallet_revoke")),
                    OperationRow.status.in_(("PENDING_SUBMISSION", "SUBMITTED", "UNKNOWN")),
                )
            )
        )
        if any(
            row.input_body["arguments"]["message"]["nonce"] == issuer.next_nonce for row in pending
        ):
            raise HTTPException(409, "NONCE_ALREADY_RESERVED")
        message = signing.message
        chain = await service.rpc("document", message.document_id, None)
        if kind == "Publish":
            if chain is not None or message.version != 1:
                raise HTTPException(409, "VERSION_CONFLICT")
        intent = {
            "action": kind,
            "arguments": {
                "message": message.model_dump(by_alias=True),
                "signature": body.signature,
            },
            "signing_request_id": saved.signing_request_id,
            "document_id": message.document_id,
            "version": message.version,
        }
        operation = service.operation(
            db, account, "wallet_" + kind.lower(), body, message.document_id, intent
        )
        saved.signature, saved.consumed_by = body.signature, operation.operation_id
        await service.commit(db)
        if not service.settings.wallet_relay_enabled:
            return service.operation_view(operation)
        # Save uncertainty before the external call so a crash cannot trigger auto-resend.
        operation.status = "UNKNOWN"
        await service.commit(db)
        try:
            tx_hash = await service.rpc("submit", signing, body.signature)
            if tx_hash:
                return await accept_transaction(service, db, operation, tx_hash)
        except HTTPException as error:
            if error.status_code != 503:
                raise
        return service.operation_view(operation)


@router.post("/publications", response_model=OperationView, status_code=202)
async def publication(body: SignedSubmission, request: Request, identity: Identity):
    return await submit_signed(body, request, identity, "Publish")


@router.post(
    "/signing-requests/{signing_request_id}/transactions",
    response_model=OperationView,
    status_code=202,
)
async def direct_transaction(
    signing_request_id: str,
    body: DirectTransaction,
    request: Request,
    identity: Identity,
):
    service = runtime(request)
    account = service.authorize(request, identity, "issuer")
    if body.signing_request_id != signing_request_id:
        raise HTTPException(422, "SIGNING_REQUEST_MISMATCH")
    async with service.database.session_factory() as db:
        await service.lock_account(db, account)
        fingerprint = input_fingerprint(body.model_dump() | {"path": signing_request_id})
        claim_key = (account.account_id, "direct_transaction", body.request_id)
        claim = await db.get(WalletRequestRow, claim_key)
        if claim and claim.input_hash != fingerprint:
            raise HTTPException(409, "REQUEST_ID_CONFLICT")
        saved, _ = await service.owned_signing(db, account, signing_request_id)
        if saved.signature is None or saved.consumed_by is None:
            raise HTTPException(409, "SIGNED_SUBMISSION_REQUIRED")
        operation = await db.scalar(
            select(OperationRow)
            .where(
                OperationRow.operation_id == saved.consumed_by,
            )
            .with_for_update()
        )
        if operation is None:
            raise HTTPException(410, "RESULT_EXPIRED")
        if operation.tx_hash and operation.tx_hash != body.tx_hash:
            raise HTTPException(409, "DIRECT_TX_ALREADY_BOUND")
        if claim is None:
            db.add(
                WalletRequestRow(
                    account_id=account.account_id,
                    action="direct_transaction",
                    request_id=body.request_id,
                    input_hash=fingerprint,
                    resource_id=operation.operation_id,
                )
            )
            await service.commit(db)
        if operation.status in ("CONFIRMED", "FAILED"):
            return service.operation_view(operation)
        return await accept_transaction(service, db, operation, body.tx_hash)


async def owned_operation(service, db, operation_id, account):
    row = await db.scalar(
        select(OperationRow)
        .where(
            OperationRow.operation_id == operation_id,
        )
        .with_for_update()
    )
    if (
        row is None
        or not row.action.startswith("wallet_")
        or (
            row.account_id != account.account_id
            and not (
                account.role == "issuer"
                and account.issuer_id
                and row.issuer_id == account.issuer_id
            )
        )
    ):
        raise HTTPException(404, "OPERATION_NOT_FOUND")
    if row.recovery_reference.get("domain") != service.domain.model_dump(by_alias=True):
        raise HTTPException(409, "DEPLOYMENT_CHANGED")
    return row


@router.get("/operations/{operation_id}", response_model=OperationView)
async def get_operation(operation_id: str, request: Request, identity: Identity):
    service = runtime(request)
    account = service.authorize(request, identity, mutation=False)
    async with service.database.session_factory() as db:
        return service.operation_view(await owned_operation(service, db, operation_id, account))


@router.post("/operations/{operation_id}/reconcile", response_model=OperationView, status_code=202)
async def reconcile(operation_id: str, request: Request, identity: Identity):
    service = runtime(request)
    account = service.authorize(request, identity)
    async with service.database.session_factory() as db:
        row = await owned_operation(service, db, operation_id, account)
        if row.status in ("CONFIRMED", "FAILED"):
            return service.operation_view(row)
        tx = await service.rpc("find_transaction", row.input_body)
        if tx:
            return await accept_transaction(service, db, row, tx.tx_hash)
        if row.tx_hash:
            result = await accept_transaction(service, db, row, row.tx_hash)
            if result.status in ("CONFIRMED", "FAILED"):
                return result
        if row.input_body["action"] in ("Publish", "Revoke"):
            message = row.input_body["arguments"]["message"]
            if now() >= message["deadline"]:
                issuer = await service.rpc("issuer", message["issuerId"])
                chain = await service.rpc("document", message["documentId"], message["version"])
                absent = (
                    chain is None
                    if row.input_body["action"] == "Publish"
                    else (chain is not None and chain.document.state != "REVOKED")
                )
                if issuer and issuer.next_nonce == message["nonce"] and absent:
                    row.status, row.error_code = "FAILED", "SIGNATURE_EXPIRED"
                    row.recovery_reference = row.recovery_reference | {"resolved_at": now()}
                    await service.commit(db)
        return service.operation_view(row)


def document_key(service, did, version):
    return (service.domain.chain_id, service.domain.verifying_contract, did, version)


@router.get("/documents/{document_id}", response_model=DocumentView)
async def get_document(
    document_id: Hex32,
    request: Request,
    version: int | None = Query(default=None, ge=1, le=2**53 - 1),
):
    service = runtime(request)
    chain = await service.rpc("document", document_id, version)
    if chain is None:
        raise HTTPException(404, "DOCUMENT_NOT_FOUND")
    if chain.document.document_id != document_id or (
        version is not None and chain.document.version != version
    ):
        raise HTTPException(503, "CHAIN_RECORD_MISMATCH")
    issuer = await service.rpc("issuer", chain.document.issuer_id)
    key = await service.rpc("key", chain.document.key_id)
    warnings = []
    if issuer is None or key is None:
        warnings.append("CHAIN_UNAVAILABLE")
    else:
        if issuer.state == "SUSPENDED":
            warnings.append("ISSUER_SUSPENDED")
        if key.compromise_block is not None:
            warnings.append("KEY_COMPROMISED")
    async with service.database.session_factory() as db:
        row = await db.get(
            WalletDocumentRow, document_key(service, document_id, chain.document.version)
        )
        available = row is not None and row.original is not None and now() < row.retain_until
    state = chain.document.state
    if state == "ACTIVE" and now() >= chain.document.expires_at:
        state = "EXPIRED"
    return chain.document.model_copy(
        update={"state": state, "warnings": warnings, "original_available": available}
    )


@router.get("/documents/{document_id}/verification-material", response_model=VerificationMaterial)
async def verification_material(
    document_id: Hex32,
    request: Request,
    version: int | None = Query(default=None, ge=1, le=2**53 - 1),
):
    service = runtime(request)
    chain = await service.rpc("document", document_id, version)
    if chain is None:
        raise HTTPException(404, "DOCUMENT_NOT_FOUND")
    if chain.document.document_id != document_id or (
        version is not None and chain.document.version != version
    ):
        raise HTTPException(503, "CHAIN_RECORD_MISMATCH")
    async with service.database.session_factory() as db:
        row = await db.get(
            WalletDocumentRow, document_key(service, document_id, chain.document.version)
        )
        if (
            row is None
            or row.original is None
            or row.signature is None
            or now() >= row.retain_until
        ):
            raise HTTPException(410, "ORIGINAL_UNAVAILABLE")
        saved = await db.get(WalletSigningRow, row.signing_request_id)
        try:
            signing = SigningRequest.model_validate(
                saved.payload
                | {
                    "message": row.message,
                    "content": row.content,
                    "original_base64": base64.b64encode(row.original).decode(),
                }
            )
            from originproof_core.wallet_verification import matches_document

            if not matches_document(signing.message, chain.document):
                raise ValueError("chain mismatch")
        except ValueError:
            raise HTTPException(409, "STORED_CONTENT_MISMATCH") from None
        return VerificationMaterial(
            signing_request=signing,
            signature=row.signature,
            block_number=chain.block_number,
            block_hash=chain.block_hash,
        )


@router.post("/verifications", response_model=VerificationResult)
async def verify_document(
    body: VerificationRequest,
    request: Request,
    identity: Annotated[tuple | None, Depends(optional_session)],
):
    service = runtime(request)
    chain, issuer, key, unavailable = None, None, None, False
    try:
        chain = await service.rpc("document", body.document_id, body.version)
        if chain:
            issuer = await service.rpc("issuer", chain.document.issuer_id)
            key = await service.rpc("key", chain.document.key_id)
    except HTTPException as error:
        if error.status_code != 503:
            raise
        unavailable = True
    original_candidate, message, content, signature, original, metadata = (None,) * 6
    tampered = False
    async with service.database.session_factory() as db:
        if body.original_ref:
            if identity is None:
                raise HTTPException(401, "AUTH_REQUIRED")
            artifact = await db.get(WalletInputRow, body.original_ref)
            if artifact is None or artifact.account_id != identity[0].account_id:
                raise HTTPException(404, "INPUT_NOT_FOUND")
            if artifact.original is not None and now() < artifact.expires_at:
                original_candidate = artifact.original
        version = chain.document.version if chain else body.version
        row = (
            await db.get(WalletDocumentRow, document_key(service, body.document_id, version))
            if version
            else None
        )
        if row and now() < row.retain_until:
            try:
                message = PublishMessage.model_validate(row.message)
                model = (
                    PaymentContent
                    if row.content.get("notice_type") == "PAYMENT_REQUEST"
                    else OfficialContent
                )
                content = model.model_validate(row.content)
                original, signature = row.original, row.signature
            except ValueError:
                tampered = True
        if row:
            apps = list(await db.scalars(select(IssuerApplicationRow)))
            app = next((a for a in apps if service.issuer_id(a) == row.issuer_id), None)
            onboarding = await db.get(WalletOnboardingRow, app.application_id) if app else None
            metadata = onboarding.metadata_value | {"name": app.issuer_name} if onboarding else None
    result = verify_wallet_document(
        body,
        service.domain,
        checked_at=now(),
        chain=chain,
        issuer=issuer,
        key=key,
        message=message,
        content=content,
        signature=signature,
        original=original,
        candidate_original=original_candidate,
        metadata=metadata,
        unavailable=unavailable,
        database_tampered=tampered,
    )
    async with service.database.session_factory() as db:
        db.add(
            WalletVerificationRow(
                session_id=result.session_id,
                expires_at=now() + 86400,
                result=result.model_dump(mode="json"),
            )
        )
        await service.commit(db)
    return result
