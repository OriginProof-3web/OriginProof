# W3 A 검사 기록

## 2026-10-03 PR #44 CI 보완 재현

- 검사 소스: `f875958` (최신 `phase/W3@9047163`을 반영한 `de9432d` + CI 보완).
- 사용자 요청에 따라 C 계정의 Codex가 기존 웹 PR의 머지 준비를 보완했습니다.
- 최초 CI 실패는 `#quick-nav summary`의 click 30초 timeout입니다. 현재 로컬에서는
  보완 전 같은 테스트도 1 passed/12.3초로 통과하여, 제품 메뉴 오류나 GPU 성능 문제로
  원인을 확정하지 않았습니다.
- 기존 실제 QA의 production/reduced motion 조건을 CI 기능 검사에도 적용했습니다.
  CI는 사전 build의 `pnpm start`, 로컬 기본은 기존 dev를 사용합니다. timeout 증가,
  force click, 검사 skip, 제품 WebGL/원본 디자인 변경은 하지 않았습니다.
- 390px 메뉴의 Enter 열기, Escape 닫기·summary 포커스 복귀, 실제 로그인 링크 이동을
  추가 검사합니다. 마우스 클릭·익명 조회·사이드바·MVP 접근성 회귀도 유지합니다.
- 환경: macOS, Node 22.14.0, pnpm 11.25.0, 기존 lockfile/Next 15.5.3/Playwright 1.55.0.
  GitHub CI의 Node 22.18.0/pnpm 11.19.0 결과는 PR check에서 별도로 확인합니다.

| 이번 실행 | 결과 |
| --- | --- |
| 웹 lint/typecheck/build | 통과 |
| component | 15 passed |
| production E2E 전체 | 9 passed/2 live skipped, 6.4초 |
| `f875958` clean git archive + frozen offline install + 새 production build/E2E | build 통과, E2E 9 passed/2 live skipped |
| Python API/core/analyzer/indexer | 318 passed/5 opt-in skipped |
| 현재 W3 생성 원본과 웹 생성 타입 snapshot 2개 비교 | byte 일치 |
| lockfile/원본 디자인·WebGL/diff | lockfile·제품 디자인 변경 없음, diff check 통과 |

기본 E2E에서 제외한 2개는 합성 계정 파일을 명시해야 실행하는 실제 API 검사입니다.
이번에는 현재 통합 SHA의 실제 DB/RPC/API 브라우저, 휴대폰 LAN/QR, D 독립 실제 재현과
W4 화면을 실행·완료했다고 기록하지 않습니다. 기능 E2E는 reduced motion 조건이며
일반 애니메이션 성능 검사를 대체하지 않습니다. 아래는 최초 제출 당시 증거입니다.

- 기록 시각: 2026-10-02T21:32:29+09:00
- 기준 SHA: `1f8ed632ea9c74091abaf2fe2ec32882038f731f` (`phase/W3`). 검사 대상은 이 SHA에 미커밋 웹 변경을 더한 작업 트리입니다.
- 브랜치: `codex/w3-a-official-web`; push/PR 미실행.
- 소스 fingerprint SHA-256: `1af601d528242259560ff6766a2f7fe2786e7ada130a399e4f936f71c36851a6`. official 원본(의존성 설치 폴더 제외), app TSX, e2e TS 및 웹 설정 파일을 경로 정렬 후 `경로 + NUL + 파일 bytes + NUL`로 계산했습니다.
- 환경: macOS, Node v26.0.0, pnpm 11.19.0, Next 15.5.3, Chromium Playwright 1.55.0.
- API: C #36 `85e152cd5550f24874abb267122a5d8ece29e3b9` / PostgreSQL 16.4 / Anvil chain 31337, 기존 폐기 가능한 합성 환경. 이번 변경에서 reset/migration/재배포는 하지 않았습니다.

| 명령·사례 | 최종 결과 | 범위 |
| --- | --- | --- |
| `pnpm --filter originproof-demo-web lint` | 통과, 오류·경고 없음 | 원본 화면 및 새 코드 |
| `pnpm --filter originproof-demo-web typecheck` | 통과 | 생성 타입·React 입력·기존 화면 |
| `pnpm --filter originproof-demo-web test` | 15 passed | 기존 8개 + 새 7개; 필수 입력·정수·422 매핑·링크 공개성·중복 클릭/ID 재사용·조회 범위 |
| `pnpm --filter originproof-demo-web build` | 통과 | 공식 assets 및 Next production build; 기존 styles.css의 autoprefixer `end` 경고는 남음 |
| `ORIGINPROOF_TEST_ACCOUNTS=… pnpm --filter originproof-demo-web test:e2e` | 10 passed / skip 0 / 8.0s | production Next; 8개 화면/mock·회귀 + 2개 실제 API 검사 |
| 실제 PAYMENT_REQUEST | 통과 | 새 발행·공개 PROOF_ONLY·지정 recipient FULL_COMPARISON 정상, 금액 변조 AMOUNT_MISMATCH |
| 실제 OFFICIAL_DOCUMENT | 통과 | 새 발행·공개 조회·정상 비교, 문서번호 변조 FIELD_MISMATCH |
| 실제 기관 분리 | 두 유형 통과 | 다른 기관 목록에 ID 없음, 제한 content 404 |
| 모바일/사이드바 | 통과 | 390px viewport overflow 없음, 접힌 sidebar 폭 <100px, 상단 메뉴·공개 조회 |
| 원본 보존 byte 비교 | 통과 | index.html·beyond-horizon.js·SidebarNav.tsx·foundation.css 동일 |
| 생성 타입 byte 비교 | 통과 | C #35 고정 SHA의 api.ts/originproof.ts와 동일 |
| `git diff --check` | 통과 | whitespace |

## 실패와 수정

- React 원본을 독립 npm 패키지로 보존하면서 컴포넌트 검사에서 React가 두 번 로드되어
  invalid hook call이 발생했습니다. Vitest resolve.dedupe로 검사 renderer와 같은 React를 사용했습니다.
- 처음 422 필드 검사에서 오류 문구가 label 이름에 포함되어 exact 조회가 실패했습니다.
  발행 입력에 고정 aria-label을 제공하고 aria-describedby로 오류를 연결했습니다.
- 일부 live 검사에서 로그인 입력 중 30초 timeout이 발생했습니다. 개발 서버와 빌드를 동시에
  사용한 검사 시도는 최종 증거로 쓰지 않았습니다. production 서버로 전환하고 기능 검사
  browser context의 reducedMotion을 reduce로 설정한 최종 전체 실행에서 10개가 통과했습니다.
  timeout 원인을 모두 확정한 것은 아니며 애니메이션 성능 개선/측정 결과로 주장하지 않습니다.

## 한계·미실행

- live 검사는 animation을 줄인 합성 브라우저 환경입니다. 원본 WebGL/휠/hover 디자인 코드는
  그대로 보존했습니다. 실제 사용자의 모든 GPU 환경·애니메이션 성능을 검증한 결과가 아닙니다.
- QR 생성은 새 의존성 추가에 대한 사용자 확인 대기입니다. QR decode·휴대폰 LAN 스캔 미실행.
- C #35/#36, B #40은 미병합 PR입니다. phase의 실제 통합 결과·D 독립 clean 재현·작성자 외
  리뷰·CI 성공을 대체하지 않습니다.
- AI 추출 provider, Proof 폐기·consume, 공개 가입은 W3 P0 완료 근거에 포함하지 않습니다.

## PR 제출 전 clean archive 재현

- 사용자님이 2026-10-02 PR 제출을 요청한 뒤 커밋 `52e794c`를 git archive로 별도 디렉터리에 추출했습니다.
- 루트 `pnpm install --frozen-lockfile` 후 웹 lint·typecheck·component(15 passed)·production build가 모두 통과했습니다. 기존 autoprefixer end 경고는 유지됩니다.
- 이 커밋은 앞선 웹 검사 이후 문서·추가 검사 증거·공백 정리만 포함합니다. clean archive 브라우저 재실행은 하지 않았고, 실제 웹 browser 10 passed 증거는 앞선 기존 작업 트리/production 서버 검사입니다.
- 커밋 이후 추가된 이 절은 기록만 변경합니다. 작성자 외 리뷰와 CI는 제출 후 확인 대상입니다.
