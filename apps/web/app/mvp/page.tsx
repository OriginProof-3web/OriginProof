"use client";

import { FormEvent, useMemo, useState } from "react";

import type {
  VerificationRequest,
  VerificationResult,
} from "../../../../packages/schemas/generated/types/originproof";

type FormState = {
  proofId: string;
  issuerName: string;
  maskedCard: string;
  amountMinor: string;
  currency: string;
  merchant: string;
  approvedAt: string;
  transactionId: string;
  confidence: string;
  requestId: string;
};

type ApiError = { error: string; request_id?: string };

const normalPreset: FormState = {
  proofId: "prf_demo_001",
  issuerName: "Origin Mock Bank",
  maskedCard: "1234",
  amountMinor: "154000",
  currency: "KRW",
  merchant: "ORIGIN CAFE",
  approvedAt: "2026-09-03T03:14",
  transactionId: "txn_demo_001",
  confidence: "1",
  requestId: "req_demo_normal",
};

const tamperedPreset: FormState = {
  ...normalPreset,
  amountMinor: "1540000",
  requestId: "req_demo_amount_tampered",
};

const flowSteps = [
  ["1", "입력 후보", "M2가 추출한 것으로 가정한 합성 카드 알림 필드"],
  ["2", "Signed Proof", "M1이 서버에 저장된 신뢰 Proof를 조회"],
  ["3", "체인 신뢰 상태", "M4 Reader가 M3 Issuer·Key Registry를 조회"],
  ["4", "결정", "M1이 서명·해시·핵심 필드를 비교해 최종 판정"],
] as const;

const baselineProof = {
  issuerId: "iss_origin_mock_bank",
  keyId: "key_origin_mock_bank_001",
  chainId: "31337 (local Anvil)",
  card: "Origin Mock Bank · Synthetic Card •••• 1234",
  transaction: "ORIGIN CAFE · 154,000 KRW · 2026-09-03 12:14 KST",
} as const;

function asUtc(value: string): string {
  return `${value.length === 16 ? `${value}:00` : value}Z`;
}

function statusClass(status?: string): string {
  if (status === "VERIFIED") return "verified";
  if (status === "TAMPERED") return "tampered";
  if (status === "INCONCLUSIVE") return "inconclusive";
  return "neutral";
}

function checkValue(
  result: VerificationResult | null,
  checkName: string,
  isSubmitting: boolean,
): string {
  if (isSubmitting) return "검증 중";
  if (!result) return "API 응답 대기";
  return result.checks[checkName] ?? "결과에 없음";
}

export default function DemoPage() {
  const [form, setForm] = useState<FormState>(normalPreset);
  const [result, setResult] = useState<VerificationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const requestBody = useMemo<VerificationRequest>(
    () => ({
      proof_id: form.proofId,
      request_id: form.requestId,
      candidate: {
        issuer_name: form.issuerName || null,
        masked_card: form.maskedCard || null,
        amount_minor: form.amountMinor ? Number(form.amountMinor) : null,
        currency: form.currency.toUpperCase() || null,
        merchant: form.merchant || null,
        approved_at: form.approvedAt ? asUtc(form.approvedAt) : null,
        transaction_id: form.transactionId || null,
        proof_id: form.proofId || null,
        confidence: Number(form.confidence),
        missing_fields: [],
      },
    }),
    [form],
  );

  function updateField(field: keyof FormState, value: string) {
    setForm((previous) => ({ ...previous, [field]: value }));
  }

  function applyPreset(preset: FormState) {
    setForm(preset);
    setResult(null);
    setError(null);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setResult(null);
    setIsSubmitting(true);
    try {
      const response = await fetch("/api/v1/mvp/card-notices/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      });
      const payload = (await response.json()) as VerificationResult | ApiError;
      if (!response.ok || "error" in payload) {
        setError("error" in payload ? payload.error : "REQUEST_FAILED");
        return;
      }
      setResult(payload);
    } catch {
      setError("API_UNAVAILABLE");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main>
      <header className="hero">
        <div>
          <p className="eyebrow">ORIGINPROOF · SYNTHETIC MVP</p>
          <h1>카드 알림 검증 데모</h1>
          <p className="subtitle">
            입력 후보를 바꾸고, 저장된 Signed Proof와 체인 신뢰 상태를 기준으로 실제 API 판정을
            확인합니다.
          </p>
        </div>
        <p className="synthetic-note">합성 Origin Mock Bank 데이터만 사용합니다.</p>
      </header>

      <section aria-labelledby="flow-title" className="flow-section">
        <div className="section-heading">
          <p className="eyebrow">VERIFICATION FLOW</p>
          <h2 id="flow-title">M1부터 M4까지의 하나의 검증 흐름</h2>
        </div>
        <ol className="flow-list">
          {flowSteps.map(([number, title, description]) => (
            <li key={number}>
              <span aria-hidden="true">{number}</span>
              <div>
                <strong>{title}</strong>
                <p>{description}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="workspace" aria-label="검증 데모">
        <section className="baseline-card" aria-labelledby="baseline-title">
          <div>
            <p className="eyebrow">SEEDED SYNTHETIC BASELINE</p>
            <h3 id="baseline-title">정상 프리셋의 신뢰 기준</h3>
          </div>
          <p>
            정상 프리셋은 아래 합성 은행 카드 거래를 그대로 입력한 편의값입니다. 이 정보는 로컬
            서버에 Signed Proof로 저장되고, 발행기관과 키는 로컬 체인에 등록됩니다.
          </p>
          <dl>
            <div><dt>발행기관</dt><dd>Origin Mock Bank (합성)</dd></div>
            <div><dt>카드</dt><dd>{baselineProof.card}</dd></div>
            <div><dt>기준 거래</dt><dd>{baselineProof.transaction}</dd></div>
            <div><dt>Proof ID</dt><dd>prf_demo_001</dd></div>
            <div><dt>발행기관 ID</dt><dd>{baselineProof.issuerId}</dd></div>
            <div><dt>등록 키 ID</dt><dd>{baselineProof.keyId}</dd></div>
            <div><dt>신뢰 체인</dt><dd>{baselineProof.chainId}</dd></div>
          </dl>
          <p className="baseline-note">
            실제 계좌번호·카드번호·은행 정보는 사용하지 않습니다. 이 프리셋이 “정상”인 이유는
            위 기준값을 로컬 Signed Proof와 일치하도록 시드했기 때문이며, 최종 정상 판정은
            브라우저가 아니라 Verify API가 합니다.
          </p>
        </section>

        <form className="candidate-form" onSubmit={submit}>
          <div className="form-heading">
            <div>
              <p className="eyebrow">UNTRUSTED CANDIDATE</p>
              <h2>검증할 카드 알림 입력</h2>
            </div>
            <div className="preset-buttons" aria-label="프리셋 선택">
              <button type="button" onClick={() => applyPreset(normalPreset)}>
                정상 프리셋
              </button>
              <button type="button" onClick={() => applyPreset(tamperedPreset)}>
                금액 변조 프리셋
              </button>
            </div>
          </div>

          <p className="form-help">
            프리셋을 고르거나 필드를 직접 수정한 뒤 검증을 실행하세요. 이 값은 신뢰 근거가 아니라
            비교 대상입니다.
          </p>

          <div className="fields">
            <label>
              Proof ID
              <input
                value={form.proofId}
                onChange={(event) => updateField("proofId", event.target.value)}
                pattern="prf_[A-Za-z0-9_-]+"
                required
              />
            </label>
            <label>
              발행 기관
              <input
                value={form.issuerName}
                onChange={(event) => updateField("issuerName", event.target.value)}
              />
            </label>
            <label>
              카드 끝 네 자리
              <input
                value={form.maskedCard}
                onChange={(event) => updateField("maskedCard", event.target.value)}
                inputMode="numeric"
                pattern="[0-9]{4}"
              />
            </label>
            <label>
              금액 (원)
              <input
                value={form.amountMinor}
                onChange={(event) => updateField("amountMinor", event.target.value)}
                inputMode="numeric"
                min="1"
                type="number"
              />
            </label>
            <label>
              통화
              <input
                value={form.currency}
                onChange={(event) => updateField("currency", event.target.value.toUpperCase())}
                maxLength={3}
                pattern="[A-Z]{3}"
              />
            </label>
            <label>
              가맹점
              <input
                value={form.merchant}
                onChange={(event) => updateField("merchant", event.target.value)}
              />
            </label>
            <label>
              승인 시각 (UTC)
              <input
                value={form.approvedAt}
                onChange={(event) => updateField("approvedAt", event.target.value)}
                type="datetime-local"
              />
            </label>
            <label>
              거래 ID
              <input
                value={form.transactionId}
                onChange={(event) => updateField("transactionId", event.target.value)}
              />
            </label>
            <label>
              추출 신뢰도
              <input
                value={form.confidence}
                onChange={(event) => updateField("confidence", event.target.value)}
                max="1"
                min="0"
                step="0.01"
                type="number"
              />
            </label>
            <label>
              Request ID
              <input
                value={form.requestId}
                onChange={(event) => updateField("requestId", event.target.value)}
                pattern="req_[A-Za-z0-9_-]+"
                required
              />
            </label>
          </div>

          <button className="submit-button" disabled={isSubmitting} type="submit">
            {isSubmitting ? "검증 중…" : "실제 Verify API로 검증"}
          </button>
        </form>

        <div className="verification-aside">
          <section className="result-panel" aria-labelledby="result-title" aria-live="polite">
            <div>
              <p className="eyebrow">DETERMINISTIC RESULT</p>
              <h2 id="result-title">최종 검증 결과</h2>
            </div>

            {!result && !error && (
              <div className="empty-result">
                <strong>아직 검증하지 않았습니다.</strong>
                <p>정상 또는 금액 변조 프리셋을 선택한 뒤 API 호출 결과를 확인하세요.</p>
              </div>
            )}

            {error && (
              <div className="error-result" role="alert">
                <strong>요청을 완료하지 못했습니다: {error}</strong>
                <p>Docker 데모 환경이 실행 중인지 확인한 뒤 다시 시도하세요.</p>
              </div>
            )}

            {result && (
              <div className="result-content">
                <div className={`status-card ${statusClass(result.verification_status)}`}>
                  <span>Verification Status</span>
                  <strong>{result.verification_status}</strong>
                  <span>Lifecycle Status</span>
                  <b>{result.lifecycle_status ?? "—"}</b>
                </div>

                <div className="result-detail">
                  <h3>Reason Codes</h3>
                  <p>{result.reason_codes?.length ? result.reason_codes.join(", ") : "없음"}</p>
                </div>

                <div className="checks">
                  <h3>검증 근거</h3>
                  <dl>
                    {Object.entries(result.checks).map(([name, value]) => (
                      <div key={name}>
                        <dt>{name}</dt>
                        <dd>{value}</dd>
                      </div>
                    ))}
                  </dl>
                </div>

                <p className="request-meta">
                  Session {result.session_id} · Request {result.request_id}
                </p>
              </div>
            )}
          </section>

          <section className="pipeline-panel" aria-labelledby="pipeline-title" aria-live="polite">
            <div>
              <p className="eyebrow">LIVE VERIFICATION TRACE</p>
              <h2 id="pipeline-title">실제 검증 파이프라인</h2>
              <p className="pipeline-intro">
                단계 상태는 Verify API가 반환한 실제 <code>checks</code>를 표시합니다. 서버가
                조기 종료한 경우 이후 단계는 결과에 나타나지 않습니다.
              </p>
            </div>
            <ol className="pipeline-list">
              <li>
                <span className="pipeline-number">1</span>
                <div>
                  <strong>후보 입력 전송 · M2 입력 경계</strong>
                  <p>{form.issuerName || "발행기관 없음"} · 카드 ••••{form.maskedCard || "—"} · {form.amountMinor || "—"} {form.currency || ""}</p>
                  <b className="trace-state">{isSubmitting ? "전송 중" : result ? "API에 전송됨" : "입력 대기"}</b>
                </div>
              </li>
              <li>
                <span className="pipeline-number">2</span>
                <div>
                  <strong>Signed Proof 조회 · M1 저장소</strong>
                  <p>Proof ID <code>{form.proofId || "—"}</code>로 서버 저장소에서 신뢰 원본을 조회합니다.</p>
                  <b className="trace-state">{checkValue(result, "proof_repository", isSubmitting)}</b>
                </div>
              </li>
              <li>
                <span className="pipeline-number">3</span>
                <div>
                  <strong>원본 무결성·유효기간 · M1</strong>
                  <p>저장된 Payload Hash를 재계산하고 Proof의 만료 여부를 확인합니다.</p>
                  <b className="trace-state">Hash {checkValue(result, "payload_hash", isSubmitting)} · Expiry {checkValue(result, "expiry", isSubmitting)}</b>
                </div>
              </li>
              <li>
                <span className="pipeline-number">4</span>
                <div>
                  <strong>후보 필드 대조 · M1</strong>
                  <p>금액, 가맹점, 카드 끝자리 등 사용자가 보낸 후보를 Signed Proof와 비교합니다.</p>
                  <b className="trace-state">{checkValue(result, "candidate_match", isSubmitting)}</b>
                </div>
              </li>
              <li>
                <span className="pipeline-number">5</span>
                <div>
                  <strong>Issuer·Key Registry 조회 · M4 → M3</strong>
                  <p>로컬 Anvil 체인에서 발행기관과 발행 키의 활성·유효 상태를 조회하고 서명을 검증합니다.</p>
                  <b className="trace-state">Issuer {checkValue(result, "issuer", isSubmitting)} · Key {checkValue(result, "issuer_key", isSubmitting)} · Signature {checkValue(result, "signature", isSubmitting)}</b>
                </div>
              </li>
              <li>
                <span className="pipeline-number">6</span>
                <div>
                  <strong>최종 결정 · M1</strong>
                  <p>모든 통과 근거와 라이프사이클을 조합해 결정합니다.</p>
                  <b className="trace-state">{isSubmitting ? "검증 중" : result ? `${result.verification_status} · ${result.lifecycle_status ?? "—"}` : "API 응답 대기"}</b>
                </div>
              </li>
            </ol>
          </section>
        </div>
      </section>
    </main>
  );
}
