# 카드 후보 확인·정정·비교 계약 인계안

- D: 여인준님 `@yijun0330`, 사용자 요청의 기존 `CARD_PAYMENT_NOTICE` 안전성 보강.
- 상태: **A/C 소비자 계약 초안. 소유자 합의·구현·실제 연결 대기.**
- 검토 기준: C `feat/w4-c-proof-lifecycle@8e57159efed4f3d435ab617b74952b2bbb970ec7`.
- D 시작 기준: `phase/W3@1f8ed632ea9c74091abaf2fe2ec32882038f731f`.
  두 SHA의 Analyzer와 v1 `verification.py`는 동일합니다. C 개인 branch는 병합하지 않았습니다.
- 기준 정책: [계획서 8장·15.9절](../development_plan.md), [ADR 0001](../adr/0001-finals-contracts.md),
  [현재 v1 계약](../api/mvp_verification.md). 새 본선 두 유형 추출은 이번 범위에 없습니다.

## 1. 현재 소비 흐름과 공백

| 현재 코드 | 실제 흐름·공백 | 담당 |
| --- | --- | --- |
| `services/analyzer/.../main.py`, `service.py` | `/v1/analyze/card-payment-notice`는 후보 10개 필드 반환. 헤더는 출처·확인 필요·비교 미수행을 알립니다. Python 직접 호출도 미확인 후보입니다. | D |
| `packages/python/originproof_core/models.py` | `VerificationRequest`는 후보·Proof ID만 받고 추출 출처, artifact 참조, 확인 기록이 없습니다. confidence는 출처나 확인 증거가 아닙니다. | C |
| `packages/python/originproof_core/verification.py` | null 필드는 건너뛰고 모두 null인 후보에도 `candidate_match=PASS`, 이후 `VERIFIED`를 반환할 수 있습니다. 후보 차이는 원인 구분 없이 `TAMPERED`로 반환합니다. | C |
| `apps/api/src/originproof_api/main.py` | v1 verify는 위 코어를 호출합니다. Analyzer를 호출하거나 사용자 확인을 강제하는 연결은 없습니다. | C |
| `apps/web/app/page.tsx`, `apps/web/next.config.ts` | 수동/합성 프리셋 후보를 Next rewrite를 통해 v1 API로 전달합니다. 실제 Analyzer 호출은 없습니다. UI가 채운 confidence·빈 missing_fields는 사용자 확인 기록이 아닙니다. | A |
| `scripts/ci/mvp_http_e2e.py`, `scripts/ci/proof_storage_smoke.py` | 합성 입력/저장된 payload를 사용한 검증 회귀입니다. AI 추출을 호출하거나 확인하지 않습니다. | 공통 QA/C |
| v1 생성 JSON Schema·TypeScript | 현재 모델과 일치하며 출처·확인 기록이 없습니다. D는 변경하지 않았습니다. | C |

C 검토 branch의 추가 본선 API도 카드 Analyzer에 직접 연결된 소비자는 아닙니다.
기존 v1 후보 불일치는 서명/Registry 검사보다 먼저 반환하므로 그 응답의 `ACTIVE`만으로
실제 서명·현재 체인 검사 성공을 주장할 수 없습니다. 실제 수행한 `checks`와 분리해야 합니다.
자동으로 AI 결과를 그대로 verify에 전달하는 신규 연결을 만들기 전에 아래 계약을 구현해야 합니다.

## 2. 현재 D 응답 계약

성공 JSON은 기존 `CardPaymentNoticeCandidate` 그대로입니다. 헤더 예시:

```http
X-OriginProof-Candidate-Source: ai
X-OriginProof-Confirmation-Required: true
X-OriginProof-Artifact-Comparison: not-performed
X-OriginProof-Missing-Comparison-Fields: transaction_id
```

`none`은 null인 payload 필드가 없다는 뜻입니다. 값의 진실성, grounding, 사용자 확인,
비교 수행을 뜻하지 않습니다. 헤더가 누락·유실되면 확인된 값으로 승격하지 마세요.
프록시가 응답 헤더를 보존하고, 직접 다른 origin에서 호출하도록 채택하면 명시적 CORS
노출 설정을 별도 검토해야 합니다. 현재 서비스는 그런 브라우저 연결을 제공하지 않습니다.
클라이언트가 보낸 동일 이름의 헤더를 서버 확인의 증거로 신뢰하지 마세요.

## 3. C가 구현·생성·리뷰할 계약 초안

기존 v1 endpoint·status/reason enum·서명 Golden을 보존하고, 새 확인 기반 비교 계약을
별도 버전/endpoint로 구현하는 안입니다. 아래 이름·응답 구조는 **현재 API가 아닙니다.**
Python 원본 모델과 생성기에서 JSON Schema·TypeScript·OpenAPI·예시를 함께 만들고,
호환성 설명·A/D 소비자 리뷰 및 필요한 B 서명 경계 리뷰를 받습니다. D가 생성물을 손으로
수정하거나 이 문서를 승인된 runtime 계약으로 취급하지 않습니다.

### 확인 요청 예시

```json
{
  "request_id": "req_synthetic_confirm_001",
  "extraction_review_id": "extr_synthetic_001",
  "proof_id": "prf_demo_001",
  "confirmed_fields": ["issuer_name", "masked_card", "amount_minor", "currency", "merchant", "approved_at", "transaction_id"],
  "corrections": {"amount_minor": 154000}
}
```

1. C의 서버가 생성·관리하는 `extraction_review_id`를 이용해 원래 후보, 대상 자료 참조,
   source, 설정/prompt 버전을 현재 사용자 세션에 연결합니다. 원문·전체 후보를 로그에 남기지
   않으며 실제 보관 방식·기간은 P1 채택 정책과 함께 정합니다. 새 DB 보관은 이번에 구현하지 않습니다.
2. 사용자는 A 화면에서 원문을 대조하고 필드별 확인/정정합니다. 수정된 값도 동일 모델로 재검증합니다.
   브라우저의 source/confirmed=true 또는 confidence만으로 서버 확인 상태를 만들지 않습니다.
3. 서버는 다른 사용자/자료의 review ID, 중복·알 수 없는 field, 유효하지 않은 정정, 오래된 review를
   거부합니다. 후보 또는 대상 자료가 바뀌면 기존 확인 기록을 무효화하고 다시 확인받습니다.
4. 사용자 확인은 ‘사용자가 이 값을 확인했다고 기록함’이며 원문과의 독립적인 기술 검증이 아닙니다.
   원문을 기계적으로 대조한 증거가 없다면 grounding 완료로 표시하지 않습니다.

### 비교 범위와 응답 예시

전체 **보호된 카드 payload 필드** 비교에 필요한 필드는 현재 `CardPaymentNotice.model_fields`의
`issuer_name`, `masked_card`, `amount_minor`, `currency`, `merchant`, `approved_at`, `transaction_id`입니다.
Proof ID는 조회 locator로 별도 검증합니다. masked card는 끝 네 자리 범위이며 전체 카드 번호,
이미지 레이아웃, 보호되지 않은 텍스트까지 일치한다는 표현은 사용하지 않습니다.

```json
{
  "proof_authenticity": "VERIFIED",
  "artifact_comparison": {
    "status": "INCONCLUSIVE",
    "scope": "CARD_PAYMENT_NOTICE_PROTECTED_FIELDS",
    "missing_fields": ["transaction_id"],
    "unconfirmed_fields": [],
    "mismatched_fields": [],
    "cause": "UNDETERMINED"
  }
}
```

위 `proof_authenticity`는 실제 서명·해시·신뢰 검사에 성공한 경우에만 반환하는 예시입니다.
서명 확인과 현재 lifecycle·체인 상태는 기존 정책대로 분리하며, 미수행 검사를 성공으로 채우지 않습니다.

| 입력·검사 상황 | 제안된 자료 비교 결과 | 금지된 해석 |
| --- | --- | --- |
| ID만 조회 | `NOT_RUN` | 자료 내용까지 일치 |
| 미확인 AI/Mock 후보 | `INCONCLUSIVE`, 확인 필요 | confidence로 확인 생략 |
| 필수 값 누락, 관찰된 차이 없음 | `INCONCLUSIVE`, 누락 필드 표시 | 전체 보호 필드 일치 |
| 확인된 값 일부 차이 + 다른 필드 누락 | `MISMATCH`, 실제 비교·누락 범위를 함께 표시 | 누락 때문에 차이를 숨기거나 성공 처리 |
| 확인된 필수 값 모두 존재하고 실제 비교 모두 일치 | `MATCH`, 보호 필드·입력값 범위 명시 | 자료 전체 또는 실제 거래 사실 보증 |
| AI 유래 후보 차이 | 원인 `UNDETERMINED`, 원문·추출 재검토 | 자료 변조/위조 원인 확정 |
| 서명/등록 검증 실패 | 별도 Proof 검사 실패 | AI 출력으로 실패 덮기 |

새 필드·enum은 계약 초안이며 기존 v1 응답에 조용히 섞지 않습니다. v1에서 계속 사용하는
`VERIFIED`/`TAMPERED`는 기존 회귀를 보존하되 소비 화면이 비교 범위와 원인의 한계를 설명해야 합니다.

## 4. A의 화면·표현 인계

- 추출 후 원문과 후보를 나란히 보여주고 필드별 확인·정정 뒤 비교합니다. 미확인/누락 값은
  비워두고, confidence가 높아도 확인을 생략하지 않습니다. UI 숨김만으로 서버 검사를 대신하지 않습니다.
- AI 유래 차이: **‘추출한 값이 등록된 내용과 다릅니다. 원문과 추출값을 다시 확인해 주세요.’**
- 필수 값 누락: **‘비교할 항목이 부족합니다. 누락된 값을 확인해 주세요.’**
- ID 조회: **‘발행 기록을 조회했습니다. 받은 자료의 내용은 아직 비교하지 않았습니다.’**
- 확인된 입력 비교 성공: **‘확인한 보호 필드가 등록된 내용과 일치합니다.’**
- 원문 변조/진위 원인 확정, 법적 효력, 실제 거래 존재를 AI 추출만으로 표시하지 않습니다.

## 5. 연결 후 필요한 검사

현재 [D 검사](../qa/analyzer-extraction-safety.md)는 Mock/SDK MockTransport, core의 in-memory
ports를 사용합니다. 아래 항목은 A/C 구현 뒤 실제 연결로 추가해야 합니다.

1. 미확인 후보의 직접 API 비교 요청을 서버가 보류/거부하는지, 확인 UI 우회·review ID 교체·값 변경 거부.
2. 필수 값 각각 누락, 모두 null, ID-only, confidence=1.0의 잘못된 값, 부분 차이+누락의 범위·우선순위.
3. 정상/정정/재확인 흐름과 AI 유래 차이 표현을 실제 브라우저·서버 응답으로 확인.
4. v1 정상 `VERIFIED + ACTIVE`, 금액 변조 `TAMPERED + AMOUNT_MISMATCH`, 서명 Golden 유지.
5. 채택된 파일 보관/삭제 및 악성 입력 보호. 유료 모델 평가는 별도 승인 범위가 있을 때만 실행.

이 인계안은 소유자에게 별도 메시지로 발송하지 않았으며 리뷰 승인도 아직 없습니다.
