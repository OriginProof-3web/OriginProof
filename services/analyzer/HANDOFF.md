# M2 → M1: 카드 알림 후보 추출 구현 Handoff

> **MVP 과거 기록 — 현재 작업 지시로 사용하지 마세요.** 당시 역할·브랜치·미완료 상태·설정값을 보존한 문서입니다. 현재 개발은 [시작 안내](../../START_HERE.md)와 [개발 계획서](../../docs/development_plan.md)를 따르며, 아래의 실행/병합 지시는 자동으로 적용하지 않습니다.

개발 시작 기준: `origin/mvp/integration@3bbaba025acd9d692ab484232f778a12a7579702`
현재 병합 기준: `origin/mvp/integration@f029e76b310de30cb27731be08c18a4360dc281c`
작업 브랜치: `mvp/ai` · 작성일: 2026-09-07

## 현재 결과

사용자의 최신 통합 기준 작업 시작 지시에 따라 `git fetch origin` 후 위 SHA에서
`git switch -c mvp/ai origin/mvp/integration`을 실행했다. M1 병합 준비를 위해
최신 통합 커밋 `f029e76` 위로 rebase했다.
이전 체인 브랜치는 병합하지 않았다. 이전 단독 프로젝트도 수정하지 않았다.

M2 추출 구현과 로컬 Python 검증을 완료했다. 다만 **전체 공통 환경/배포/PR 완료 상태는 아니다.**
Docker/Foundry가 없어서 `bootstrap-check`의 환경 단계, 전체 `mvp-test`, 공통 `smoke`는
완료되지 않았다. 네 명 fingerprint 일치 및 지정 리뷰어 clean-clone 재현도 아직 확인하지 않았다.

이전 main 기준 보류 보고서는 [과거 Bootstrap 점검 기록](notes/bootstrap_audit_4ee98f3.md)으로 보존했다.
그 보고서의 9필드 Candidate/M1 역할 정보는 과거 상태이며 이번 구현의 기준이 아니다.

## M1 연결 계약

- Endpoint: `POST /v1/analyze/card-payment-notice` (Analyzer, 기본 8001)
- 요청 모델: `originproof_analyzer.inputs.SemanticInput`
- 서비스: `originproof_analyzer.service.SemanticInterface.analyze_card_payment_notice`
- 포트: `originproof_analyzer.providers.LLMProvider.extract_card_payment_notice`
- 출력: `originproof_core.CardPaymentNoticeCandidate`, transaction_id 포함 **10개 필드**
- FastAPI entrypoint와 health는 `originproof_analyzer.main:app`, `{"status":"live"}` 그대로다.
- M1 `POST /v1/mvp/card-notices/verify`와 검증 규칙은 변경하지 않았다.
- API 연결/배포와 최종 Verification Status 결정은 M1 후속 통합 범위다.

추출 후 M1에 넘길 객체에는 verification_status, lifecycle_status, reason_codes,
authenticity score, 자유 형식 판정 또는 provider 내부 객체를 넣지 않는다.
공통 모델/JSON Schema를 재정의하거나 수정하지 않았다.

입력·응답 예제와 설정은 [Analyzer README](README.md)에 있다.
Fixture `fixtures/mvp/analyzer_cases.json`에 정상/금액 변경/누락의 전체 기대 Candidate가 있다.

| 입력 | 주요 기대 값 |
| --- | --- |
| normal | amount_minor=154000, transaction_id=txn_demo_001, confidence=0.98 |
| amount_changed | amount_minor=1540000, 다른 추출 필드는 정상과 동일 |
| readme_missing_transaction | transaction_id=null, missing_fields=["transaction_id"], confidence=0.8575 |
| missing_proof | proof_id=null, missing_fields=["proof_id"], confidence=0.8575 |

원본에 없는 transaction_id를 Proof ID나 Golden Fixture에서 가져오지 않는다.
정상·금액 변경 기대 값은 기존 Golden JSON과도 테스트에서 대조한다.
Fixture의 expected_verification_status/expected_reason_codes는 downstream annotation이며
Analyzer 응답/판정이 아니다.

## 설정·오류·메타데이터

Prompt: `card_payment_notice_v3`
설정 키: LLM_PROVIDER, OPENAI_MODEL, OPENAI_REASONING_EFFORT, OPENAI_API_KEY,
LLM_TIMEOUT_SECONDS, LLM_MAX_RETRIES, ANALYZER_MIN_CONFIDENCE.

모델 기본값 `gpt-5.6-luna`, provider 기본값 `mock`을 유지했다.
OpenAI Docs 스킬의 공식 Responses/Pydantic 지침을 반영했다.
유료 API 호출은 실행하지 않았고 live 테스트는 opt-in이다.

오류 body는 `{"error":{"code":"...","message":"고정 안전 문자열"}}`이며 HTTP mapping은 다음과 같다.

- 422: MALFORMED_INPUT / UNSUPPORTED_INPUT / REFUSAL / LOW_CONFIDENCE
- 502: SCHEMA_MISMATCH / INCOMPLETE_OUTPUT
- 503: RATE_LIMIT / PROVIDER_UNAVAILABLE
- 504: TIMEOUT

SDK 단일 retry loop(최대 3회 시도), 요청별 timeout, raw envelope 선검사,
strict JSON 검증을 적용했다. SDK 오류/validation/serializer 경고에 원본 값을 노출하지 않는다.
Logger의 `record.analyzer`에는 설정된 provider/model/prompt 버전, 입력 종류, 경과 시간,
안전한 오류 코드만 있다. 실제 배포에서는 해당 INFO 이벤트 수집 설정이 필요하다.

## 실제 검증 결과

| 실행 명령 | 결과 |
| --- | --- |
| `make bootstrap-check` | 구조 통과 / 환경 실패: docker, forge 없음 |
| `uv sync --all-packages --all-groups --locked` | 통과 |
| `make test-analyzer` | **97 passed** |
| `make mvp-test` (`make -k`로 나머지 단계도 확인) | 실패: forge 없음. Python 하위 단계는 통과; 최종 전체 Python 결과는 아래 make test 참조 |
| `make lint` | 통과 |
| `make typecheck` | 통과 (현 target은 compileall) |
| `make test` | **111 passed** (최종 수정 포함) |
| `make smoke` | 실패: 127.0.0.1:8000 서비스 미기동 |
| `python -m originproof_analyzer.evaluation` (uv workspace) | **10/10**, 합성 Text + image replay; 실제 모델 평가 아님 |
| `uv build --package originproof-analyzer` | wheel/sdist 빌드 통과 |
| 임시 localhost uvicorn + curl | health 및 실제 정상/변경 POST 모두 HTTP 200; 금액 154000 / 1540000 확인 후 서버 종료 |
| `git diff --check` | 통과 |

마지막 테스트 경고는 기존 Starlette/AnyIO의 deprecated alias 1건이다.
평가 보고서는 ignored 산출물 `build/m2-evaluation.json`에 있고 커밋 대상이 아니다.
기존 Golden Fixture 2개와 M1/공통 Schema/체인/Compose/Makefile의 diff가 없음을 확인했다.
변경 영역의 API token/private-key 패턴 검사에서는 일치 항목이 없었고,
`.env`, build 및 dist 산출물의 Git ignore 적용을 확인했다. 이는 완전한 비밀정보 감사는 아니다.

## M1 확인 및 후속 작업 요청

1. **공유 lockfile 리뷰**
   - 파일: `services/analyzer/pyproject.toml`, `uv.lock`
   - 요청: OpenAI SDK 2.54.0, Pillow 12.3.0과 전이 의존성 추가를 통합 리뷰한다.
     기존 dependency 버전 교체는 하지 않았다.
   - 이유: 실행 지침의 Responses/Pydantic 및 안전한 이미지 디코딩에 필요하다.
   - 기대: frozen/locked install과 Docker Analyzer build 성공.
   - 테스트: locked sync, test-analyzer, Docker build, smoke.
   - 기한/요청 브랜치: M2 PR 병합 전, mvp/ai.

2. **M1 API 연결과 Docker 재현**
   - 인터페이스: 위 추출 endpoint → 기존 M1 verify 요청의 candidate.
   - 기대: 정상/변경 후보는 위 Fixture와 같고 최종 판정은 M1에서만 생성한다.
   - 테스트: Docker 공통 기동·seed·smoke·전체 mvp-test와 clean-clone 리뷰어 재현.
   - 기본 Mock HTTP는 임의 이미지를 지원하지 않는다. 합성 이미지 replay는 코드 주입 테스트이고,
     실제 이미지 추출은 OpenAI opt-in이다. Dockerfile은 fixtures를 복사하지 않아도 Text와
     OpenAI 경로를 실행할 수 있다. Docker 이미지/원격 API 실제 동작은 아직 검증하지 않았다.
   - 기한/요청 브랜치: 통합 데모 전, mvp/ai.

3. **공통 fingerprint 문제는 별도 담당 범위**
   - 파일: `scripts/ci/environment_fingerprint.py`
   - 기존 점검에서 source tree 해시에 __pycache__가 포함되어 테스트 전후 해시가 달라졌다.
     이번 통합 버전도 같은 구현이다. ABI 누락/버전 정렬 문제도 M2가 임의 수정하지 않았다.
   - 기대/테스트: 생성물 제외, 승인된 ABI/compiler/version 검사, 네 명 comparable 일치.
   - 기한/요청 브랜치: 공통 환경 검증 완료 전, mvp/ai.

이 문서는 로컬 handoff다. 원격 push, PR 생성, 통합 브랜치 병합이나 팀원에게 메시지 발송은 하지 않았다.
