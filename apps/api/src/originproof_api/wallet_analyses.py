"""Owned analysis jobs and retention; input selection and real analyzer remain explicit."""

import asyncio
import base64
from io import BytesIO
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from originproof_analyzer.converted_inputs import analyze_conversion, prepare_conversion
from originproof_analyzer.inputs import SemanticInput
from originproof_core.wallet_contract import (
    AnalysisJob,
    AnalysisList,
    AnalysisReport,
    AnalysisRequest,
    InputReceipt,
    TextInputRequest,
    VerificationResult,
)
from originproof_core.wallet_inputs import DocumentImageInputRequest
from PIL import Image
from pydantic import Field
from sqlalchemy import BigInteger, and_, cast, delete, or_, select, update

from .accounts import current_session
from .database import AuditEventRow, OperationRow
from .operations import expired_wallet_audits, expired_wallet_operations, input_fingerprint
from .wallet_database import (
    WalletAnalysisRow,
    WalletDocumentRow,
    WalletInputRow,
    WalletRequestRow,
    WalletSigningRow,
    WalletVerificationRow,
)
from .wallet_onboarding import expire_codes
from .wallet_runtime import now, runtime

router = APIRouter(prefix="/v3", tags=["wallet analyses"])
Identity = Annotated[tuple, Depends(current_session)]
ACTIVE = ("QUEUED", "RUNNING")
InputRequest = Annotated[TextInputRequest | DocumentImageInputRequest, Field(discriminator="kind")]


def input_enabled(settings, kind):
    # kind is TEXT or DOCUMENT_IMAGE: the request model and stored rows allow nothing else.
    if kind == "TEXT":
        return settings.wallet_text_input_enabled
    return settings.wallet_image_input_enabled


def image_format(data):
    """(MIME type, file extension); stored bytes already passed SemanticInput at upload."""
    with Image.open(BytesIO(data)) as image:
        return Image.MIME[image.format], image.format.lower()


async def image_report(converter, processor, data, remaining):
    """Converter reads the photo; the analyzer and C grounding only ever see the read text."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + remaining
    artifact = SemanticInput(
        image_base64=base64.b64encode(data).decode(), image_media_type=image_format(data)[0]
    )
    converted = await converter(artifact, min(remaining, 180))
    left = deadline - loop.time()
    if left <= 0:
        raise TimeoutError
    result = await analyze_conversion(converted, processor, remaining_seconds=min(left, 180))
    return ground_report(result.report, prepare_conversion(converted).text)


def view(row):
    report = row.report if row.report_expires_at and now() < row.report_expires_at else None
    expired = row.status == "COMPLETED" and report is None
    return AnalysisJob(
        analysis_id=row.analysis_id,
        status="EXPIRED" if expired else row.status,
        retain_report=row.retain_report,
        retain_original=row.retain_original,
        result_expires_at=row.report_expires_at,
        original_expires_at=row.original_expires_at,
        report=AnalysisReport.model_validate(report) if report else None,
        error_code=row.error_code,
    )


async def owned_job(db, account, analysis_id):
    row = await db.scalar(
        select(WalletAnalysisRow)
        .where(
            WalletAnalysisRow.analysis_id == analysis_id,
        )
        .with_for_update()
    )
    if row is None or row.account_id != account.account_id:
        raise HTTPException(404, "ANALYSIS_NOT_FOUND")
    return row


def ground_report(value, text):
    report = AnalysisReport.model_validate(
        value.model_dump() if isinstance(value, AnalysisReport) else value
    )
    if report.verification is not None:
        raise ValueError("ANALYZER_AUTHORITY_VIOLATION")
    evidence = []
    for item in report.evidence:
        start, end = item.start_offset, item.end_offset
        if item.page is not None or item.start_ms is not None:
            raise ValueError("GROUNDING_MISMATCH")
        if start is None:
            start = text.find(item.quote)
            if start < 0 or text.find(item.quote, start + 1) >= 0:
                raise ValueError("GROUNDING_MISMATCH")
            end = start + len(item.quote)
        if not 0 <= start < end <= len(text) or text[start:end] != item.quote:
            raise ValueError("GROUNDING_MISMATCH")
        evidence.append(item.model_copy(update={"start_offset": start, "end_offset": end}))
    return report.model_copy(
        update={
            "evidence": evidence,
            "verification": None,
            "verification_not_run_reason": "NO_DOCUMENT_REFERENCE",
        }
    )


async def finish(app, analysis_id, report=None, error=None):
    service = app.state.wallet_runtime
    async with service.database.session_factory() as db:
        row = await db.scalar(
            select(WalletAnalysisRow)
            .where(
                WalletAnalysisRow.analysis_id == analysis_id,
            )
            .with_for_update()
        )
        if row is None or row.status != "RUNNING":
            return  # Deletion/cancellation is a durable fence against late provider responses.
        stamp = now()
        if stamp >= row.accepted_at + 180:
            report, error = None, "ANALYSIS_TIMEOUT"
        if report and row.verification_result:
            report = report.model_copy(
                update={
                    "verification": VerificationResult.model_validate(row.verification_result),
                    "verification_not_run_reason": None,
                }
            )
        row.status, row.completed_at, row.error_code = (
            "COMPLETED" if report else "FAILED",
            stamp,
            error,
        )
        row.report = report.model_dump(mode="json") if report else None
        row.report_expires_at = stamp + (7 * 86400 if row.retain_report else 600)
        artifact = await db.get(WalletInputRow, row.input_id)
        if not row.retain_original or stamp >= artifact.expires_at:
            artifact.original = None
            if not row.retain_original:
                artifact.expires_at = stamp
        await service.commit(db)


async def process(app, analysis_id):
    service = app.state.wallet_runtime
    async with service.database.session_factory() as db:
        row = await db.scalar(
            select(WalletAnalysisRow)
            .where(
                WalletAnalysisRow.analysis_id == analysis_id,
            )
            .with_for_update()
        )
        if row is None or row.status != "QUEUED":
            return
        artifact = await db.get(WalletInputRow, row.input_id)
        kind = artifact.kind
        data = (
            artifact.original
            if (artifact.original is not None and now() < artifact.expires_at)
            else None
        )
        row.status, row.started_at = "RUNNING", now()
        remaining = row.accepted_at + 180 - now()
        await service.commit(db)
    processor = app.state.analysis_processor
    report, error = None, None
    try:
        if remaining <= 0:
            raise TimeoutError
        if data is None:
            error = "INPUT_EXPIRED"
        elif processor is None or (kind != "TEXT" and app.state.image_converter is None):
            error = "ANALYZER_UNAVAILABLE"
        elif kind == "TEXT":
            text = data.decode("utf-8")
            value = await asyncio.wait_for(processor(text), timeout=remaining)
            report = ground_report(value, text)
        else:
            report = await asyncio.wait_for(
                image_report(app.state.image_converter, processor, data, remaining),
                timeout=remaining,
            )
    except TimeoutError:
        error = "ANALYSIS_TIMEOUT"
    except asyncio.CancelledError:
        await finish(app, analysis_id, error="WORKER_STOPPED")
        raise
    except ValueError as problem:
        error = (
            str(problem)
            if str(problem) in ("GROUNDING_MISMATCH", "ANALYZER_AUTHORITY_VIOLATION")
            else "ANALYZER_SCHEMA_MISMATCH"
        )
    except Exception as problem:
        code = getattr(problem, "code", None)
        error = (
            code
            if isinstance(code, str)
            and code
            in {
                "REFUSAL",
                "TIMEOUT",
                "RATE_LIMIT",
                "INCOMPLETE_OUTPUT",
                "SCHEMA_MISMATCH",
                "LOW_CONFIDENCE",
                "PROVIDER_UNAVAILABLE",
                "UNSUPPORTED_INPUT",
                "MALFORMED_INPUT",
            }
            else "ANALYZER_UNAVAILABLE"
        )
    await finish(app, analysis_id, report, error)


def launch(app, analysis_id):
    # shortcut: local in-process workers; use the existing queue for distributed execution.
    task = asyncio.create_task(process(app, analysis_id))
    app.state.analysis_tasks.add(task)

    def completed(worker):
        app.state.analysis_tasks.discard(worker)
        if not worker.cancelled() and worker.exception() is not None:
            app.state.analysis_worker_error = "WORKER_STORAGE_UNAVAILABLE"

    task.add_done_callback(completed)


@router.post("/inputs", response_model=InputReceipt, status_code=201)
async def input_text(body: InputRequest, request: Request, identity: Identity):
    service = runtime(request)
    account = service.authorize(request, identity)
    if not input_enabled(service.settings, body.kind):
        raise HTTPException(409, "INPUT_SUPPORT_UNDECIDED")
    if body.kind == "TEXT":
        if not body.text.strip():
            raise HTTPException(422, "EMPTY_INPUT")
        original = body.text.encode("utf-8")
    else:
        try:
            SemanticInput(image_base64=body.image_base64, image_media_type=body.image_media_type)
        except ValueError:
            # Validation details may echo untrusted image metadata; keep only the code.
            raise HTTPException(422, "MALFORMED_INPUT") from None
        original = base64.b64decode(body.image_base64, validate=True)
    row = WalletInputRow(
        input_id=f"inp_{uuid4().hex}",
        account_id=account.account_id,
        kind=body.kind,
        original=original,
        accepted_at=now(),
        expires_at=now() + 3600,
    )
    async with service.database.session_factory() as db:
        db.add(row)
        await service.commit(db)
    return InputReceipt(input_ref=row.input_id, expires_at=row.expires_at)


@router.post("/analyses", response_model=AnalysisJob, status_code=202)
async def analysis(body: AnalysisRequest, request: Request, identity: Identity):
    service = runtime(request)
    account = service.authorize(request, identity)
    await cleanup(request.app, account_id=account.account_id)
    async with service.database.session_factory() as db:
        await service.lock_account(db, account)
        existing = await db.scalar(
            select(WalletAnalysisRow).where(
                WalletAnalysisRow.account_id == account.account_id,
                WalletAnalysisRow.request_id == body.request_id,
            )
        )
        if existing:
            if existing.input_hash != input_fingerprint(body.model_dump()):
                raise HTTPException(409, "REQUEST_ID_CONFLICT")
            return view(existing)
        artifact = await db.scalar(
            select(WalletInputRow)
            .where(
                WalletInputRow.input_id == body.input_ref,
            )
            .with_for_update()
        )
        if artifact is None or artifact.account_id != account.account_id:
            raise HTTPException(404, "INPUT_NOT_FOUND")
        if not input_enabled(service.settings, artifact.kind):
            raise HTTPException(409, "INPUT_SUPPORT_UNDECIDED")
        if artifact.original is None or now() >= artifact.expires_at:
            raise HTTPException(410, "INPUT_EXPIRED")
        if await db.scalar(
            select(WalletAnalysisRow).where(WalletAnalysisRow.input_id == artifact.input_id)
        ):
            raise HTTPException(409, "INPUT_ALREADY_ANALYZED")
        recent = list(
            await db.scalars(
                select(WalletAnalysisRow).where(
                    WalletAnalysisRow.account_id == account.account_id,
                    WalletAnalysisRow.accepted_at > now() - 600,
                )
            )
        )
        if any(row.status in ACTIVE for row in recent) or len(recent) >= 5:
            raise HTTPException(429, "ANALYSIS_LIMIT", headers={"Retry-After": "600"})
        verification = None
        if body.verification_session_id:
            session = await db.get(WalletVerificationRow, body.verification_session_id)
            if (
                session is None
                or session.privacy_scope == "LEGACY"
                or (session.account_id is not None and session.account_id != account.account_id)
            ):
                raise HTTPException(404, "VERIFICATION_SESSION_NOT_FOUND")
            if now() >= session.expires_at:
                raise HTTPException(410, "VERIFICATION_SESSION_EXPIRED")
            verification = session.result
        original_expiry = (
            artifact.accepted_at + 7 * 86400 if body.retain_original else artifact.expires_at
        )
        artifact.expires_at = original_expiry
        row = WalletAnalysisRow(
            analysis_id=f"ana_{uuid4().hex}",
            account_id=account.account_id,
            input_id=artifact.input_id,
            request_id=body.request_id,
            input_hash=input_fingerprint(body.model_dump()),
            status="QUEUED",
            accepted_at=now(),
            retain_report=body.retain_report,
            retain_original=body.retain_original,
            original_expires_at=original_expiry if body.retain_original else None,
            verification_result=verification,
        )
        db.add(row)
        service.audit(db, account, "wallet_analysis", row.analysis_id, "QUEUED")
        await service.commit(db)
        result = view(row)
    launch(request.app, row.analysis_id)
    return result


@router.get("/analyses", response_model=AnalysisList)
async def history(
    request: Request,
    identity: Identity,
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = Query(default=None, max_length=64),
):
    service = runtime(request)
    account = service.authorize(request, identity, mutation=False)
    async with service.database.session_factory() as db:
        query = select(WalletAnalysisRow).where(
            WalletAnalysisRow.account_id == account.account_id,
            WalletAnalysisRow.status != "CANCELLED",
            or_(
                and_(
                    WalletAnalysisRow.retain_report.is_(True),
                    WalletAnalysisRow.report_expires_at > now(),
                ),
                and_(
                    WalletAnalysisRow.retain_original.is_(True),
                    WalletAnalysisRow.original_expires_at > now(),
                ),
            ),
        )
        if cursor:
            pivot = await owned_job(db, account, cursor)
            query = query.where(
                or_(
                    WalletAnalysisRow.accepted_at < pivot.accepted_at,
                    and_(
                        WalletAnalysisRow.accepted_at == pivot.accepted_at,
                        WalletAnalysisRow.analysis_id < pivot.analysis_id,
                    ),
                )
            )
        rows = list(
            await db.scalars(
                query.order_by(
                    WalletAnalysisRow.accepted_at.desc(), WalletAnalysisRow.analysis_id.desc()
                ).limit(limit + 1)
            )
        )
        return AnalysisList(
            items=[view(row) for row in rows[:limit]],
            next_cursor=rows[limit - 1].analysis_id if len(rows) > limit else None,
        )


@router.get("/analyses/{analysis_id}", response_model=AnalysisJob)
async def job(analysis_id: str, request: Request, identity: Identity):
    service = runtime(request)
    account = service.authorize(request, identity, mutation=False)
    async with service.database.session_factory() as db:
        return view(await owned_job(db, account, analysis_id))


@router.delete("/analyses/{analysis_id}", status_code=204)
async def remove(analysis_id: str, request: Request, identity: Identity):
    service = runtime(request)
    account = service.authorize(request, identity)
    async with service.database.session_factory() as db:
        row = await owned_job(db, account, analysis_id)
        row.status, row.report, row.verification_result = "CANCELLED", None, None
        artifact = await db.get(WalletInputRow, row.input_id)
        artifact.original, artifact.expires_at = None, now()
        service.audit(db, account, "wallet_analysis_delete", analysis_id, "CANCELLED")
        await service.commit(db)
    return Response(status_code=204)


@router.get("/analyses/{analysis_id}/report", response_model=AnalysisReport)
async def report(analysis_id: str, request: Request, identity: Identity):
    service = runtime(request)
    account = service.authorize(request, identity, mutation=False)
    async with service.database.session_factory() as db:
        result = view(await owned_job(db, account, analysis_id)).report
        if result is None:
            raise HTTPException(410, "RESULT_EXPIRED")
        return result


@router.get("/analyses/{analysis_id}/original")
async def original(analysis_id: str, request: Request, identity: Identity):
    service = runtime(request)
    account = service.authorize(request, identity, mutation=False)
    async with service.database.session_factory() as db:
        row = await owned_job(db, account, analysis_id)
        artifact = await db.get(WalletInputRow, row.input_id)
        if (
            row.status == "CANCELLED"
            or not row.retain_original
            or (artifact.original is None or now() >= artifact.expires_at)
        ):
            raise HTTPException(410, "ORIGINAL_UNAVAILABLE")
        media, extension = (
            ("text/plain; charset=utf-8", "txt")
            if artifact.kind == "TEXT"
            else image_format(artifact.original)
        )
        return Response(
            artifact.original,
            media_type=media,
            headers={"Content-Disposition": f'attachment; filename="{analysis_id}.{extension}"'},
        )


async def cleanup(app, *, restart=False, account_id=None):
    if account_id is None:
        await expire_codes(app)
    service = app.state.wallet_runtime
    stamp = now()
    queued = []
    async with service.database.session_factory() as db:
        due = [
            and_(
                WalletAnalysisRow.status.in_(ACTIVE), WalletAnalysisRow.accepted_at <= stamp - 180
            ),
            WalletAnalysisRow.report_expires_at <= stamp,
        ]
        if restart:
            due.append(WalletAnalysisRow.status.in_(ACTIVE))
        query = select(WalletAnalysisRow).where(or_(*due))
        if account_id is not None:
            query = query.where(WalletAnalysisRow.account_id == account_id)
        jobs = list(await db.scalars(query.with_for_update()))
        for row in jobs:
            artifact = await db.get(WalletInputRow, row.input_id)
            timed_out = row.status in ACTIVE and stamp >= row.accepted_at + 180
            interrupted = restart and row.status == "RUNNING"
            if timed_out or interrupted:
                row.status = "FAILED"
                row.completed_at, row.report_expires_at = stamp, stamp + 600
                row.error_code = "ANALYSIS_TIMEOUT" if timed_out else "PROCESS_RESTARTED"
                if not row.retain_original:
                    artifact.original, artifact.expires_at = None, stamp
            if row.report_expires_at and stamp >= row.report_expires_at:
                row.report, row.verification_result = None, None
            if restart and row.status == "QUEUED":
                queued.append(row.analysis_id)
        if account_id is not None:
            await service.commit(db)
            return queued
        await db.execute(
            update(WalletInputRow)
            .where(WalletInputRow.expires_at <= stamp, WalletInputRow.original.is_not(None))
            .values(original=None)
        )
        for doc in await db.scalars(
            select(WalletDocumentRow).where(WalletDocumentRow.retain_until <= stamp)
        ):
            doc.original, doc.signature, doc.content = None, None, {}
        for source in await db.scalars(
            select(WalletSigningRow).where(
                WalletSigningRow.kind == "Publish",
                cast(WalletSigningRow.payload["message"]["expiresAt"].as_string(), BigInteger)
                <= stamp - 30 * 86400,
                or_(
                    WalletSigningRow.signature.is_not(None),
                    WalletSigningRow.payload["original_base64"].as_string().is_not(None),
                ),
            )
        ):
            source.payload = source.payload | {"original_base64": None, "content": None}
            source.signature = None
        await db.execute(
            delete(WalletVerificationRow).where(WalletVerificationRow.expires_at <= stamp)
        )
        expired_operation = expired_wallet_operations(stamp)
        expired_ids = select(OperationRow.operation_id).where(expired_operation)
        await db.execute(
            delete(WalletRequestRow).where(WalletRequestRow.resource_id.in_(expired_ids))
        )
        await db.execute(delete(OperationRow).where(expired_operation))
        await db.execute(delete(AuditEventRow).where(expired_wallet_audits(stamp)))
        await service.commit(db)
    app.state.analysis_worker_error = None
    return queued


async def maintenance(app, stop):
    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(), timeout=300)
        except TimeoutError:
            try:
                await cleanup(app)
            except Exception:
                app.state.analysis_worker_error = "MAINTENANCE_STORAGE_UNAVAILABLE"
