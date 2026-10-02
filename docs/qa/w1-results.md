> 현재 W1 기준의 후속 결과는 [2026-10-02 최종 연결 검증](w1-final-verification.md)을 참조합니다. 아래는 당시 SHA/환경의 역사 기록입니다.

# W1-D 독립 검사 결과 — 2026-10-01

기준: `3295a71c10a1a99c523d3cfefde91b5737b737ac` + 이번 D 작업 트리 변경.
브랜치: `codex/w1-d-qa`, 대상 phase: `phase/W1`.
검사는 `3295a71c10a1a99c523d3cfefde91b5737b737ac` 위의 D 작업 트리에서 실행했다.
작성자 외 리뷰는 아직 미수행이다.

## 실제 검사

| 명령/검사 | 결과와 범위 |
| --- | --- |
| `UV_PROJECT_ENVIRONMENT=.uv-venv uv sync --all-packages --all-groups --locked` | 성공. lockfile 변경 없이 Python 3.13.7 환경 구성 |
| `make bootstrap-check` | 초기에는 `.env` 없음으로 실패; 합성 `.env` 생성 후 구조·환경 모두 통과 |
| `make env-fingerprint` | 성공. [환경 기록](w1-environment.json) |
| `LLM_PROVIDER=mock make test` | **147 passed, 1 warning**. API health, 공통 코어, Analyzer, 환경 검사 포함 |
| 새 파일의 `ruff check` | 통과. fixture 생성기·무결성 검사·v1 독립 회귀 |
| fixture 생성 함수와 cases.json 비교 | 동일 자료 재현 확인; 28개 사례 모두 NOT_RUN |
| `make smoke` | 초기에는 API 미기동으로 실패; `make mvp-e2e` 후 통과 |
| `docker info` | Docker Desktop 시작 후 서버 29.7.2 연결 확인 |
| `make mvp-test` | 통과: API 5, Analyzer 130, Foundry 컨테이너 Contract 10, 통합 Python 135; Analyzer·통합 검사에 같은 deprecation warning 1개 |
| `make mvp-e2e` | 통과: 합성 DB migration/seed, 로컬 Anvil 계약 배포, HTTP 정상 VERIFIED + ACTIVE, 금액 변조 TAMPERED + AMOUNT_MISMATCH, smoke 통과. 브라우저 E2E와 W1 신규 기능 연결은 미실행 |

macOS 기본 git/make는 Xcode 라이선스 오류가 있었지만 설치된 Command Line Tools
실행 파일은 정상 동작했다. 이 환경에서는 `PATH=/Library/Developer/CommandLineTools/usr/bin:$PATH`
접두사로 실제 Makefile을 실행했다. 라이선스를 대신 승인하거나 글로벌 PATH를 바꾸지 않았다.
Starlette/AnyIO deprecation warning 1개는 기록하고 의존성을 임의 변경하지 않았다.

147개 중 D의 신규 33개는 합성 QA 자료 무결성 31개와 카드 독립 회귀 2개다.
카드 회귀는 기존 C Golden의 signing digest를 확인하고 메모리 내 임시 서명기로 서명한 뒤
실제 VerificationService에 기존 카드 fixture를 전달했다. 정상은 VERIFIED + ACTIVE,
금액 변경은 TAMPERED + ACTIVE / AMOUNT_MISMATCH 기대값과 일치했다.
Repository/BlockchainReader는 in-memory mock이며 실제 RPC·HTTP E2E 결과가 아니다.
Golden 파일은 수정하지 않았다.

독립 검사 작성 중 request_id의 기존 req_ 규칙을 어긴 테스트 입력이 실패했다.
테스트 입력을 공통 계약에 맞춰 수정했고, fixture ID도 공통 모델의 생성 Schema 규칙으로
검사하도록 하여 key_ 형식의 이탈을 막았다. 제품 모델을 테스트 편의상 바꾸지 않았다.

## 환경 차이와 연결 대기

Node는 24.8.0으로 기준 22.18.0과 다르며 이번 Python 검사는 Node를 사용하지 않는다.
웹 검사 전에 맞춰야 한다. Python은 3.13.7(프로젝트 허용 범위), pnpm은 11.19.0이다.
이 작업 트리에 기존 `.env`가 없는 것을 확인하고 `.env.example`에서 합성 `.env`를 생성했다. `LLM_PROVIDER=mock`, `OPENAI_MODEL=gpt-6-luna`이며 개인 비밀값은 읽거나 덮어쓰지 않았다.
환경 fingerprint의 컨테이너 설정 해시를 보존했고 host_forge는 참고 정보다.

착수 시 확인한 선행 PR은 모두 OPEN·미병합이다:

- [C #23](https://github.com/OriginProof-3web/OriginProof/pull/23): 인증·신청 API.
- [B #26](https://github.com/OriginProof-3web/OriginProof/pull/26): Registry 계약·체인 작업.
- [A #27](https://github.com/OriginProof-3web/OriginProof/pull/27): 신청·작업 화면.

다른 담당 branch는 병합하지 않았다. ADR의 정책은 승인 상태이며 C1/C3의 실제 API·v2
모델·생성물 소비 확인, C2/C4 실제 권한/신청 연결과 A/B 통합은 별도 대기다.
W1-D1의 기존 MVP 로컬 EVM/HTTP E2E 재현은 완료했다. W1 신규 기능의 실제 A/B/C 연결, 브라우저 E2E와 결과 합의는 아직 완료하지 않았다.

## 후속 실행

C가 제공할 계정·v2 생성 계약에 QA profile을 대응시킨 뒤 각 case의 실제 결과를 기록한다.
로컬 Docker·합성 DB·Anvil에서 기존 MVP E2E를 완료했다. W1 선행 변경이 phase에 들어오면 새 기능의 실제 API·브라우저 E2E를 별도 수행한다.
D 소유자 검토와 지정 리뷰어 확인 후 작업 PR을 phase/W1 대상으로 제출한다.
P1 추출 확장·유료 모델·다른 담당 기능 구현·단계 완료 판정은 수행하지 않았다.

## 후속 합동 검증 — 2026-10-01

위 기록 이후 A/B/C/D 작업 브랜치의 현재 PR 내용을 임시 통합 트리에서 함께 적용하고,
W1-C3의 v2 모델/생성 스키마 준비 작업을 별도 추가한 기준
`31ddda0ca63defd0a4df10d5c8511a6e5859e18f`에서 재검증했다. 이 SHA는 로컬 합동 검증
기준이며 `phase/W1` 또는 `integration`에 병합된 SHA를 뜻하지 않는다.

| 명령/검사 | 결과와 범위 |
| --- | --- |
| `LLM_PROVIDER=mock make test` | **163 passed**, deprecation warning 1개. v1 회귀 및 W1-C3 v2 계약 모델 포함 |
| `make lint` | Python Ruff 및 웹 ESLint 통과 |
| `make typecheck` | Python compileall 및 TypeScript 검사 통과 |
| `make mvp-test` | API 10, Analyzer 130, Foundry 컨테이너 Contract 10, 통합 Python 140 통과; deprecation warning 1개 |
| `make mvp-e2e` | 합성 DB migration/seed, Foundry 컨테이너 기반 로컬 배포, HTTP 정상 VERIFIED + ACTIVE 및 변조 TAMPERED + AMOUNT_MISMATCH, smoke 모두 통과 |
| 실제 API·DB 흐름 | 로그인·역할 권한·CSRF·발행자 신청·운영자 조회/승인·자기 승인 차단·중복 결정 거부·로그아웃 세션 폐기를 합성 계정으로 확인; 테스트 행 정리 완료 |
| 실제 Chromium 브라우저 흐름 | Next rewrite와 실제 API/DB를 거쳐 발행자 신청, 운영자 승인, 발행자 재조회에서 체인 활성화 대기 상태 표시까지 통과; 합성 테스트 행 정리 완료 |
| 웹 Playwright 기존 테스트 | 4개 통과; 웹 컴포넌트 테스트 6개 통과 |
| Indexer | `UV_PROJECT_ENVIRONMENT=.uv-venv uv run pytest -q services/indexer/tests`: 48 passed, live-chain opt-in 1 skipped |

실제 연결 검사는 로컬 합성 계정·DB·Anvil로만 진행했으며 외부 기관·실결제·실제 체인/RPC는
사용하지 않았다. W1-C3의 새 v2 모델과 JSON Schema/TypeScript 생성물은 준비됐지만, v2 API
경로 및 실제 v2 발급·검증·상태 수명주기 구현은 후속 계획 작업이다. 보안/리뷰 승인, A/B/C/D
각 PR의 `phase/W1` 병합, 단계 독립 QA·전체 수용 기준과 `phase/W1` → `integration` 승격은
여전히 남아 있으므로 이 합동 검사만으로 W1 완료를 선언하지 않는다.
