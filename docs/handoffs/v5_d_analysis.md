# D 비동기 분석기·평가 초안 인계

> 현재 GitHub 공유 상태: [D PR #70~#76 현재 리뷰 목록](v5_d_review_index.md). 아래 실행 기록의 push/PR 미수행 표시는 당시 상태로 보존합니다.

- 작업: V5-W5-D, V5-W1-D의 평가 준비 후속. 사용자 입력은 **미정**입니다. 2026-10-16 최종 후속 지시로 **Jev 도입을 취소하고 OpenAI 모델만 사용**합니다. 최종 모델은 2026-10-18 사용자가 **OpenAI GPT-6 Luna (`gpt-6-luna`)**로 확정했습니다. 유료 평가/전송 범위·예산은 미정입니다.
- 현재 소비 기준: 계획서 5.1·공유 계약 v5-shared-0.2. 2026-10-21에는 C가 포함된 같은 HEAD에서 재검사했습니다. [현재 근거·계약 검토](../qa/v5-d-weekly-status-20261021.md). 과거 고정0.1/0.2 후보 검사는 아래 날짜별 기록으로 보존합니다.
- 브랜치: `codex/v5-w5-d-analysis`, 구현/검증 SHA `98d2c5400aa0e3e398dbb8df720b6d1445fae6db`.
- 상태: 독립 구현·합성/mock/SDK 검사 완료. 실제 모델 평가·입력 활성화·A/B/C 실제 연결·리뷰는 후속입니다.

## 분석기와 C 연결

[`PhishingAnalyzer`](../../services/analyzer/src/originproof_analyzer/phishing.py)는 async `processor(text) -> AnalysisReport` 콜백입니다. 기존 LLMProvider/OpenAILLMProvider/MockLLMProvider와 설정·안전한 오류 처리를 재사용하며 별도 공통 모델 사본을 만들지 않았습니다.

처리는 문맥/요구 행동 규칙 → 비동기 Responses 구조화 분석 → 실제 원문 인용 대조 → 공통 보고서 순서입니다. 규칙은 요청 행동과 비밀정보/원격제어/긴급 송금/변경 계좌/공식 확인 방해의 조합을 찾고 부정문·인용된 예방 예시를 별도 검사합니다. 규칙은 제한된 휴리스틱이며 실제 모델 분석을 대체하지 않습니다.

quote는 공백·분해 Unicode를 보존하며 위치는 코드 포인트 `[start,end)`입니다. 없는 인용·틀린 위치·모호한 반복(겹친 반복 포함)·TEXT의 page/time·provider의 발행 판정/규칙 출처 위조를 거부합니다. HIGH/CAUTION은 실제 인용 없이 반환하지 않습니다. 제한 개수에서 잘릴 때도 선택한 위험 수준의 근거와 mock/불일치 안내를 유지합니다.

기본 mock은 LLM 성공을 만들지 않습니다. 검증된 규칙이 있으면 RULE 근거만, 없으면 UNDETERMINED를 반환하고 `LLM_ANALYSIS_UNAVAILABLE:<고정 code>`로 설명합니다. 정상 mock replay에도 모델 성능이 아니라는 제한을 남깁니다. 원시 예외·입력·provider 응답은 로그에 넣지 않습니다. LLM이 제공한 limitations는 `LLM: ` 접두어로 서비스 상태 코드와 구분합니다.

OpenAI 구현은 [공식 Structured Outputs 문서](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses)와 설치된 SDK 2.54.0을 확인했습니다. 내부 `_AnalysisOutput`은 공통 AnalysisReport를 상속하되 verification=null로 좁힌 provider 전용 형식입니다. 기존 model/reasoning/timeout/retry 설정을 재사용하고 store=false·도구 없음으로 요청합니다. async HTTP는 취소를 전파하며 소유한 client는 호출 종료/취소 시 닫습니다. 기존 카드 동기 호출은 같은 오류 변환기를 재사용합니다.

사용 예시는 C 후보의 명시적 dependency injection입니다. 이 코드만으로 입력 지원을 활성화하지 않습니다.

```python
from originproof_analyzer.phishing import PhishingAnalyzer
from originproof_analyzer.providers import MockLLMProvider
processor = PhishingAnalyzer(MockLLMProvider())  # 환경 설정과 무관하게 유료 요청 없음
# C 후보: create_app(analysis_processor=processor, ...)
# wallet_text_input_enabled는 기본 false를 유지합니다.
```

C가 발행 검증 세션을 별도로 집계합니다. D는 verification을 생성하지 않습니다. D의 인용 검사가 DG12를 차단해도 C `ground_report`의 겹친 반복 결함 자체를 고친 것은 아닙니다. 다른 분석기 소비 경로의 C 수정·재검사가 필요합니다.

## 합성 원본과 평가

[`phishing_sources_v1.json`](../../fixtures/synthetic/phishing_sources_v1.json)은 네 수준별 15개, 총 60개 합성 텍스트 원본 초안입니다. 제안 분할은 개발 24/보류 36(수준별 6/9)이며 같은 source_group의 변형이 분할을 넘지 않도록 검사합니다. 동일 원문이 양쪽에 들어가는 것도 거부합니다. 기존 30개 근거 replay와 카드 추출 10개 평가를 위험 분류 60개와 합산하지 않습니다.

**DRAFT_REVIEW_REQUIRED / labels_human_reviewed=false / input_selection=UNDECIDED**입니다. 최종 지원 입력 결정과 A 또는 C의 라벨/분할 사전 리뷰 전에는 확정 평가셋으로 동결하지 않습니다. 현재 합성 텍스트 원형은 OCR/STT/PDF 지원을 뜻하지 않습니다.

```sh
PYTHONPATH=apps/api/src:packages/python:services/analyzer/src \
  UV_PROJECT_ENVIRONMENT=.uv-venv uv run --locked --offline \
  python -m originproof_analyzer.phishing_evaluation \
  --manifest fixtures/synthetic/phishing_sources_v1.json \
  --output build/v5-d-development-evaluation.json
```

CLI는 환경의 provider 설정과 무관하게 명시적 mock/rules를 사용합니다. 기본 분할은 development이며 holdout은 명시적으로 선택해야 합니다. 이번에 보류 36개 모델 예측은 실행하지 않았습니다. 라벨·기대 인용은 processor에 전달하지 않고 원문만 전달합니다. 호출/Schema/근거 실패는 ERROR로 계산하며 UNDETERMINED의 정답으로 합산하지 않습니다.

[실제 개발 분할 결과](../qa/v5-d-development-evaluation.json): 24개, macro-F1 **0.451863**, HIGH recall **1.0(6개)**, 판단 보류 **17개**, 예외 실패 0개. 모델 미실행/거부 표시는 24개 모두이며 LLM 유료 호출은 0입니다. 표시한 인용 8개는 검증기를 통과한 출력의 안전성 불변식이며 모델 후보 인용의 정확도 점수가 아닙니다. 제안된 기대 근거 12개 중 위치 포함 충족은 7개(location recall 7/12)입니다. 규칙 기준선의 한계이며 최종 모델 목표 달성이 아닙니다.

위험 전용 원본은 보호 필드 추출 정확도를 측정하지 않습니다. 해당 분모는 null/NOT_EVALUATED이며 기존 카드 후보 평가와 별도로 후속 선정 입력/검사 원본이 필요합니다. 지연은 로컬 합성 처리 구간만 기록했고 실제 LLM p95 목표와 구분합니다.

## 최초 검사·한계 (2026-10-16)

- 전체 Python **292 PASS**, 기존 TestClient deprecation warning 1. 새 규칙/원문 대조/async callback/SDK 오류/취소·평가 분할·분모와 기존 v1 회귀 포함입니다.
- 최초 새 SDK 검사 1 FAIL은 비동기 raw response의 parse를 await한 호출 오류였습니다. 설치 SDK의 raw.parse는 동기 메서드이므로 수정 후 새 SDK·기존 SDK 검사와 전체 회귀가 통과했습니다.
- Ruff·diff 검사 PASS, 의존성·공통 모델·API·Schema 원본 변경 없음.
- 실제 LLM·입력 변환·보류 분할 평가·브라우저/신규 Registry 연결·성능 목표·사람 리뷰는 미실행입니다. 보존 브랜치와 기존 사용자 작업을 유지하고 push/PR은 하지 않았습니다.

## 후속 독립 QA

[`codex/v5-d-independent-qa`](../qa/v5-d-independent-qa.md)에서 같은 분석 소스를 C #62 고정 후보에 주입해 ASGI/SQLite/합성 Registry 12개를 통과했습니다. C 후보 환경의 Analyzer 251개도 통과했습니다. 실제 신규 A/B/C 통합 완료와 구분합니다. 과거 고정 제품의 PostgreSQL/Anvil mixed 18그룹이 이번에 통과했지만 G07은 원인·수정 인계 전까지 미해결을 유지합니다. 상세 SHA/명령/실행 경계는 연결된 QA 보고서에 있습니다.

## 2026-10-16 최종 사용자 선택: OpenAI만 사용

사용자가 같은 날 검토했던 `typesafe/jev` 도입을 취소하고 OpenAI 모델만 사용하겠다고 명시했습니다. 앞선 Jev 선행·OpenAI 후속 제안을 대체합니다. Jev 호출 경로·질문·분기 임계값은 후속 결정 목록에서 제외합니다. 기존 OpenAI Responses/Structured Outputs 연결과 규칙·원문 근거 대조를 재사용합니다.

2026-10-16 당시 공급자 선택만 OpenAI로 정해졌고 세부 모델명·유료 범위·예산은 미정이었습니다. 그때 코드 기본값을 최종 선택으로 간주하지 않았습니다. 모델 미정 상태는 아래 2026-10-18 사용자 결정으로 대체하며 입력/유료 범위/라벨·분할 리뷰는 후속입니다.

Jev SDK·의존성·호출 코드가 추가되지 않았으므로 제거할 실행 코드는 없습니다. 이번에는 D 인계 문서만 정정했고 기존 mock 기본값·입력 비활성화·유료 호출 제한·공통 계약·과거 평가 결과는 유지했습니다. OpenAI Decisions API는 계속 현재 범위 밖입니다. 문서 diff와 로컬 링크를 검사했으며 기능 검사를 재실행한 것으로 보고하지 않습니다. 원격 push·PR 생성·병합은 수행하지 않았습니다.


## 2026-10-18 리뷰 수정

- 수정 실행 소스 `77e4f44198a16c12502283dade4db8b4289fb159`, 준비 브랜치 `codex/v5-w5-d-analysis` / PR #75. 최신 integration `54705588d660aceea71ff1cb03eefb5aefe37aa4`(#80)을 D 선행 단계의 merge로 반영했습니다.
- 평가 버전 `v5-d-evaluation-0.2`: 검증된 출력만으로 항상 1.0이 되던 기존 `evidence.grounding_ratio`를 제거했습니다. `validated_quote_count`는 출력 안전성에 한정하고, 원시 후보를 관측하지 못하는 `candidate_grounding`의 분모·일치 수·비율은 null/NOT_EVALUATED입니다. 누락·위치 정확도와 함께 실제 후보 품질 평가가 남아 있으며 필수 평가를 면제하거나 완료 처리하지 않습니다.
- 거부된 보고서 수는 별도로 집계합니다. 환각 후보를 격리한 뒤 규칙 근거만 살아남는 경우도 검사해 후보 품질이 100%로 표시되지 않게 했습니다. 실패 사례도 기대 위치 분모에서 빠지지 않습니다.
- 개발 24개만 재실행했으며 위험 예측·macro-F1·보류·실패 수·원본/라벨/분할은 그대로입니다. 이전 결과는 Git 이력과 최초 실행 SHA에 보존합니다. 보류36개/유료 OpenAI는 미실행입니다.
- SDK의 실제 `httpx.ReadTimeout → APITimeoutError → TIMEOUT` 변환을 MockTransport로 검사했습니다. 총 180초 기한은 테스트에서만 즉시 만료시켜 provider 취소와 TIMEOUT 처리를 검증합니다. 예기치 않은 예외는 원문/메시지 없이 타입명만 메타데이터에 기록합니다. [공식 오류 안내](https://developers.openai.com/api/docs/guides/error-codes)와 설치 SDK 2.54.0을 대조했습니다.
- 새 코드에서 `make test`: **329 PASS / 1 SKIP**. indexer의 실제 체인 opt-in 검사는 미실행이며 기존 warning 1개가 있습니다. 관련 분석기 검사 84 PASS, `make generate` 후 전체 생성물 diff 없음, 전체 Ruff 통과입니다.
- [단계별 전용 CI·재현·잔여 결함](../qa/v5-d-review-fixes.md). C 제품은 수정하지 않았고 DG12·G07은 미해결입니다. PR 공유·재리뷰와 단계 완료를 구분합니다.

테스트 공용 응답 builder는 conftest fixture로 재사용하며 test 모듈 직접 import가 없습니다. 분석기 전체는 importlib 모드에서도 256 PASS였습니다. Python compileall·웹 tsc 타입 검사도 통과했습니다.


## 2026-10-18 사용자 최종 모델 결정 — GPT-6 Luna

사용자가 “AI모델 openAI 6.0 luna로 사용할게”라고 직접 선택했습니다. 최종 분석 모델은 **OpenAI GPT-6 Luna**, API 모델 ID는 **`gpt-6-luna`**입니다. [공식 OpenAI 모델 문서](https://developers.openai.com/api/docs/models/gpt-6-luna)로 ID를 확인했습니다. 이 결정은 기존 모델 미정 기록을 대체합니다.

`AnalyzerSettings.openai_model`과 루트 `.env.example`의 `OPENAI_MODEL`이 이미 `gpt-6-luna`여서 실행 코드·기본값 변경은 없습니다. 기존 Responses/Structured Outputs 경로를 사용합니다. 현재 `OPENAI_REASONING_EFFORT=low`는 기존 설정이며 이번에 새로 평가·최적화한 값은 아닙니다.

Q05의 모델 선택은 완료됐고 유료 평가/전송 범위·예산·최종 평가 설정은 남아 있습니다. Q01 입력 종류/우선순위와 A/C 라벨·분할 리뷰도 후속입니다. provider 기본 mock·입력 비활성·유료 opt-in 경계는 유지했습니다. 이번 문서 결정 반영에서 모델 호출·유료 평가·holdout 예측은 실행하지 않았고 실제 품질/지연/비용을 검증한 것으로 기록하지 않습니다. 기존 DG12/G07 상태도 바꾸지 않습니다.
