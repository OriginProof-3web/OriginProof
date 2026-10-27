# T1 서버↔AI 연결 준비 인계 — 2026-10-27

작성: 키티 프라이드(개발), 대표 김형준님 지시. 수신: 민서(C), 인준(D), 웹(A).
작업 ID: T1, 관련 본선 V5-W5-C/D/A. 사용자 지시의 수신자 호칭을 사용하며 저장소의 담당자 인적 정보를 변경하지 않습니다.

- 기준/검증 코드 SHA: `df39f1477f0ed513b1e603066f7b2442fc16f8c9`, branch `prep/a-ai-connect-readiness` + 이 문서와 새 시험의 미커밋 변경.
- 시작 시 사용자 변경 없음. 생산 코드·모델·생성물·lockfile 변경 없음. 최신 허락에 따라 commit/fetch/push/PR 및 기타 `.git` 쓰기 없음. PR URL·새 커밋 SHA 없음.
- **독립 Mock HTTP 시험 완료 / 실제 생산 연결 대기**입니다. C/D/A 리뷰, clean clone 재현, 단계 완료를 주장하지 않습니다. 별도 메시지는 발송하지 않았습니다.
- 입력은 이번 대표 지시(2026-10-26 결정 인용)에 따라 텍스트·이미지, 음성 보류입니다. 저장소 계획의 입력 미정 문구는 과거 상태이며 이번 문서는 기준 문서 자체를 수정하지 않습니다. 근거: `docs/development_plan.md:342`, `docs/shared_contract_v5.md:135` 및 이번 작업 지시. Claude 사용 권한·크레딧 가용성은 대표 제공 정보이며 API 호출로 확인하지 않았습니다.

## 1. 현재 실행 경계와 시험

API 기본 `app = create_app()`에는 처리기 주입이 없으며, 처리기 기본값과 state 저장값은 None입니다. 텍스트도 기본 비활성입니다. 입력을 켜서 접수한 뒤 처리기 없이는 `ANALYZER_UNAVAILABLE`로 실패합니다. 근거: `apps/api/src/originproof_api/main.py:80`, `apps/api/src/originproof_api/main.py:157`, `apps/api/src/originproof_api/main.py:226`, `apps/api/src/originproof_api/settings.py:45`, `apps/api/src/originproof_api/wallet_analyses.py:152`.

추가 시험: `apps/api/tests/test_ai_connect_readiness.py:1`.
기존 합성 계정·SQLite/SQLAlchemy fixture와 httpx ASGITransport를 재사용합니다. 새 앱을 `create_app(analysis_processor=PhishingAnalyzer(MockLLMProvider(...)))`로 만들고 실제 라우트·처리 태스크·저장·조회 코드를 실행합니다. TCP 서버/서비스 간 네트워크가 아닌 **in-process ASGI HTTP 시험**입니다. 인증 의존성을 기존 fixture로 대체하고 lifespan은 실행하지 않으므로 로그인, 생산 startup/shutdown, PostgreSQL, 분산 실행의 검증은 아닙니다. 근거: 새 시험 및 `apps/api/tests/test_wallet_runtime.py:97`.

요청 순서: `POST /v3/inputs {kind: TEXT, text}` → 201 `input_ref` → `POST /v3/analyses {request_id, input_ref}` → 202 QUEUED → 실제 background task 대기 → `GET /v3/analyses/{analysis_id}` → 200.

| 사례 | 기대값 / 확인 내용 |
| --- | --- |
| 정상 replay | COMPLETED, CAUTION, source=LLM, emoji 앞부분을 포함한 Unicode 코드 포인트 `[start,end)`와 quote 일치 |
| D에 잘못된 quote replay | D가 인용을 제거, 규칙 근거 없는 입력은 UNDETERMINED, `LLM_ANALYSIS_UNAVAILABLE:GROUNDING_MISMATCH`; API 작업 자체는 COMPLETED |
| D 검증 뒤 C 경계에 잘못된 quote 주입 | C `ground_report`가 거부, FAILED / GROUNDING_MISMATCH / report=null |
| D 검증 뒤 C 경계에 잘못된 offset 주입 | C가 독립 거부, FAILED / GROUNDING_MISMATCH / report=null |

C 실패 두 건은 시험 전용 wrapper에서 D 결과를 변조합니다. D를 정상 통과한 실제 결과가 잘못됐다는 주장이 아닙니다. 정상/보류 보고서 모두 verification=null, verification_not_run_reason=NO_DOCUMENT_REFERENCE이며 mock 성능을 실제 모델 정확도로 표현하지 않습니다. 근거: `services/analyzer/src/originproof_analyzer/phishing.py:94`, `services/analyzer/src/originproof_analyzer/phishing.py:165`, `apps/api/src/originproof_api/wallet_analyses.py:66`, `apps/api/src/originproof_api/wallet_analyses.py:161`.

## 2. 민서(C): 생산 연결

1. **위치·형태 제안(추정, 미구현):** `create_app`의 명시적 주입 우선 계약을 보존하고, 처리기가 없을 때만 Settings로 선택한 provider를 lifespan에서 구성하여 `app.state.analysis_processor`에 넣습니다. 반드시 `cleanup(restart=True)`가 QUEUED를 재실행하기 전에 준비해야 합니다. 형태는 async callable `(text: str) -> AnalysisReport`이며 `PhishingAnalyzer(provider=..., settings=...)`를 재사용합니다. 근거: `apps/api/src/originproof_api/main.py:89`, `apps/api/src/originproof_api/main.py:114`, `services/analyzer/src/originproof_analyzer/phishing.py:136`.
2. **배포 경계:** API 패키지는 analyzer를 의존성으로 선언하지 않았습니다. workspace 전체 설치 시험이 API 단독 이미지에서 import 가능함을 보장하지 않습니다. C/D가 in-process 패키징 또는 서비스 간 async adapter를 선택해야 합니다. 현재 analyzer HTTP `/v1/analyze/card-payment-notice`는 CardPaymentNoticeCandidate 추출용이며 AnalysisReport 피싱 endpoint가 아닙니다. 이를 그대로 분석 callback으로 연결하면 안 됩니다. 서비스 간 방식은 새 endpoint/인증/timeout 계약이 필요합니다(추정). 근거: `apps/api/pyproject.toml:5`, `services/analyzer/src/originproof_analyzer/main.py:55`, `services/analyzer/src/originproof_analyzer/main.py:63`.
3. **수명주기:** 앱별 provider 1개 구성 제안(추정), 공유 mutable 요청 상태는 두지 않습니다. 소유 HTTP client가 있으면 종료 시 작업 취소·대기 뒤 닫고, 주입 client의 소유권은 호출자와 합의하십시오. 기존 OpenAI async 경로는 호출마다 client를 닫습니다. API는 종료 시 analysis_tasks를 취소·대기합니다. 근거: `services/analyzer/src/originproof_analyzer/providers.py:320`, `apps/api/src/originproof_api/main.py:134`.
4. **timeout·동시성:** C는 접수 시각부터 180초 잔여 예산으로 `wait_for`, D는 내부 180초, provider는 기본 요청 20초/재시도 2회입니다. 취소를 삼키지 않고 전체 예산 안에서 처리해야 합니다. 계정별 진행 중 1건·10분당 5건은 기존 제어이며, 전 계정 공통 동시성 상한은 별도 구현·부하 검증 필요(추정: 제한 semaphore 또는 기존 queue 재사용). 현재 asyncio task는 분산 queue가 아닙니다. 근거: `apps/api/src/originproof_api/wallet_analyses.py:149`, `apps/api/src/originproof_api/wallet_analyses.py:200`, `apps/api/src/originproof_api/wallet_analyses.py:283`, `services/analyzer/src/originproof_analyzer/phishing.py:159`, `services/analyzer/src/originproof_analyzer/settings.py:15`.
5. **텍스트 켜기:** 기존 환경 이름은 `API_WALLET_TEXT_INPUT_ENABLED=true`입니다. Settings는 `.env`와 `API_` prefix를 사용합니다. 이는 처리기 연결과 별개이며 이번에는 생산 설정을 켜지 않았습니다. 근거: `apps/api/src/originproof_api/settings.py:45`, `apps/api/src/originproof_api/settings.py:48`, `apps/api/src/originproof_api/wallet_analyses.py:210`.
6. **이미지:** 별도 업로드·보관/소유권·변환 경로가 필요합니다. 현재 `/v3/inputs`는 TEXT를 저장하고 `/v3/analyses`도 TEXT만 수락하며 worker는 UTF-8 decode합니다. 기존 `SemanticInput`의 MIME/signature/5MiB/12MP/1프레임 검사를 재사용할 수 있지만 이것만으로 v3 이미지 분석은 연결되지 않습니다. 변환 텍스트·좌표/원본 이미지 대응과 실패·보존기간을 C/D/A가 합의해야 합니다(추정). 현재 C `ground_report`는 page/time 근거를 거부하므로 이미지 영역 근거를 지원한다고 표시하지 마십시오. 근거: `apps/api/src/originproof_api/wallet_analyses.py:136`, `apps/api/src/originproof_api/wallet_analyses.py:221`, `apps/api/src/originproof_api/wallet_analyses.py:258`, `services/analyzer/src/originproof_analyzer/inputs.py:11`, `apps/api/src/originproof_api/wallet_analyses.py:75`.

C 독립 완료 명령은 5절입니다. 생산 연결 완료에는 기본 엔트리포인트의 Settings만으로 Mock 성공을 재현하는 lifespan 시험, 취소/재시작·동시성·종료 client 정리, API 실제 배포 패키징, PostgreSQL 확인을 추가해야 합니다. 이미지 수용은 별도 정상·거부 업로드와 변환/근거 시험 뒤 판정합니다. 이 기준선 통과만으로 '남은 작업은 한 줄 주입뿐'이라고 판단하지 않습니다.

## 3. 인준(D): 공급자·Claude 인계

- 인터페이스는 `provider_name`, `model`, 동기 `extract_card_payment_notice(SemanticInput) -> CardPaymentNoticeCandidate`, 비동기 `analyze_phishing(text) -> AnalysisReport | dict`입니다. 기존 카드 회귀와 피싱을 구분하십시오. 근거: `services/analyzer/src/originproof_analyzer/providers.py:37`.
- 출력 원본은 `AnalysisReport`·`AnalysisEvidence`입니다. risk_level은 HIGH/CAUTION/NO_CLEAR_INDICATORS/UNDETERMINED, evidence 최대 50, limitations 최대 20입니다. LLM 근거는 source=LLM, 짧은 quote와 코드 포인트 offset을 제공하고 발행 판정은 생성하지 않습니다. 모르는 추출 필드는 null이며 근거/필수 구조가 없으면 성공을 꾸미지 않습니다. 근거: `packages/python/originproof_core/wallet_contract.py:407`, `packages/python/originproof_core/wallet_contract.py:425`, `services/analyzer/src/originproof_analyzer/providers.py:230`, `services/analyzer/src/originproof_analyzer/phishing.py:94`.
- **Claude 추가 제안(추정, 이번 미구현):** 위 Protocol을 구현하는 Anthropic adapter와 provider 선택 분기를 D가 추가하고 C가 composition을 연결합니다. 구조화 출력에 동일 schema/검증을 적용하며 refusal/incomplete/timeout/rate limit/schema/provider 오류를 기존 `AnalyzerErrorCode`에 매핑하고 취소를 전파합니다. 원시 응답·원문·키를 로그로 남기지 않습니다. 기존 공급자는 mock/openai뿐입니다. 근거: `services/analyzer/src/originproof_analyzer/settings.py:10`, `services/analyzer/src/originproof_analyzer/errors.py:4`, `services/analyzer/src/originproof_analyzer/phishing.py:165`.
- **설정 이름 제안(추정, 현재 사용 불가):** `ANALYZER_LLM_PROVIDER=anthropic`, `ANALYZER_ANTHROPIC_API_KEY`, `ANALYZER_ANTHROPIC_MODEL`, `ANALYZER_TIMEOUT_SECONDS`, `ANALYZER_MAX_RETRIES`. API 배포에서 서버 `.env`만 읽도록 C/D가 명시적으로 연결하고 key는 SecretStr/repr 제외로 취급하십시오. 현재 AnalyzerSettings는 env_file=None, prefix 없음이므로 이 이름들은 자동 적용되지 않습니다. 현재 실제 이름은 `LLM_PROVIDER`, `OPENAI_MODEL`, `OPENAI_API_KEY`, `LLM_TIMEOUT_SECONDS`, `LLM_MAX_RETRIES`입니다. 새 SDK 의존성은 이번 허용 범위 밖이며 도입이 필요하면 별도 승인·lock 갱신을 받으십시오. 근거: `services/analyzer/src/originproof_analyzer/settings.py:7`.
- 먼저 Mock replay와 오류 주입으로 동일 계약을 통과시키고, 대표의 구체적 live 호출 허락 뒤에만 소량 평가하십시오. 이번에는 유료 호출 0건이며 Claude/크레딧을 실제 검증하지 않았습니다. RAG 지식베이스 구축·정량 모델 지표 평가·Decisions API는 별도 범위입니다. 기존 평가 자산을 실제 Claude 성능으로 표시하지 않습니다. 근거: `docs/development_plan.md:358`, `docs/development_plan.md:721`, `services/analyzer/src/originproof_analyzer/providers.py:136` 및 이번 대표 지시.

## 4. 웹(A, 5안): 확인된 상태와 소비 제안

현재 SHA의 `apps/web`에는 5안 4축 보고서·형광펜 구현이나 `/v3/analyses` 소비 코드를 확인하지 못했습니다. 현재 홈은 구버전 VerificationRequest/Result를 사용해 `/api/v1/mvp/card-notices/verify`를 호출합니다. 따라서 아래는 **공통 계약 기반 소비 제안(추정)**이며 실제 5안 코드와 맞췄다는 뜻이 아닙니다. 근거: `apps/web/app/page.tsx:5`, `apps/web/app/page.tsx:116`; 확인 검색: `rg -n 'risk_level|start_offset|/v3/analyses|형광펜|4축' apps/web`.

| 화면 용도 | 받을 필드 / 처리 제안 |
| --- | --- |
| 비동기 상태 | AnalysisJob.analysis_id/status/error_code/report, 만료 result_expires_at; 202는 접수, 성공 판정 금지 |
| 4축 중 AI 칸 | report.risk_level/evidence/limitations; 발행 기록·내용 비교·현재 상태를 AI가 정하지 않음 |
| 발행 측 표시 | report.verification 또는 verification_not_run_reason; 비교 범위와 현재 상태는 VerificationResult 소비 |
| 형광펜 | evidence[].quote/start_offset/end_offset/source/rule_id, 분석에 쓴 동일 변환 텍스트; offset은 Unicode 코드 포인트 `[start,end)` |
| 보관 | retain_report/retain_original/result_expires_at/original_expires_at; 원문을 응답에 있다고 가정하지 않음 |

근거: `packages/python/originproof_core/wallet_contract.py:399`, `packages/python/originproof_core/wallet_contract.py:407`, `packages/python/originproof_core/wallet_contract.py:425`, `packages/python/originproof_core/wallet_contract.py:441`, `docs/ui_ux_design.md:111`.

형광펜은 JS 문자열의 UTF-16 slice를 그대로 쓰지 말고 코드 포인트 배열(예: Array.from(text)) 기준으로 변환하고 quote를 재대조해야 합니다(추정: 구현 제안). GET 결과에 전체 변환 텍스트는 없습니다. 웹이 입력 텍스트를 유지하거나 소유권 있는 원본 경로를 사용해야 하며, 원본 미보관·만료 410을 고려하십시오. 이미지 텍스트·영역 계약은 아직 미연결입니다. 근거: `docs/shared_contract_v5.md:141`, `apps/api/src/originproof_api/wallet_analyses.py:395`, `packages/python/originproof_core/wallet_contract.py:425`.

연결 전 문구 제안(추정): **“AI 분석 연결 준비 중입니다. 현재 AI 결과는 제공되지 않습니다. 발행 ID로 기록을 조회할 수 있습니다.”** 분석 실패는 설계의 “분석을 완료하지 못했습니다. 발행 ID로 기록을 조회할 수 있습니다”를 사용하고, 판단 보류/명확한 정황 없음도 안전 보장으로 표시하지 마십시오. 규칙만 남으면 “규칙 검사 결과”와 LLM 제한을 표시하십시오. 근거: `docs/ui_ux_design.md:113`, `docs/ui_ux_design.md:181`, `docs/development_plan.md:338`.

브라우저는 지시에 따라 실행하지 않았습니다. 실제 5안 소스와의 소비 리뷰·화면·키보드·형광펜 실측은 A/본부 실측 요청으로 남깁니다.

## 5. 실행 기록·완료 기준

환경: macOS arm64, uv 0.12.10, CPython 3.13.15, 저장소 uv.lock 사용. 기본 uv 캐시 접근이 차단되어 `UV_CACHE_DIR="$PWD/.cache/uv"`로 작업 폴더 안 캐시를 사용했습니다. 환경 준비는 `uv sync --locked`, 이어 `uv sync --locked --all-packages`이며 둘 다 종료 코드 0, 후자는 workspace 3개 패키지까지 설치했습니다. 새 의존성/lock 변경은 없습니다. 초기 `uv run python --version`은 기본 캐시 권한 오류로 종료 코드 2였습니다.

검사 전 환경은 다음과 같습니다. live DB/체인 opt-in을 해제하고 provider 기본값은 mock으로 고정했습니다. 기존 provider 단위시험의 가짜 SDK 검사는 실제 유료 호출이 아닙니다.

```sh
export UV_CACHE_DIR="$PWD/.cache/uv" LLM_PROVIDER=mock ORIGINPROOF_WALLET_LIVE=0
unset TEST_DATABASE_URL TEST_CHAIN_RPC_URL TEST_CHAIN_MANIFEST
uv run pytest -q apps/api/tests/test_ai_connect_readiness.py
uv run ruff check apps packages/python services scripts
uv run pytest -q
```

| 실행 | 원문 마지막 줄 | 종료 코드 |
| --- | --- | --- |
| 새 HTTP 시험 | `4 passed in 6.91s` | 0 |
| 지정 Ruff | `All checks passed!` | 0 |
| 전체 pytest | `1079 passed, 12 skipped, 1 warning in 27.51s` | 0 |

전체 검사의 skip 12건은 통과 건수에 포함하지 않습니다. 경고 1건은 기존 FastAPI/Starlette TestClient의 httpx 사용 폐기 예정 안내입니다. 의존성 변경은 하지 않았습니다.

| T1 완료 기준 | 결과 |
| --- | --- |
| 지침·계획·계약·branch/SHA·사용자 변경 확인과 작업 전 보고 | 충족 |
| 생산 코드 변경 없이 Mock HTTP·ground_report 정상/실패 검증 | 충족, 새 시험 4건 |
| C/D/A 인계·근거·추정·명령·독립/생산 연결 차이 기록 | 충족, 실제 5안 소비 코드는 이 SHA에서 미확인 |
| 지정 Ruff·전체 pytest 실행과 마지막 줄/종료 코드 | 충족, 위 실행 기록 |
| 허용 경로·diff·비밀정보 확인 | 충족, 신규 시험/인계서 2개만 Git 변경; 토큰/키 값 없음 |
| 새 커밋 SHA | 생성 안 함, 최신 허락의 commit/.git 쓰기 금지 준수 |

실제 생산·이미지·Claude·웹·PostgreSQL·공개 체인 연결, 타인 리뷰/clean clone 재현은 미실행이며 이번 독립 준비 완료와 구분합니다. 별도 포트폴리오 파일은 허용 경로 밖이므로 수정하지 않았습니다. 최종 변경 파일 전체를 검토했으며 기존 추적 파일 diff는 없습니다. `git diff --check`는 종료 코드 0입니다(새 미추적 파일은 별도 공백/경로 검사).

## 6. 카톡용 전달 초안 (미발송)

민서님·인준님, df39f14 기준 MockLLMProvider→PhishingAnalyzer 주입 HTTP 기준선 4건을 추가했습니다.
텍스트 접수→분석→GET 정상과 D 근거 보류, C quote·offset 거부를 확인했습니다.
생산 기본 앱은 아직 처리기 미연결이며, 이미지 업로드·변환과 Claude adapter는 후속입니다.
연결 위치·수명주기·설정 제안·웹 필드는 docs/handoffs/a_ai_connect_handoff_20261027.md에 정리했습니다.
유료 호출·생산 코드 수정·커밋·push·PR은 하지 않았습니다.
