# M2 실행 문서 카드 알림 후보 추출

## 시작 기준

이 작업은 최신 `origin/mvp/integration`에서 시작합니다. M1 Backend PR은
`c2e4be5`에 병합됐으며, 이후의 통합 문서도 함께 받아야 합니다. 다른 브랜치의 예전 Schema나
임시 API를 기준으로 구현하지 않습니다.

```bash
git fetch origin
git switch -c mvp/ai origin/mvp/integration
make bootstrap-check
```

M2의 소유 경로는 `services/analyzer`와 `fixtures/mvp`입니다. 공통 Pydantic 모델,
생성된 Schema, API 검증 규칙, Solidity, 체인 어댑터는 수정하지 않습니다. 후보 필드가 부족하거나
타입이 맞지 않으면 M1에 handoff를 요청합니다.

## 목표

합성 Origin Mock Bank 카드 알림의 텍스트 또는 이미지를 `CardPaymentNoticeCandidate`로
구조화합니다. AI 또는 규칙 기반 추출기는 진위, 사기 가능성, 위험도, `VERIFIED`, `TAMPERED`를
판단하거나 반환해서는 안 됩니다. 최종 판정은 M1 검증 서비스만 수행합니다.

현재 Analyzer는 `/health/live`만 제공하는 골격입니다. M2는 이 서비스 내부에 추출 포트와
어댑터를 추가하고, M1이 이후 연결할 수 있는 명확한 입력·출력 계약을 PR 설명과 handoff에 남깁니다.

## 고정 출력 계약

권위 있는 정의는 `packages/python/originproof_core/models.py`의
`CardPaymentNoticeCandidate`이며 생성 Schema는
`packages/schemas/generated/json/card-payment-notice-candidate.schema.json`입니다.

| 필드 | 규칙 |
| --- | --- |
| `issuer_name` | 추출하지 못하면 `null` |
| `masked_card` | 마지막 네 자리 숫자만, 예: `1234`; 없으면 `null` |
| `amount_minor` | 정수 최소 화폐 단위, 예: KRW 154,000원은 `154000`; 없으면 `null` |
| `currency` | 세 글자 대문자 ISO 코드, 예: `KRW`; 없으면 `null` |
| `merchant` | 추출하지 못하면 `null` |
| `approved_at` | timezone을 포함한 ISO 8601 datetime 또는 `null` |
| `transaction_id` | 추출하지 못하면 `null` |
| `proof_id` | 예: `prf_demo_001`; 추출하지 못하면 `null` |
| `confidence` | 항상 `0` 이상 `1` 이하의 숫자 |
| `missing_fields` | 알 수 없는 필드명을 나열한 배열 |

출력에는 `verification_status`, `lifecycle_status`, `reason_codes`, authenticity score 또는
자유 형식의 진위 판단 문장을 포함하지 않습니다. 모델이 알 수 없는 필드는 `null`로 두고
`missing_fields`에 기록합니다. 유효하지 않은 값은 억지로 보정하지 않고 검증 실패로 처리합니다.

## 구현 범위

1. `LLMProvider` 추상화와 `MockLLMProvider`를 구현합니다. 기본 테스트는 Mock만 사용해야 합니다.
2. `OpenAILLMProvider`는 설정값을 통해 OpenAI Responses API와 Pydantic Structured Outputs를
   사용합니다. 모델 기본값은 `OPENAI_MODEL` 또는 `gpt-5.6-luna`입니다.
3. provider, model, reasoning effort, timeout, retry는 설정에서 읽습니다. API key, 원문 이미지,
   원문 메시지, 제한 없는 provider 응답을 로그에 남기지 않습니다.
4. text와 image 입력에서 같은 정보가 주어지면 같은 정규화 후보를 반환하도록 구현합니다.
5. refusal, timeout, rate limit, incomplete output, schema mismatch, 낮은 confidence를 명시적으로
   안전한 도메인 오류 또는 후보 결과로 처리합니다. 오류 원문을 외부에 노출하지 않습니다.
6. M1 API의 `POST /v1/mvp/card-notices/verify`를 바꾸지 않습니다. M2는 후보 추출까지만 제공하고,
   API 연결은 M1의 후속 통합 단계에서 합니다.

## 필수 합성 Fixture와 테스트

기존 fixture는 다음 두 개입니다.

- `fixtures/mvp/card_notice_valid.json`: `amount_minor=154000`
- `fixtures/mvp/card_notice_amount_tampered.json`: `amount_minor=1540000`

두 fixture는 금액 외 모든 보호 필드가 동일해야 합니다. fixture는 `source: synthetic`을 유지하고
실제 은행명, 실제 카드 정보, 실제 개인 정보, API key, 원문 이미지 파일을 포함하지 않습니다.

최소 테스트는 아래를 포함합니다.

1. 정상 텍스트가 예상 Candidate를 반환합니다.
2. 변조 금액 텍스트가 `1540000`을 추출하며, M2 자체는 `TAMPERED`를 반환하지 않습니다.
3. 필드 누락 입력이 `null`과 올바른 `missing_fields`를 반환합니다.
4. 잘못된 형식 입력과 Structured Output schema mismatch가 안전하게 실패합니다.
5. Mock provider의 timeout, refusal, incomplete 결과가 재현 가능하게 처리됩니다.
6. 선택한 image fixture가 있으면 같은 내용의 text fixture와 동일한 Candidate를 반환합니다.

실행 명령은 최소 `make test-analyzer`, `make mvp-test`, `make lint`, `make typecheck`입니다.
실제 OpenAI 호출은 opt-in이며 PR 필수 조건이 아닙니다.

## M1 handoff와 PR

구현 전 또는 완료 시 M1에 아래 정보를 남깁니다.

- 추출 진입점과 요청·응답 모델
- Prompt 버전과 provider 설정 키 이름
- 정상·변조·누락 입력의 예상 Candidate
- 실패 모드별 외부 안전 오류 형태
- M1 API 연결에 필요한 endpoint 또는 import 경로
- 실제 실행한 테스트 결과

PR은 `mvp/ai`에서 `mvp/integration`으로 생성합니다. M1은 Candidate Schema 변경 요청,
AI가 최종 진위 판단을 하지 않는지, fixture가 합성 데이터만 사용하는지 확인한 뒤 병합합니다.
