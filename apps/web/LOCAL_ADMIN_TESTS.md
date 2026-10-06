# 관리자 화면에서 로컬 검사

사용자 요청(2026-10-03)에 따라 수동 협업 검사와 재실행 결과의 진입점은
`http://127.0.0.1:8768/admin.html`로 통일합니다. 기존 메인 화면으로 시작하는
macOS `.command` 실행 동선은 유지합니다. 별도 3103/3104 웹 테스트 서버는 사용하지 않습니다.

## 화면

- 기업 기능: 합성 기관 선택, 기관 상태, 키 관리, 발행, 발행 목록, 공개 ID QR, 작업 이력.
- 개인 기능: ID 조회, 내용 비교, 기존 AI 후보 필드 추출, 요청 사용 조건, 검증 내역.
- 기관 승인: 기존 운영자 API로 신청 결정·체인 활성화를 확인합니다.
- 검사 결과: 기존 PR #35/#36/#40·웹 연결 기록, W3 전체 검사, 명령·로그·개별 결과·코드 SHA·화면 식별값.

기존 BusinessWorkspace/UserWorkspace/SidebarNav를 재사용합니다. API가 없는 consume·폐기·
회원가입 기능을 성공 처리하지 않습니다. 유료 AI 호출은 실행하지 않습니다.

## 로컬 연결 조건

`test/local-console-server.py`는 127.0.0.1:8768에서만 실행하는 개발용 도구입니다.
실제 API는 127.0.0.1:8770에 있어야 합니다. 별도 배포/공개 호스팅에 포함하지 않습니다.
운영자 인증을 먼저 확인한 뒤 `/test-api/bank`, `/test-api/office`, `/test-api/recipient`를
실제 합성 계정으로 연결합니다. 운영자 쿠키를 기업/개인 쿠키로 교체하지 않습니다.
다른 기관·수신자 권한은 기존 서버에서 검사합니다. 운영자 로그아웃은 `/api`를 사용합니다.

계정 파일은 로컬 `~/.local/share/originproof-web-test/accounts.json`에만 둡니다.
비밀번호·쿠키·개인키를 코드, 저장소, 검사 결과에 넣지 않습니다.
서버 실행 시 `ORIGINPROOF_CONSOLE_ROOT`를 기존 로컬 웹 폴더,
`ORIGINPROOF_WEB_SOURCE`를 현재 `apps/web` checkout 경로로 지정합니다.
기존 로컬 `collaboration-server.py`는 이 서버를 실행하는 wrapper로 연결했습니다.

변경 후 `pnpm --filter originproof-demo-web build`를 실행하고 관리자/기업/개인 bundle과
관련 수정 파일을 로컬 웹 폴더에 반영한 뒤 관리자 검사 버튼을 실행합니다.
기존 랜딩 디자인을 덮어쓰지 않습니다. `/mvp`, `/finals`, `/finals/keys` 회귀검사는
동일한 8768 서버에서 Next production build의 정적 페이지/청크를 제공합니다.
새 웹 서버나 별도 테스트 진입 페이지는 필요하지 않습니다.

W3 검사 버튼은 lint → typecheck → 컴포넌트 → Playwright 순으로 실행합니다.
브라우저 검사는 8768의 배포된 화면을 대상으로 합니다. 검사 시작 시 HEAD와 로컬 수정 여부,
배포 화면 fingerprint를 기록합니다. 수정 상태를 clean SHA 검증이라고 표시하지 않습니다.

## 이번 재검증 범위

- 컴포넌트: 18개.
- 브라우저: 13개(실제 두 기관 발행·QR·수신자 비교·변조·기관 격리 포함).
- 관리자: 두 기관 전환, 실제 발행/QR, 개인 조회/내용 비교/변조, 운영자 세션 보존,
  비로그인 test proxy 거부, 승인/검사 메뉴, 사이드바 접기·모바일.
- 과거 고정 SHA 재검사: #35 26 passed/4 skipped, #36 33 passed,
  #40 78 passed/1 skipped, 웹 연결 14 passed.

#35/#40의 skip 및 mock 경계는 그대로 보존합니다. 과거 고정 SHA 검사 결과가
최신 팀원 구현 전체의 통합 성공을 의미하지 않습니다. W3 QR 문서에 남긴 3103/3104 검사는
당시 실행 기록이며, 현재 로컬 재검사는 위 8768 관리자 화면에서 진행합니다.

## 최신 관리자 기능 연결 (2026-10-03)

`codex/admin-latest-functions`, 시작 웹 SHA `5cd16fc5f6bc4145ca21737e76de5f3014251609`.
관리자에만 `lifecycleEnabled`를 전달합니다. 일반 기업·개인 화면의 활성화는 후속 이식입니다.
GitHub C #38 `3ef1fd40943914c1450e8bc05047119ab7eabbc0`의 실제 API/Adapter/계약과
lockfile을 재사용하며, 해당 PR/단계가 승인·완료되었다고 판정하지 않습니다.
새 프레임워크·의존성·팀원 API 구현을 추가하지 않았습니다.

- 관리자 화면: 기관 신청·승인·활성화, 기관 중지/재활성화/폐기, 키 등록/교체/폐기,
  두 유형 Proof 발행/등록/조회/비교/폐기, 지정 수신자 1회 사용, Operation 조회/복구,
  체인 동기화와 DB/현재 체인 등록 일치 조회.
- 관리자 QR: `admin.html?proof_id=...`로 같은 합성 환경을 조회합니다. 관리자 인증이
  필요하며 공개 사용자 QR라고 표시하지 않습니다. 일반 페이지의 공개 QR는 유지합니다.
- AI: Git에 구현된 카드 알림 후보 추출만 mock Analyzer에 연결했습니다.
  PAYMENT_REQUEST/OFFICIAL_DOCUMENT 추출 API 및 유료 provider live 검사는 미제공/미실행입니다.
- API 모델에서 `scripts/generate_api_contracts.py`로 생성한 타입을 웹에 복사했습니다.

### 환경과 시작

기존 8768 웹·8770 로그인/일반 페이지는 유지합니다. 관리자 proxy만 8780으로 연결합니다.
`test/admin-runtime.py`는 독립 합성 PostgreSQL 55434, Anvil 18546(1초 채굴),
최신 API 8780, 기존 mock Analyzer 8781을 실행합니다. 새 등록 검사를 위해 배포 스크립트의
Bank 사전 seed만 임시 제외하고 동일 계약과 역할을 배포하며 원본 스크립트를 복원합니다.
이 배포 방식은 원래 seed 배포의 검증 결과와 구분합니다. DB를 reset하지 않습니다.
보호된 계정·signer·체인 상태는 `~/.local/share/originproof-admin-test`에 보존됩니다.
실행 당시 환경: Python 3.13, Node 26, pnpm 11.19, PostgreSQL 16.4, Foundry 1.4.4.

기존 macOS 시작 `.command`의 `local-runtime.py`는 8780이 준비되지 않으면 이 runtime을
추가로 실행하도록 연결했습니다. 웹 진입점은 여전히 `index.html`입니다.
운영자 역할 검사는 기존 8770 세션을 사용하고 실제 테스트 역할은 8780이 확인합니다.
테스트 역할 비밀번호·쿠키·개인키는 브라우저 응답이나 Git에 포함하지 않습니다.
모든 proxy는 loopback Host·운영자 세션·변경 Origin·본문 크기를 검사합니다.

### 실행 명령과 결과 보관

관리자 → 검사 결과 → 관리자 기능 검사는 `test/admin-lifecycle-check.py`를 실행합니다.
이 검사는 동일 8768 proxy를 통해 요청하며 합성 발행·키 교체·폐기·기관 상태 변경을 수행합니다.
명시된 독립 합성 Anvil에서만 채굴을 잠시 멈추어 미확정 receipt의 같은 tx 복구를 확인하고
finally에서 채굴을 복원합니다. 운영 환경에서 실행하는 검사가 아닙니다.
PR #38 검사 버튼은 고정 SHA의 API/Adapter/Analyzer 회귀 검사를 별도로 실행합니다.
최종 개별 결과·skip·시간·SHA는 `collaboration-results.json`에 기록되어 관리자에서 조회합니다.

초기 실패: demo seed로 Bank 중복 등록(CHAIN_REVERTED), 재시작 뒤 Anvil 시각 지연
(ProofExpired)을 발견했습니다. 사전 seed 제외와 시작 시각/주기 채굴로 합성 환경을 고쳤습니다.
HTTP 404의 권한 보호, REPLAY_DETECTED 409, PROOF_REVOKED enum은 실제 API 계약에 맞춰
검사 기대값을 수정했습니다. 이를 제품 코드 오류 수정이나 fake success로 표현하지 않습니다.

연속 채굴 중 API가 서로 다른 블록 snapshot을 관측하면 fail-closed로
INCONCLUSIVE + DEPENDENCY_UNAVAILABLE를 반환합니다. 관리자만 읽기 전용 verify를
최대 4회 재조회하며 지속 실패와 TAMPERED는 성공으로 바꾸지 않습니다.
실제 검사도 이 조건의 읽기만 다시 확인합니다. 변경 요청은 재전송하지 않습니다.
회귀 검사와 동시에 많은 요청을 보낸 초기 실행에서는 RATE_LIMITED(429)를 확인했습니다.
정책을 완화하지 않고 실제 기능 검사를 순차·간격을 두고 실행하도록 조정했습니다.

### 이번 최종 검사 결과

| 검사 | 결과 | 경계 |
| --- | --- | --- |
| 최신 #38 API/Adapter/Analyzer 회귀 | 404 passed / 6 skipped | mock 및 독립 단위 검사 포함; skip은 실제 연결 성공이 아님 |
| 관리자 실제 기능 연결 | 19 passed | 동일 8768 proxy → 실제 PostgreSQL/Anvil; 같은 tx 복구 포함; AI만 mock |
| 웹 컴포넌트 | 22 passed | 읽기 재시도·지속 불확실·변조·HTTP 실패 4개 추가 |
| 8768 웹 브라우저 | 13 passed | 실제 관리자 1회 사용·AI 버튼, 일반 페이지·QR·MVP 기존 회귀 |
| lint / typecheck / build / Python compile / diff | 통과 | 새 의존성 없음; 기존 npm audit 4 high는 이번 변경의 신규 의존성이 아님 |

기관 영구 폐기는 UI 연결 및 저장소 회귀 검사에 포함되지만, 두 수동 테스트 기관을
계속 사용할 수 있도록 이번 실제 8768 시나리오에서 영구 폐기하지 않았습니다.
공개 회원가입, 신규 두 유형 AI 추출, 유료 AI live, 외부 체인/운영 배포,
작성자 외 리뷰·D 독립 재현 및 개인/기업 페이지 이식은 완료로 판정하지 않습니다.
위 검사들은 변경된 로컬 웹 내용을 대상으로 했고, 관리자 W3 재실행 기록은 현재 Git HEAD와
웹 fingerprint를 별도로 저장합니다. 팀 전체 W4/W5/W6 완료를 의미하지 않습니다.

## 2026-10-04 오류 복구와 기업·개인 이식

사용자 요청으로 관리자 검증 후 일반 기업·개인 화면에도 lifecycleEnabled를 전달했습니다.
기업: 키 생성/교체/폐기, Proof 발행/등록/폐기, 허가된 사용, Operation 조회/같은 거래 복구.
개인: ID 조회/내용 비교, 지정 수신자 1회 사용, 미확인 거래 조회/복구.
관리자 전용 기관 운영 권한이나 합성 역할 전환은 일반 페이지에 노출하지 않습니다.
일반 QR는 기존 공개 ID 링크이며 관리자 QR는 별도 관리자 조회 링크를 유지합니다.

8768 `/api`와 관리자 역할 proxy는 동일 C #38 고정 SHA의 8780 API를 사용합니다.
이전 8770의 데이터는 삭제하지 않았으며, 과거 일반 페이지에서 발행한 ID는 이전 환경 기록입니다.
기관/계정 ID를 보존하고 로컬 보호된 기존 테스트 계정의 로그인 정보를 8780 합성 DB에 반영했습니다.
역할·기관 불일치가 있으면 seed를 거부합니다. 브라우저 역할 값으로 권한을 부여하지 않습니다.

오류 원인/수정:
- 전체 과거 storage snapshot의 반복 dump가 RPC를 5초 넘게 막아 Reader ReadTimeout/503을 만들었습니다.
  현재 storage·블록 정체성·receipt를 60초마다 atomic 저장합니다. 원래 역사/손상 파일은 보존합니다.
- Anvil interval 설정은 automine을 끕니다. interval 0을 먼저 지정하고 automine true를 나중에 지정합니다.
  빈 블록 무한 채굴을 제거하고 쓰기를 즉시 채굴합니다. UNKNOWN 시에는 새 요청 대신 기존 tx를 복구합니다.
- API/Analyzer를 다시 시작하고 health ready/live를 확인했습니다.
- 관리자 권한 확인은 매 요청 실행하며 요청 제한을 줄이지 않습니다. 기능 검사는 1.2초 간격,
  관리자 실제 변경 검사와 브라우저 검사는 같은 합성 환경에서 순차 실행합니다.
- `.command` 시작은 index.html을 유지하고 API 또는 mock Analyzer가 없으면 최신 runtime을 기동합니다.

재시작 후 관리자 실제 검사 19 passed(2026-10-04T08:05:48Z), 컴포넌트 22 passed,
checkpoint/채굴 복원 순서 unittest 2 passed, lint/typecheck/build 통과.
기업/개인 브라우저 최종 결과는 아래에 기록합니다.
현재 상태 checkpoint는 전체 과거 블록 storage replay를 보장하지 않으며 W5 D 장애 검사를 대신하지 않습니다.
공개 회원가입·새 두 유형 AI 추출 API·운영 배포·D 독립 재현/PR 승인은 이번 완료 범위가 아닙니다.

### 이식 후 최종 확인 (2026-10-04)

- 기존 8768 관리자 화면 → 실제 PostgreSQL/로컬 Anvil 기능 검사: 19 passed (AI 후보 추출만 mock).
- 기업·개인·관리자 브라우저: 최종 15개 사례 통과. 전체 실행은 13 passed/2 failed였고,
  지급 요청 탭의 아이콘을 포함한 접근성 이름과 이력 목록 선택자를 수정한 2개 재검사는 2 passed였습니다.
  단일 실행에서 15개 모두 통과했다고 기록하지 않습니다. 실제 API 연결 5개, 나머지는 디자인/합성 API 회귀입니다.
- 기업 실제 발행·공개 QR 디코딩·타 기관 내용 조회 거부·키 교체/이전 키 유지·작업 이력 확인,
  개인 정상 비교·변조·1회 사용 및 재조회, 문서 폐기의 개인 화면 반영을 확인했습니다.
- 컴포넌트 23 passed; 런타임/채굴 복원/운영자 권한/429 구분 unittest 5 passed.
- lint/typecheck/운영용 build/Python compile/diff 확인 통과.
  임시 Next 생성물의 중복 `* 2.ts`로 발생한 타입 오류는 해당 생성 캐시만 제거해 해결했습니다.
- 관리자 권한 확인에서 API 429/503을 403으로 오인하지 않습니다. 요청을 자동 재전송하지 않습니다.
  관리자 결과 polling은 10초 간격이며 실제 변경 suite와 브라우저 suite는 동시에 시작하지 않습니다.
- 기존 `.command`는 index.html 시작을 유지하며 준비 검사는 현재 API의 18546 체인을 확인합니다.
- 실행 웹: 576832905cb50e8e29873a89d891f48706ea8f2d + 로컬 변경.
  API: C #38 3ef1fd40943914c1450e8bc05047119ab7eabbc0.
  결과와 웹 fingerprint는 기존 관리자 `검사 결과`에 저장했습니다.
  최초 브라우저 실패 원본은 `/tmp/originproof-web-full-final-attempt.xml`,
  재검사 원본은 `/tmp/originproof-web-final-rerun.xml`입니다.

새 PR/push/리뷰 승인/운영 배포는 하지 않았습니다. W4의 담당 웹 연결 후속은 구현·로컬 검사 완료이며,
phase PR·작성자 외 리뷰·D 독립 재현·팀 전체 단계 완료는 별도입니다.
이전 8770 DB/18545 체인 데이터는 보존합니다. 현재 `/api`의 과거 ID 조회는 8780 환경에 저장된 기록을 사용합니다.
공개 회원가입, 지급 요청/공식 문서 AI 추출, 외부 운영 배포는 서버 계약/별도 수용 기준 대기입니다.

## W5 추가 재현 (2026-10-06)

[W5 검사와 잔여 실패](W5_UI_VALIDATION.md), [SHA·환경 요약](test/evidence/w5-20261006.json).
기존 `http://127.0.0.1:8768/admin.html`을 그대로 사용합니다.
`test/run-w5-admin.py`는 frozen C #38 API와 D disposable fixture를 읽기 전용 재사용하며
계정만 seed합니다. browser request forwarding은 실제 별도 API의 응답을 전달하며
신청·승인·키·Proof 성공을 mock하지 않습니다. 운영자/기업/수신자 계정 비밀은 공개 trace에 넣지 않습니다.
기존 수동 테스트 데이터는 지우지 않고 helper가 만든 PG/Anvil/network만 정리합니다.

재현 전 해당 Git 객체(C `3ef1fd4`, D `a3f55c6`, W4 QA `0bb5da4`, prep `78cce40`)를 fetch하고
C lockfile로 설치한 Python 환경(pytest/uvicorn/httpx 포함)을 사용합니다. root는 pnpm lock 기반입니다.
새 clone은 `pnpm install --frozen-lockfile --ignore-scripts`, official은 `npm --prefix apps/web/official ci --ignore-scripts` 후 빌드합니다.
8768에 현재 admin bundle이 제공돼야 합니다. 임시 clone이 `/private/tmp`에 있으면
Colima 공유 폴더의 절대 경로를 W5_ADMIN_OUTPUT_DIR로 지정해야 합니다. 배포 manifest 누락은 즉시 실패합니다.

```sh
W5_ADMIN_QA=1 W5_ADMIN_OUTPUT_DIR=/path/to/docker-shared/evidence /path/to/c-lock-venv/bin/python apps/web/test/run-w5-admin.py
W5_D_API_QA=1 W5_D_MIXED_STACK_QA=1 /path/to/c-lock-venv/bin/python apps/web/test/run-w5-api.py
# fresh API 검사는 W5_D_MIXED_STACK_QA를 지정하지 않습니다.
cd apps/web
ORIGINPROOF_TEST_ACCOUNTS=/path/to/private/accounts.json ORIGINPROOF_WEB_BASE_URL=http://127.0.0.1:8768 ./node_modules/.bin/playwright test e2e/w5-admin-accessibility.spec.ts --workers=1
```

두 Python 진입점은 A의 재실행이며 D 독립 승인과 별개입니다. API wrapper는 D SHA 전체를
자신의 build 아래에 읽기 전용 export하고 C baseline uv.lock을 명시합니다. QA 원본·생성물을
팀원 branch에서 바꾸지 않습니다. 요약의 product/QA SHA와 실제 A 실행 환경을 함께 기록합니다.
W5 mixed 마지막 G07 실패를 성공으로 표시하지 않으며 원시 private evidence와 비밀 없는 요약을 구분합니다.
