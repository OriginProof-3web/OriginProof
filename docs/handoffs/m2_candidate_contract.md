# Handoff: M1 to M2 — Card payment notice candidate contract

> **MVP 과거 기록 — 현재 작업 지시로 사용하지 마세요.** 당시 역할·브랜치·미완료 상태·설정값을 보존한 문서입니다. 현재 개발은 [시작 안내](../../START_HERE.md)와 [개발 계획서](../development_plan.md)를 따르며, 아래의 실행/병합 지시는 자동으로 적용하지 않습니다.

Requesting role: M1 Backend

Target owner: M2 AI

Exact interface: `CardPaymentNoticeCandidate` in
`packages/schemas/generated/json/card-payment-notice-candidate.schema.json`.

M2 returns extracted candidate fields, a numeric confidence from `0` to `1`, a possible `proof_id`,
and `missing_fields`. It must not return a verification status, authenticity score, or any final
decision.

M1 compares only fields actually present in the candidate with the server-side signed proof. The
MVP’s altered-amount fixture must preserve every other field and return `TAMPERED` with
`AMOUNT_MISMATCH` from the backend verifier.
