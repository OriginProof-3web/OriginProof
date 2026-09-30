# OriginProof Agent Instructions

## 1. 적용 범위와 현재 기준

이 파일은 저장소 전체에 적용됩니다. 사용자에게 항상 존댓말을 사용합니다. 하위 `AGENTS.md`는 해당 경로의 추가 규칙이며 공통 보안·소유권·검증 규칙을 반복하거나 약화하지 않습니다. 사용자의 명시적인 지시와 이미 승인한 결정을 우선합니다.

현재 작업은 MVP 이후 본선 W1~W7 개발입니다. [개발 계획서](docs/development_plan.md)가 범위·단계·수용 기준의 기준본이며, [본선 기술 결정](docs/adr/0001-finals-contracts.md)은 사용자님이 승인한 v3.0 정책을 기록합니다. 계획 승인, 코드 구현, 리뷰, 실제 연결 완료는 서로 다른 상태입니다. 문서를 고쳤다는 이유로 기능을 완료 처리하지 않습니다.

## 2. 제품 목표와 회귀 기준

발행 주체, 보호된 내용의 무결성, 현재 유효성을 검증합니다. AI는 후보 필드만 추출하며 진위를 결정하지 않습니다. `VERIFIED`는 실제 수행한 결정론적 검사의 성공이며, 현재 사용 가능 여부는 lifecycle과 권한·기간·single_use를 함께 확인합니다. ID만 조회한 결과에 자료 내용까지 일치한다고 표시하지 않습니다.

P0는 테스트 계정, 두 합성 기관, `PAYMENT_REQUEST`·`OFFICIAL_DOCUMENT`, 사용자·발행자·운영자 웹, 로컬 EVM입니다. 공개 회원가입·외부 로그인·호스팅·테스트넷·OCR는 선택 확장이며 P0를 지연시키지 않습니다. 기존 `CARD_PAYMENT_NOTICE`의 정상 `VERIFIED + ACTIVE`, 금액 변조 `TAMPERED + AMOUNT_MISMATCH` 및 v1 서명 Golden Fixture를 회귀로 보존합니다. 기존 MVP 성공은 본선 전체 성공의 증거가 아닙니다.

## 3. 기술 스택과 의존 방향

Python·uv, FastAPI·Pydantic, SQLAlchemy 2·Alembic·PostgreSQL, Redis·Celery, Solidity·Foundry·OpenZeppelin, Next.js·TypeScript, Docker Compose·Makefile·GitHub Actions를 유지합니다. 기존 구현과 설치된 의존성을 먼저 재사용하고, 필요 없는 계층·복제 SDK·새 프레임워크를 만들지 않습니다.

`apps/services → packages` 방향을 지킵니다. 검증 코어에 HTTP·DB·UI·provider 객체를 넣지 않습니다. 기존 `apps/`, `services/`, `packages/`, `fixtures/`, `infra/`, `scripts/`, `docs/`, `.github/` 구조를 사용하고 승인 없이 새 최상위 디렉터리를 만들지 않습니다.

## 4. 담당자와 경로 소유권

| 역할 | 담당자 | 주 담당 경로·책임 |
| --- | --- | --- |
| A | 김형준님 `@kimhyounjun` | `apps/web/`: 세 역할 화면·UX·접근성 |
| B | 여하민님 `@hamin1228` | `packages/contracts/`, `services/indexer/`, `apps/api/src/infrastructure/blockchain/`: Contract·ABI·배포·Adapter |
| C | 사용자님 `@Jordi2801K` | blockchain Adapter 외 `apps/api/`, `packages/python/`, 모델 생성기: 인증·발행·DB·검증·통합 조율 |
| D | 여인준님 `@yijun0330` | `services/analyzer/`, 합의된 합성 fixture·평가·실패 사례·E2E 재현 |

공유 Schema는 C가 원본 모델에서 생성하고 B가 체인 경계를 검토합니다. `Makefile`, lockfile, `.github/`, `infra/`, `scripts/`, 공유 문서는 작업마다 수정 담당자와 리뷰어를 정하며 C가 조율합니다. 타 담당 경로의 구현은 서면 handoff와 소유자 확인 또는 사용자의 명시적인 작업 지시 없이 수정하지 않습니다. B의 Contract와 Adapter도 각각 검증합니다. MVP의 M1~M4는 과거 기록의 역할명입니다.

## 5. 착수와 환경 확인

루트 지침 → `START_HERE.md` → 현재 작업 ID·계획서 관련 절 → 경로별 지침 → 관련 모델·API·ABI·ADR·fixture·테스트 순서로 읽습니다. Claude Code는 `CLAUDE.md`도 읽습니다. 수정 전에 현재 branch·SHA·사용자 변경, 적용 지침, 수정 경로, 선행 조건, 검증 명령을 보고합니다.

현재 단계 기준 SHA와 lockfile을 사용하고 작업 환경의 구조·환경·필요 smoke를 확인합니다. 환경 차이가 영향을 주는 검사만 차단하며 다른 팀원의 준비를 기다린다는 이유로 독립 구현 전체를 멈추지 않습니다. 초기 bootstrap과 MVP 통합은 완료된 과거 절차입니다. 통합·재현 시에는 같은 검증 SHA와 환경 fingerprint를 비교합니다.

## 6. 기술 결정과 공유 계약

v3.0에서 확정한 범위·정책은 재승인받지 않습니다. 범위 안의 함수명·내부 구조 등 일반 구현 선택은 담당자가 진행합니다. 소비자에게 영향을 주는 API·Schema·서명·ABI 변경은 원본과 예시, 버전·호환성·migration, 관련 소유자 리뷰를 함께 준비합니다. 이미 승인된 기능을 구현하기 위해 필요한 계약 초안·자체 테스트 작성은 진행할 수 있으며, 초안을 다른 팀원이 합의한 구현 계약으로 표현하지 않습니다.

Python 모델 원본은 `packages/python/originproof_core`입니다. JSON Schema·TypeScript·OpenAPI는 원본에서 생성하거나 해당 생성 경로와 일치시킵니다. 생성 파일을 손으로 수정하지 않습니다. 현재 v1 서명은 [서명 명세](docs/signing_spec.md), 새 두 유형의 정책·버전·상태·binding은 ADR을 따릅니다. 계획과 현재 구현이 다르면 변경 작업으로 기록하고 기존 동작을 조용히 바꾸지 않습니다.

## 7. 독립 개발과 의존 작업

기존 계약과 확정된 계획으로 자기 영역 구현·mock/합성 데이터 검사까지 진행합니다. 팀원의 실제 구현이 없으면 실제 연결과 그 완료 판정만 대기합니다. 공유 인터페이스가 새로 필요하면 소유자가 하나의 초안·예시·검사를 만들어 공유하고 관련 담당자가 검토합니다. 각 에이전트가 같은 경계를 서로 다르게 정의하지 않습니다.

`독립 구현·검사 완료`, `실제 연결 대기`, `연결 검증 완료`, `단계 완료`를 구분합니다. mock 통과는 실제 RPC·브라우저·원자적 consume 성공을 의미하지 않습니다. 미구현 동작을 성공 응답으로 대체하지 않습니다. 각 담당자가 자기 테스트를 작성하고 D가 독립 실패 사례·E2E·재현을 확인합니다.

사용자님의 W1~W7 개발 범위를 설명할 때 C 작업 ID별로 지금 구현 가능한 부분, 필요한 담당자·선행 작업 ID, 연결 후 완료할 부분을 제시합니다. A의 UI·D의 검증 등 단계 전체 의존성과 C 구현의 의존성을 구분합니다. 현재 코드·PR 근거 없이 선행 기능이 준비되었다고 말하지 않습니다.

## 8. 브랜치·공유·병합

기본 흐름은 `작업 branch → phase/Wn → integration`입니다. 작업은 최신 해당 phase에서 시작합니다. phase가 없으면 최신 integration에서 단계별 준비 branch로 독립 작업을 진행하고, phase 생성 후 최신 변경을 반영해 그 단계로 PR을 올립니다. 여러 단계는 각각 branch·PR·증거를 남깁니다. 계획·운영 문서 PR은 integration을 대상으로 할 수 있습니다.

작업 착수, 선행 PR 병합 통지 뒤, PR 제출 전에 `git fetch origin`으로 기준과 선행 PR 상태를 확인합니다. 네트워크 불가 시 마지막 확인 SHA에서 독립 부분을 진행하고 최신 연결 검증만 보류합니다. 다른 팀원의 branch를 임의로 checkout·merge·cherry-pick하지 않으며 자동 polling·병합이 실행되는 것으로 설명하지 않습니다.

다른 담당자가 기다리는 선행 계약·구현은 독립 검사를 마치면 자기 작업 branch에 push하고 URL·SHA·검사 범위·남은 결정을 인계 문서/PR에 기록합니다. 초안 공유는 계약 리뷰·단계 완료를 대신하지 않습니다. 요청 없이 팀원에게 별도 메시지를 보내지 않습니다.

모든 작업·리뷰·단계 검사를 마친 뒤 phase를 integration에 PR로 승격하고 최종 phase SHA를 보존합니다. 완료된 phase를 삭제·재사용·전진시키지 않습니다. integration에서 main으로의 통합 검증·PR은 사용자님의 명시 요청 뒤 지정된 한 명이 진행합니다. 공유 branch force push, 사용자 변경 reset, 무관한 수정은 금지합니다. main 직접 push는 해당 변경에 대한 사용자 명시 지시가 있을 때만 합니다. branch protection이 없는 경우에도 PR·리뷰 규칙을 지킵니다.

GitHub 작업은 `gh`를 우선합니다. sandbox 네트워크 오류만으로 인증 실패를 단정하지 말고 네트워크 허용으로 같은 명령을 재시도합니다. 토큰·타인의 인증정보는 공유하거나 기록하지 않습니다.

## 9. 인증·권한·키·개인정보

역할·기관·Proof 소유권·수신자는 서버에서 확인합니다. 브라우저가 보낸 역할/기관 ID를 신뢰하지 않습니다. Registry 운영키와 기관별 발행키를 분리하고 개인키·토큰·비밀번호·원문·전체 payload를 온체인·로그·공개 응답·Git에 넣지 않습니다. 제한 조회와 consume은 인증된 주체와 서명된 binding을 확인합니다.

정상 교체는 신규 발행 키를 전환하고, 유출 폐기는 기존 Proof에도 현재 사용 불가를 반영합니다. DB 승인이나 제출 hash만으로 체인 성공을 선언하지 않습니다. 결과 미확인 작업을 무조건 재전송하지 않습니다. 조회는 읽기 전용이고 1회 사용의 최종 권위는 체인입니다. P0 서버 대행 인증의 신뢰 범위는 ADR에 따라 명시합니다.

합성 기관·데이터만 사용합니다. `NOT_REGISTERED`를 가짜라고 하거나 법적 효력·완전한 사기 방지를 보장하지 않습니다. 업로드를 제공하는 경우 MIME·파일 signature·크기·페이지·보존 기간 검사는 필수입니다.

## 10. AI와 선택 입력 기능

기존 `LLMProvider`, `OpenAILLMProvider`, `MockLLMProvider`를 재사용합니다. 기본 provider는 mock, 모델은 `OPENAI_MODEL`의 `gpt-6-luna` 기본값이며 timeout·retry·reasoning 설정을 코드에 고정하지 않습니다. OpenAI Responses API와 Pydantic Structured Outputs를 사용합니다.

추출하지 못한 값은 null로 두고 refusal·incomplete·timeout·rate limit·Schema 오류를 명시합니다. AI는 진위·Registry 상태를 결정하지 않습니다. 원시 provider 응답·민감 입력을 로그에 남기지 않습니다. 유료 호출은 명시적인 live test 범위에서만 하고, P0의 ID 조회·필드 비교·발행은 AI 없이 동작해야 합니다.

## 11. 검사와 안정된 명령

현재 Makefile·package scripts의 명령을 사용합니다. `make bootstrap-check`, `make mvp-up`, `make demo-reset`, `make mvp-test`, `make lint`, `make typecheck`, `make test`, `make smoke`의 기존 이름을 유지합니다. API·코어·Contract·Adapter·웹별 명령과 한계는 계획서 15.9절을 따릅니다. 명령이 없거나 필요한 사례를 검사하지 않으면 정확히 보고하고 해당 담당 작업으로 보완합니다.

변경 영역의 정상·거부·실패·경계값을 검사하고 필요한 통합 검사를 수행합니다. mock·실제 PostgreSQL·로컬 EVM·브라우저 결과를 구분합니다. `make mvp-test`는 본선 전체 검증이 아니며 Python `make typecheck`는 현재 compileall, `make security`는 안내입니다. 문서만 바꾸면 링크·경로·명령·정책 일관성·diff를 검사하고 기능 검사를 실행한 것으로 보고하지 않습니다.

`make demo-reset`은 DB 볼륨을 지웁니다. 명시적으로 허용된 폐기 가능한 합성 환경에서만 실행합니다. 배포·migration·live 검사는 대상과 부작용을 확인합니다. 관련 검사가 통과한 후 새 변경·실패가 없으면 불필요하게 같은 검사를 반복하지 않습니다.

## 12. 작업 절차와 승인 경계

`기존 흐름 확인 → 최소 변경 → 필요한 검사 → diff 검토 → 문서·생성물 갱신 → 공유·보고`로 진행합니다. 보안·입력 검증·데이터 손실 방지는 줄이지 않습니다. 루틴한 수정과 이미 승인된 범위는 자율적으로 진행합니다.

승인 범위를 벗어난 파괴적 작업, 호환성을 깨는 새 정책, 새 의존성·최상위 경로, 운영 배포, 허용되지 않은 유료 호출·외부 게시에는 사전 확인이 필요합니다. 이미 받은 승인은 반복 요청하지 않습니다. 질문이 필요하면 근거 지침과 결정해야 할 구체적인 차이를 설명하고, 영향을 받지 않는 작업은 계속합니다. 기존 branch 공유·PR 절차는 8절을 따릅니다.

## 13. 완료와 단계 판정

자기 영역 수용 기준·검사·관련 생성물·보안 검토를 충족하고 실제 실행 SHA·환경·결과를 기록합니다. PR 완료에는 작성자 외 지정 리뷰어의 확인과 필요한 clean worktree/clone 재현이 포함됩니다. 리뷰를 받은 것으로 가정하지 않습니다.

실제 선행 구현과 연결해야 하는 기준은 연결 후에만 완료 처리합니다. 단계 완료는 모든 작업 ID, A~D 결과, 독립 검증, 필수 리뷰·CI·포트폴리오 기록을 확인한 뒤 판정합니다. 코드 작성·push·PR 생성만으로 단계를 완료 처리하지 않습니다.

## 14. 개인 기여와 포트폴리오

작업 PR마다 [PR 템플릿](.github/pull_request_template.md)과 [기여 기록 안내](docs/portfolio/README.md)를 적용합니다. 실제 담당자, 개인·재사용·협업 작업, 선택 이유, 실패 원인·해결, AI 활용과 사람의 판단, 검증 SHA·환경·결과·한계를 기록합니다. 기여 비율·수치·타인 승인·Git 작성자를 만들어내지 않습니다.

단계 마무리에 실제 작업한 `docs/portfolio/Wn-역할.md`를 갱신하고 단계 완료 PR에서 네 명의 기록을 연결합니다. 미래 성과는 미리 기록하지 않습니다. 동결 뒤 기록 보충은 integration에 반영하며 보존 phase를 수정하지 않습니다. 기록 작성은 외부 공개·메시지 발송 권한을 뜻하지 않습니다.

## 15. 인계와 최종 보고

작업 ID·담당자·branch/PR URL·기준 및 검증 SHA, 사용할 모델/API/ABI·예시, 정상·거부 기대값, 실제 검사 결과, 미완료와 다음 담당자를 제공합니다. 일정은 실제 합의가 있을 때만 기록하고 고정 주차 마감을 만들지 않습니다.

최종 보고는 변경 결과·근거, 실행/미실행 검사, 독립 구현과 연결 상태, 리뷰·기여 기록 누락을 구분합니다. 계획·정책 승인과 코드 리뷰를 구분하고, 사용자가 다시 승인할 필요 없는 기존 결정을 blocker로 나열하지 않습니다.
