# OriginProof M2 Analyzer

M2는 합성 카드 알림을 `originproof_core.CardPaymentNoticeCandidate`로 구조화한다.
진위 판정, Signed Proof 조회, 서명 검증, Registry 접근은 하지 않는다.
개발 시작 기준은 `origin/mvp/integration@3bbaba025acd9d692ab484232f778a12a7579702`와
`docs/handoffs/m2_execution_brief.md`였다. 현재 병합 기준은
`origin/mvp/integration@f029e76b310de30cb27731be08c18a4360dc281c`이다.
[통합 handoff](HANDOFF.md)에 검증 결과와 남은 조건을 기록한다.

## 빠른 실행 (저장소 루트에서)

```bash
uv sync --all-packages --all-groups --locked
LLM_PROVIDER=mock uv run --package originproof-analyzer uvicorn originproof_analyzer.main:app --host 127.0.0.1 --port 8001
```

다른 터미널에서 다음 합성 입력을 보낸다.

```bash
curl --fail-with-body http://127.0.0.1:8001/v1/analyze/card-payment-notice \
  -H 'Content-Type: application/json' \
  --data-raw '{"text":"[Origin Mock Bank]\n카드 승인\n카드 ****1234\n154,000원\nORIGIN CAFE\n2026-09-03 12:14\nProof ID: prf_demo_001"}'
```

예상 응답:

```json
{
  "issuer_name": "Origin Mock Bank",
  "masked_card": "1234",
  "amount_minor": 154000,
  "currency": "KRW",
  "merchant": "ORIGIN CAFE",
  "approved_at": "2026-09-03T03:14:00Z",
  "transaction_id": null,
  "proof_id": "prf_demo_001",
  "confidence": 0.8575,
  "missing_fields": ["transaction_id"]
}
```

`154,000원`을 `1,540,000원`으로 바꾸면 금액은 `1540000`이다.
입력에 `Transaction ID: txn_demo_001`도 있으면 해당 값이 추출되며 Mock confidence는 0.98이다.
Mock confidence는 추출된 필드 비율 기반 테스트 값이며 모델 성능이나 보정된 확률이 아니다.

## 입력과 출력

- HTTP: `POST /v1/analyze/card-payment-notice`
- 요청: `originproof_analyzer.inputs.SemanticInput`
- 반환: 공통 `originproof_core.CardPaymentNoticeCandidate` **그 자체**, 정확히 10개 필드
- health: `GET /health/live` → `{"status":"live"}` (Bootstrap 계약 유지)
- 기능 확인: `GET /v1/capabilities`
- Swagger: `/docs`

Text는 1~10,000자이며 공백만 있는 입력은 거부한다.
이미지는 다음 JSON으로 전달한다. Text와 이미지는 동시에 보내지 않는다.

```json
{"image_base64":"<base64 bytes>","image_media_type":"image/png"}
```

PNG/JPEG/WebP, 디코딩 후 5 MiB 이하, 단일 프레임, 12 megapixels 이하만 허용한다.
파일 signature, 선언 MIME, 실제 디코딩 형식과 손상 여부를 검사한다.
원본 입력이나 이미지를 저장하지 않는다.

기본 Mock는 문서화된 KRW 알림 템플릿의 Text 파서다. 임의 이미지의 OCR은 하지 않으며
기본 HTTP 서비스는 이미지에 `UNSUPPORTED_INPUT`을 반환한다.
테스트/평가에서는 합성 이미지를 메모리에서 생성하고,
`MockLLMProvider(image_replays={sha256: transcript})`를 **코드에서 주입**하여
동일 bytes를 재현한다. HTTP 사용자가 replay/예상 필드/오류 코드를 주입할 수 없다.
이미지 replay는 실제 Vision 모델 평가가 아니다.

OpenAI provider는 검증된 이미지 bytes를 Responses API의 이미지 입력으로 전달한다.
실제 API 평가를 하려면 사용자 환경에 `OPENAI_API_KEY`를 설정하고
`LLM_PROVIDER=openai`를 명시해야 한다. 기본/CI 테스트나 평가 명령은 유료 API를 호출하지 않는다.

## 설정과 Prompt

설정은 프로세스 환경변수에서 읽는다. Docker Compose의 기존 `env_file`은 그대로 사용한다.
로컬 `.env`는 자동으로 읽지 않는다. 필요하면 uvicorn에 `--env-file .env`를 명시한다.

| 환경변수 | 기본값 |
| --- | --- |
| `LLM_PROVIDER` | `mock` |
| `OPENAI_MODEL` | `gpt-6-luna` |
| `OPENAI_REASONING_EFFORT` | `low` |
| `OPENAI_API_KEY` | 없음, OpenAI 호출에만 필요 |
| `LLM_TIMEOUT_SECONDS` | `20` (각 SDK 요청의 timeout) |
| `LLM_MAX_RETRIES` | `2` (0~2, 전체 최대 3회 시도) |
| `ANALYZER_MIN_CONFIDENCE` | `0.70` |

SDK만 재시도를 수행한다. 재시도/백오프 때문에 전체 경과 시간은 timeout보다 길 수 있다.
OpenAI 실패나 키 누락 시 Mock로 자동 대체하지 않는다.

Prompt 버전은 `card_payment_notice_v3`이며 wheel에 포함한다.
`originproof_analyzer.service` logger는 INFO 수준의 `analyzer.extraction` 이벤트에
provider/model/prompt_version/input_kind/duration_ms/error_code만 전달한다.
배포 로깅에서 이 logger의 INFO 레벨과 `record.analyzer` 필드를 수집하도록 설정한다.
후보 값, 전체 입력, image hash, API Key, provider 원문은 기록하지 않는다.

[OpenAI Structured Outputs 공식 문서](https://developers.openai.com/api/docs/guides/structured-outputs)의
Responses + Pydantic 방식을 사용한다. SDK 파싱 전에 refusal/incomplete를 검사하고
원래 JSON을 strict 검증해 문자열/boolean 금액의 암묵 변환을 차단한다.

## 오류 계약

오류는 `{"error":{"code":"TIMEOUT","message":"Extraction request timed out."}}` 형태다.
message는 고정된 안전한 문자열이다.

| HTTP | code |
| --- | --- |
| 422 | MALFORMED_INPUT, UNSUPPORTED_INPUT, REFUSAL, LOW_CONFIDENCE |
| 502 | SCHEMA_MISMATCH, INCOMPLETE_OUTPUT |
| 503 | RATE_LIMIT, PROVIDER_UNAVAILABLE |
| 504 | TIMEOUT |

`missing_fields`는 null 필드와 정확히 일치해야 한다.
잘못된 값/중복 충돌/날짜/금액을 억지로 고치지 않는다.
시간대 없는 합성 한국 알림의 승인시각만 문서화된 KST 규칙을 적용한다.
모든 응답에서 승인시각은 UTC로 정규화한다.

## 재현 가능한 테스트와 평가

```bash
make test-analyzer
make mvp-test
make lint
make typecheck
make test
uv run --package originproof-analyzer python -m originproof_analyzer.evaluation --output build/m2-evaluation.json
```

평가는 합성 Text 8건과 메모리 이미지 replay 2건이다. 예상 후보는 별도 Fixture 값과 비교하며,
기존 두 Golden JSON은 변경하지 않는다. null 포함 전체 필드 비교와 실제 값이 있는 필드 비교의
분모를 별도로 기록한다. `live_model_evaluated=false`, `confidence_is_calibrated=false`다.

SDK 테스트는 실제 OpenAI 클라이언트와 `httpx.MockTransport`를 사용한다.
Analyzer 테스트에서는 socket 연결을 차단하여 외부 네트워크/개인 API Key에 의존하지 않는다.
`make mvp-test`에는 다른 역할의 Foundry 테스트가 포함되므로 Foundry 설치도 필요하다.
