# D 비동기 분석기·평가 초안 인계

- 작업: V5-W5-D, V5-W1-D의 평가 준비 후속. 사용자 입력은 **미정**입니다. 2026-10-16 후속 지시로 **TypeSafe Jev를 OpenAI 앞에 사용**하는 방향이 선택됐습니다. OpenAI 후속 모델·호출 경로·분기 조건은 미정입니다.
- 기준: 계획서 5.1·공유 계약 v5-shared-0.1. C 후보의 v5-shared-0.2는 별도 소비 대상으로 검토합니다.
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

**DRAFT_REVIEW_REQUIRED / labels_human_reviewed=false / input_selection=UNDECIDED**입니다. 최종 지원 입력·모델 결정과 A 또는 C의 라벨/분할 사전 리뷰 전에는 확정 평가셋으로 동결하지 않습니다. 현재 합성 텍스트 원형은 OCR/STT/PDF 지원을 뜻하지 않습니다.

```sh
PYTHONPATH=apps/api/src:packages/python:services/analyzer/src \
  UV_PROJECT_ENVIRONMENT=.uv-venv uv run --locked --offline \
  python -m originproof_analyzer.phishing_evaluation \
  --manifest fixtures/synthetic/phishing_sources_v1.json \
  --output build/v5-d-development-evaluation.json
```

CLI는 환경의 provider 설정과 무관하게 명시적 mock/rules를 사용합니다. 기본 분할은 development이며 holdout은 명시적으로 선택해야 합니다. 이번에 보류 36개 모델 예측은 실행하지 않았습니다. 라벨·기대 인용은 processor에 전달하지 않고 원문만 전달합니다. 호출/Schema/근거 실패는 ERROR로 계산하며 UNDETERMINED의 정답으로 합산하지 않습니다.

[실제 개발 분할 결과](../qa/v5-d-development-evaluation.json): 24개, macro-F1 **0.451863**, HIGH recall **1.0(6개)**, 판단 보류 **17개**, 예외 실패 0개. 모델 미실행/거부 표시는 24개 모두이며 LLM 유료 호출은 0입니다. 표시한 인용 8개는 전부 원문에 일치했지만, 제안된 기대 근거 12개 중 위치 포함 충족은 7개입니다. 규칙 기준선의 한계이며 최종 모델 목표 달성이 아닙니다.

위험 전용 원본은 보호 필드 추출 정확도를 측정하지 않습니다. 해당 분모는 null/NOT_EVALUATED이며 기존 카드 후보 평가와 별도로 후속 선정 입력/검사 원본이 필요합니다. 지연은 로컬 합성 처리 구간만 기록했고 실제 LLM p95 목표와 구분합니다.

## 검사·한계

- 전체 Python **292 PASS**, 기존 TestClient deprecation warning 1. 새 규칙/원문 대조/async callback/SDK 오류/취소·평가 분할·분모와 기존 v1 회귀 포함입니다.
- 최초 새 SDK 검사 1 FAIL은 비동기 raw response의 parse를 await한 호출 오류였습니다. 설치 SDK의 raw.parse는 동기 메서드이므로 수정 후 새 SDK·기존 SDK 검사와 전체 회귀가 통과했습니다.
- Ruff·diff 검사 PASS, 의존성·공통 모델·API·Schema 원본 변경 없음.
- 실제 LLM·입력 변환·보류 분할 평가·브라우저/신규 Registry 연결·성능 목표·사람 리뷰는 미실행입니다. 보존 브랜치와 기존 사용자 작업을 유지하고 push/PR은 하지 않았습니다.

## 후속 독립 QA

[`codex/v5-d-independent-qa`](../qa/v5-d-independent-qa.md)에서 같은 분석 소스를 C #62 고정 후보에 주입해 ASGI/SQLite/합성 Registry 12개를 통과했습니다. C 후보 환경의 Analyzer 251개도 통과했습니다. 실제 신규 A/B/C 통합 완료와 구분합니다. 과거 고정 제품의 PostgreSQL/Anvil mixed 18그룹이 이번에 통과했지만 G07은 원인·수정 인계 전까지 미해결을 유지합니다. 상세 SHA/명령/실행 경계는 연결된 QA 보고서에 있습니다.

## 2026-10-16 사용자 선택: Jev 선행 · OpenAI 후속

사용자가 `typesafe/jev`를 지목하고 OpenAI 앞에 사용하겠다고 명시했습니다. D 인계에서 모델 구성을 모두 미정으로 취급하던 상태를 갱신합니다. 현재 실행 소스와 과거 평가 결과는 그대로 보존하며 실제 Jev 연결 완료로 기록하지 않습니다.

[TypeSafe 공식 소개](https://docs.typesafe.ai/introduction)에 따르면 Jev는 상태와 형식이 정해진 질문을 받아 선택·점수·확률을 반환합니다. [공식 패턴](https://docs.typesafe.ai/patterns)은 분류와 신뢰도에 따른 라우팅을 설명합니다. 이 특성을 바탕으로 **Jev의 선행 판단 → OpenAI의 후속 분석/근거 설명 → 기존 원문 인용 대조 → 공통 보고서**를 연결 방향으로 정리합니다. 세부 책임 배분은 D의 연결 제안이며 아직 실행 구현이 아닙니다. 발행 검증은 기존 C/Registry 경로가 맡습니다.

남은 설정은 다음과 같습니다.

- Jev 호출 경로: OpenRouter 또는 TypeSafe 공식 API 직접 연결 여부. OpenRouter의 [모델 페이지](https://openrouter.ai/typesafe/jev)를 확인했으나 사용자가 호출 경로/고정 버전을 선택한 것으로 간주하지 않습니다.
- Jev 질문·라벨·신뢰도 임계값, 어떤 결과에서 OpenAI를 호출/생략할지, 실패/불일치 처리. 임의로 정상 판정이나 OpenAI 호출 생략을 도입하지 않습니다.
- 후속 OpenAI 모델, 유료 평가/전송 범위와 예산. 입력 종류/우선순위와 합성 자료 라벨·분할 리뷰도 계속 미정입니다.

이번 변경은 사용자 선택과 남은 연결 설정을 D 인계에 기록한 문서 변경입니다. Jev SDK·의존성·API 호출·유료 실행·입력 활성화·공통 Schema 변경은 없습니다. OpenAI Decisions API 제외 결정도 유지하며 Jev 선택을 그 API 도입으로 바꾸어 기록하지 않습니다. 기능 검사를 재실행한 것으로 보고하지 않습니다.
