"""Input-independent text analysis preparation; no HTTP route or input is activated."""

from __future__ import annotations

import asyncio
import logging
import re
from time import perf_counter

from originproof_core.wallet_contract import AnalysisEvidence, AnalysisReport
from pydantic import ValidationError

from .errors import AnalyzerError, AnalyzerErrorCode
from .inputs import SemanticInput
from .providers import (
    ANALYSIS_PROMPT_VERSION,
    LLMProvider,
    MockLLMProvider,
    OpenAILLMProvider,
)
from .settings import AnalyzerSettings

logger = logging.getLogger(__name__)
RULE_VERSION = "phishing-rules-0.1"
_PRIORITY = {"NO_CLEAR_INDICATORS": 0, "UNDETERMINED": 0, "CAUTION": 1, "HIGH": 2}
_ASK = r"(?:해\s*주(?:세요|십시오)|하(?:세요|십시오)|해라|해\s*줘|주세요|주십시오)"
_RULES = (
    (
        "CREDENTIAL_REQUEST",
        "HIGH",
        rf"(?:인증번호|비밀번호|보안카드\s*번호|OTP).{{0,25}}?"
        rf"(?:알려\s*주(?:세요|십시오)|보내\s*주(?:세요|십시오)|전달{_ASK}|공유{_ASK}|입력{_ASK})",
    ),
    (
        "REMOTE_CONTROL_REQUEST",
        "HIGH",
        rf"원격\s*(?:제어|지원).{{0,25}}?(?:설치|실행){_ASK}",
    ),
    (
        "URGENT_TRANSFER",
        "HIGH",
        rf"(?:지금|즉시|당장|[0-9]+분\s*이내).{{0,35}}?(?:송금|입금|이체){_ASK}",
    ),
    (
        "ACCOUNT_CHANGE",
        "CAUTION",
        rf"(?:새|변경된|바뀐).{{0,8}}?계좌.{{0,30}}?(?:송금|입금|이체){_ASK}",
    ),
    (
        "BLOCK_OFFICIAL_CHECK",
        "HIGH",
        r"(?:은행|기관|공식\s*창구|가족).{0,20}?(?:확인|연락|전화).{0,8}?"
        r"(?:하지\s*마(?:세요)?|하지\s*말(?:고|아야)|금지합니다)",
    ),
)
_PATTERNS = [(name, level, re.compile(pattern)) for name, level, pattern in _RULES]


def rule_analysis(text: str) -> AnalysisReport:
    """Match a request and its context; a keyword, negation or quoted warning is insufficient."""
    evidence = []
    level = "NO_CLEAR_INDICATORS"
    for sentence in re.finditer(r"[^\n.!?]+", text):
        value = sentence.group()
        quoted = []
        if re.search(r"예방|교육|경고|예시|사례|사기\s*문구", value) and re.search(
            r"예시|사례|무시|거절|응하지|따르지|속지|주의", value
        ):
            quoted = list(re.finditer(r"""["'“‘「『][^"'”’」』\n]+["'”’」』]""", value))
        for name, risk, pattern in _PATTERNS:
            for match in pattern.finditer(value):
                if any(q.start() <= match.start() and match.end() <= q.end() for q in quoted):
                    continue
                start = sentence.start() + match.start()
                evidence.append(
                    AnalysisEvidence(
                        rule_id=name,
                        quote=match.group(),
                        start_offset=start,
                        end_offset=sentence.start() + match.end(),
                        source="RULE",
                    )
                )
                if _PRIORITY[risk] > _PRIORITY[level]:
                    level = risk
    return AnalysisReport(
        risk_level=level,
        evidence=evidence[:50],
        limitations=["RULE_SCAN_NOT_A_SAFETY_GUARANTEE", RULE_VERSION],
        verification_not_run_reason="ANALYZER_DOES_NOT_VERIFY",
    )


def validate_analysis_report(value, text: str) -> AnalysisReport:
    """Revalidate provider objects and bind every quote to exact original code points."""
    try:
        report = AnalysisReport.model_validate(
            value.model_dump(warnings=False) if isinstance(value, AnalysisReport) else value,
            strict=True,
        )
    except (ValueError, TypeError, ValidationError):
        raise AnalyzerError(AnalyzerErrorCode.SCHEMA_MISMATCH) from None
    if report.verification is not None:
        raise ValueError("ANALYZER_AUTHORITY_VIOLATION")
    # Also consume the tighter 0.2 draft limits while retaining the merged 0.1 model.
    if len(report.evidence) > 50 or len(report.limitations) > 20:
        raise AnalyzerError(AnalyzerErrorCode.SCHEMA_MISMATCH)
    if any(len(item) > 500 for item in report.limitations):
        raise AnalyzerError(AnalyzerErrorCode.SCHEMA_MISMATCH)
    grounded = []
    for item in report.evidence:
        if not item.quote or not 1 <= len(item.rule_id) <= 100:
            raise AnalyzerError(AnalyzerErrorCode.SCHEMA_MISMATCH)
        if item.page is not None or item.start_ms is not None:
            raise ValueError("GROUNDING_MISMATCH")
        start, end = item.start_offset, item.end_offset
        if start is None:
            start = text.find(item.quote)
            # find from +1 also detects overlapping occurrences (C finding DG12).
            if start < 0 or text.find(item.quote, start + 1) >= 0:
                raise ValueError("GROUNDING_MISMATCH")
            end = start + len(item.quote)
        if not 0 <= start < end <= len(text) or text[start:end] != item.quote:
            raise ValueError("GROUNDING_MISMATCH")
        grounded.append(item.model_copy(update={"start_offset": start, "end_offset": end}))
    if report.risk_level in {"HIGH", "CAUTION"} and not grounded:
        raise ValueError("GROUNDING_MISMATCH")
    return report.model_copy(
        update={
            "evidence": grounded,
            "verification_not_run_reason": "ANALYZER_DOES_NOT_VERIFY",
        }
    )


class PhishingAnalyzer:
    """C's async analysis_processor(text) callback; default mock makes no paid request."""

    def __init__(
        self, provider: LLMProvider | None = None, *, settings: AnalyzerSettings | None = None
    ) -> None:
        configured = settings or AnalyzerSettings()
        self.provider = provider or (
            OpenAILLMProvider(configured)
            if configured.llm_provider == "openai"
            else MockLLMProvider()
        )

    async def __call__(self, text: str) -> AnalysisReport:
        started, error, exception_type = perf_counter(), None, None
        try:
            try:
                text = SemanticInput(text=text).text
                text.encode("utf-8")
            except (ValueError, TypeError, AttributeError):
                raise AnalyzerError(AnalyzerErrorCode.MALFORMED_INPUT) from None
            rules = rule_analysis(text)
            try:
                # C's remaining job budget may cancel this earlier. Cancellation propagates.
                async with asyncio.timeout(180):
                    raw = await self.provider.analyze_phishing(text)
                model = validate_analysis_report(raw, text)
                if any(item.source != "LLM" for item in model.evidence):
                    raise AnalyzerError(AnalyzerErrorCode.SCHEMA_MISMATCH)
            except Exception as problem:
                if isinstance(problem, AnalyzerError):
                    error = problem.code.value
                elif isinstance(problem, TimeoutError):
                    error = "TIMEOUT"
                elif isinstance(problem, ValueError):
                    error = (
                        str(problem)
                        if str(problem)
                        in {
                            "GROUNDING_MISMATCH",
                            "ANALYZER_AUTHORITY_VIOLATION",
                        }
                        else "SCHEMA_MISMATCH"
                    )
                else:
                    error = "PROVIDER_UNAVAILABLE"
                    exception_type = type(problem).__name__
                return rules.model_copy(
                    update={
                        "risk_level": rules.risk_level if rules.evidence else "UNDETERMINED",
                        "limitations": [
                            *rules.limitations,
                            "LLM_ANALYSIS_UNAVAILABLE:" + error,
                        ],
                    }
                )
            evidence = (
                model.evidence + rules.evidence
                if _PRIORITY[model.risk_level] > _PRIORITY[rules.risk_level]
                else rules.evidence + model.evidence
            )
            level = model.risk_level
            if _PRIORITY[rules.risk_level] > _PRIORITY[level]:
                level = rules.risk_level
            limitations = [*rules.limitations]
            if self.provider.provider_name == "mock":
                limitations.append("MOCK_REPLAY_NOT_MODEL_PERFORMANCE")
            if rules.evidence and model.risk_level != rules.risk_level:
                limitations.append("RULE_LLM_DISAGREEMENT")
            if len(evidence) > 50:
                limitations.append("EVIDENCE_LIMIT_TRUNCATED")
            if len(limitations) + len(model.limitations) > 20:
                limitations.append("LIMITATIONS_LIMIT_TRUNCATED")
            return AnalysisReport(
                risk_level=level,
                evidence=evidence[:50],
                limitations=(limitations + ["LLM: " + value[:495] for value in model.limitations])[
                    :20
                ],
                verification_not_run_reason="ANALYZER_DOES_NOT_VERIFY",
            )
        except AnalyzerError as problem:
            error = problem.code.value
            raise
        finally:
            logger.info(
                "analyzer.analysis",
                extra={
                    "analyzer": {
                        "provider": self.provider.provider_name,
                        "model": self.provider.model,
                        "prompt_version": ANALYSIS_PROMPT_VERSION,
                        "duration_ms": round((perf_counter() - started) * 1000),
                        "error_code": error,
                        "exception_type": exception_type,
                    }
                },
            )
