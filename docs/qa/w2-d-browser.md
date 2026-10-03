# W2-D2 — 실제 브라우저 연결 검사와 미완료 재현

- 담당: D / 여인준님 `@yijun0330`, 2026-10-03 (Asia/Seoul).
- 요청: W2 남은 일 3번 — 실제 브라우저, 새 세션, 권한·실패 및 별도 환경 재현.
- 제품 기준: `phase/W2@6f508fe6ae5ce106999c171e8205978dd2201333`.
- 검사 코드: `a66ac7205119369774c62466ae0ea4d3c5259aff`; 후속 변경은 보고 문서·이미지입니다.
- 검토 초안: [PR #51](https://github.com/OriginProof-3web/OriginProof/pull/51), C 리뷰 요청; 전체 수용 조건 미충족으로 Draft입니다.
- 상태: **연결 기능 6 passed / W2 수용 조건 6 failed / 0 skipped**. 전체 D2·W2는 미완료입니다.

## 실행 환경과 범위

[준비 도구](../../fixtures/finals/prepare_w2_browser_qa.py)는 병합된 PR #45의 실제
PostgreSQL·Anvil·uvicorn fixture를 재사용합니다. 새 tmpfs DB, 전용 network·Anvil,
새 서명기·합성 계정, 별도 loopback 포트의 production Next를 준비했습니다.
[브라우저 검사](../../fixtures/finals/w2_browser_qa.spec.ts)는 `page.route` mock이나
APIRequestContext를 쓰지 않고 실제 버튼이 보낸 HTTP 응답을 관찰합니다.

키 목록/상태/작업 조회를 확인하기 위한 별도 기관은 준비 단계에서 API로 승인·활성화하고
키를 등록했습니다. UNKNOWN 작업도 실제 Anvil 제출 후 RPC 응답 유실로 만들었습니다.
**이 준비는 웹 활성화·키 등록 성공의 증거가 아닙니다.** 새 두 기관의 신청·승인/반려는
브라우저에서 직접 수행했고, 활성화·등록·폐기를 API 호출로 대신하여 전체 UI 성공으로
처리하지 않았습니다.

Node 22.18.0, Python 3.13.7, pnpm 11.19.0, Playwright 1.55.0,
PostgreSQL 16.15 (`postgres:16-alpine`), 고정 Foundry/Anvil 1.4.4, chain ID 31337입니다.
PG 버전은 이전 D 보고의 16.4와 다릅니다. 실제 이미지 ID·RPC·주소·deployment ID·배포 SHA는
[환경·배포 기록](w2-d-browser-environment.json)에 있습니다. 호스트 forge는 사용하지 않았습니다.

## 연결 기능 — 실제 브라우저 6 passed

| 사례 | 관찰한 실제 결과 |
| --- | --- |
| 새 기관 신청 → 운영자 승인 | POST 201/200, APPROVED_PENDING_CHAIN; issuer 새로고침·새 context 로그인·reload에서 동일 신청 유지, logout 뒤 정보 미표시 |
| 다른 새 기관 신청 → 운영자 반려 | POST 201/200, REJECTED; 새 세션·reload에서 결정 유지, logout 뒤 정보 미표시 |
| CONFIRMED 작업·자기 기관 감사 조회 | 실제 GET 200, 등록 tx hash·CONFIRMED 표시; 감사 결과의 issuer_id가 자기 기관으로 제한됨 |
| 실제 UNKNOWN 작업 조회 | GET 200/UNKNOWN, 결과 확인 필요 표시, 체인 확인 완료로 표시하지 않음 |
| 타 기관 작업 ID 조회 | 실제 GET 404, 조회 권한 오류 표시, 타 기관 작업 내용 미표시 |
| 익명·운영자·수신자의 키 화면 | 익명 auth/me 401, 로그인 필요; 다른 역할은 issuer-only 안내, 변경 버튼 미제공 |

실제 DB에서도 두 브라우저 신청의 APPROVED_PENDING_CHAIN/REJECTED를 확인했습니다.
등록 Operation 3건은 전부 준비 단계에서 만든 요청이며, 브라우저의 날짜 입력 확인은
새 등록 Operation이나 체인 변경을 만들지 않았습니다.

## W2 수용 조건 — 실제 브라우저 6 failed

| ID · 담당 | 기대값 | 재현된 결과·원인 |
| --- | --- | --- |
| W2-A1 · A | 승인 뒤 웹에서 체인 활성화 가능 | 승인 대기 행에 활성화 버튼 없음; 전체 신청→체인 흐름 진행 불가 |
| W2-A2 · A | 자기 기관 키 목록 GET·표시 | 키 화면은 auth/me만 호출, GET /v1/issuer/keys 요청 없음 |
| W2-A2 · A | 유효 기간 입력 뒤 실제 키 등록 POST | 입력 조건 확인만 수행, POST /v1/issuer/keys 요청 없음 |
| W2-A2 · A | 등록된 키 폐기 버튼·확정 재조회 | 폐기 버튼 없음; 실제 폐기→새 세션 키 재조회는 NOT_RUN |
| W2-A1 · A | 실제 ACTIVE 상태를 명확히 표시 | API는 ACTIVE를 반환하지만 화면은 상태 확인 필요로 표시 |
| W2-A1/F15 · A | 올바른 definition-list 구조 | axe `definition-list` 실패; `<dl>` 직접 자식 `<p>`가 남음 |

누락 기능을 expected failure/skip으로 바꾸지 않았습니다. `acceptance-gaps` 프로젝트의
ordinary failure이므로 전체 Playwright/runner exit code는 **1**입니다. 이 6건은 현재
기능·접근성 미충족을 재현하는 검사이며, 전체 활성화→등록→폐기 E2E를 실행한 6건이라는
뜻이 아닙니다. A 연결 뒤 실제 변경·확정·새 세션까지 동선을 확장해야 합니다.

- [실제 키 등록 요청 미전송 화면](../portfolio/assets/W2/browser-key-registration-not-submitted.png)
- [ACTIVE 응답과 다른 화면 표시](../portfolio/assets/W2/browser-active-status-unknown.png)

## 검사·별도 환경 재현

| 실행 | 실제 결과 |
| --- | --- |
| 준비 도구 + 연결/수용 Chromium 12건 | 6 passed / 6 failed / 0 skipped, 27.17초; DB 관찰 일치 |
| 동일 a66ac72의 새 clone + 새 DB/Anvil/API/production 웹 | 동일 6 passed / 6 failed / 0 skipped, 27.08초; 새 deployment ID, DB 관찰 일치 |
| PR #45 장애·재시작 opt-in 재실행 | 3 passed, 25.53초; wrapper 안 C live 3건/B local-EVM 1건 포함, 중복 합산하지 않음 |
| `make test` | 171 passed / 6 live opt-in skipped, 기존 anyio deprecation warning 1개 |
| 웹 component | 8 passed |
| `make test-contracts` (별도 Compose 프로젝트) | 공식 Foundry 컨테이너 10 passed / 0 failed / 0 skipped, fuzz 512회; 이번 network 정리 |
| `make bootstrap-check`, `make lint`, `make typecheck`, fixture Ruff | 통과; Python typecheck는 compileall |
| production 웹 build | 두 clone에서 각각 통과; 각 실행 API origin으로 빌드 |
| `make env-fingerprint`, diff·문서 링크 | 확인; Git 코드 SHA와 환경·컨테이너 설정·lockfile 해시 기록 |

재현은 같은 Mac의 독립 clone·새 컨테이너 환경입니다. 동일 frozen Node 의존성·다운로드
cache·배포 이미지를 재사용했고 Python 환경·DB·체인·production build는 독립적으로 만들었습니다.
다른 물리 컴퓨터에서 실행한 것으로 표현하지 않습니다. 기본 회귀의 live skip은 위 opt-in
실제 실행과 구분했습니다. RPC 장애·중복·API/Anvil 재시작 결과는 API/체인 검사이며,
누락된 웹 변경 동선의 장애 처리까지 완료한 것으로 확대하지 않습니다.

처음 실행은 Playwright grep이 전체 제목의 시작을 가정하여 No tests found가 발생했습니다.
패턴을 고치고 DB 관찰을 실패 진단에도 남기도록 보완한 뒤 새 스택에서 12건을 실행했습니다.
첫 실행 자료는 로컬 ignored build에 보존했습니다. Xcode 전체 라이선스 요청은
DEVELOPER_DIR의 기존 Command Line Tools를 사용해 해결했으며 라이선스를 대신 승인하지 않았습니다.

## 재현 명령

개인 설정·기존 generated 파일이 없는 새 clone에서 실행합니다. 기존 `.env`가 있으면
덮어쓰지 말고 별도 clone을 사용합니다. runner는 기존 출력 디렉터리도 덮어쓰지 않습니다.

```sh
UV_PROJECT_ENVIRONMENT=.uv-venv uv sync --all-packages --all-groups --frozen
pnpm install --frozen-lockfile
test ! -e .env && (umask 077; set -C; printf 'LLM_PROVIDER=mock\nOPENAI_MODEL=gpt-6-luna\n' > .env)
docker build -f infra/docker/deployer.Dockerfile -t originproof-w2-recovery-deployer .
PYTHONPATH=apps/api/src:packages/python:services/analyzer/src:services/indexer/src \
W2_BROWSER_QA=1 .uv-venv/bin/python fixtures/finals/prepare_w2_browser_qa.py
```

실제 실행에서 Node 22.18.0을 PATH 앞에 지정했고 macOS의 기존 Command Line Tools를
DEVELOPER_DIR로 선택했습니다. runner가 만들었던 API/웹·DB/Anvil/network는 두 실행 모두
정리했습니다. 개인 `.env`·기존 DB/Compose·원래 미커밋 저장소는 유지했으며 제품 소스·공유
모델·Golden·lockfile·Graphify 그래프·Serena 메모리는 변경하지 않았습니다.
계정 암호·서명기는 ignored private build에만 있고 공개 기록에는 넣지 않았습니다.
운영 배포·유료 모델 호출·기존 DB 초기화는 수행하지 않았습니다.

## 다음 담당

- **A:** 위 A1/A2 기능 연결, 생성 타입·현재 상태 표시, W1 접근성 수정 반영.
- **D:** 연결된 W2 SHA에서 실제 활성화→키 등록→폐기→새 세션·실패 흐름 재검증.
- **C:** 이 D QA 변경 리뷰, A 연결 변경 통합 및 최신 결과·기여 기록을 모아 단계 판정.

PR #45는 C 승인 후 이미 병합됐습니다. 과거 보고의 리뷰 대기와 새 QA의 리뷰 대기를
구분합니다. 이번 결과만으로 W2-D2 또는 phase/W2→integration 완료를 선언하지 않습니다.
