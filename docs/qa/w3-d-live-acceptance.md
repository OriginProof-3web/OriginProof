# W3 D — 실제 API·브라우저 독립 확인

- 담당: D / 여인준님 `@yijun0330`, 실행일 2026-10-03.
- 시작 제품 기준: `phase/W3@121e1cade40f9ac3b001dc7aa24256d9033f0214`.
- 선행 #35(C 발행), #40(B Reader), #44(A 웹), #46(D 코어 QA)는 모두 병합됐습니다.
- 작업: `test/w3-d-live-qa`, 대상 `phase/W3`. **W3 단계 완료·승격 PR이 아닙니다.**
- 작업 PR: [#47](https://github.com/OriginProof-3web/OriginProof/pull/47), C 작성자 외 리뷰 요청.
- 최종 검사 코드: `53da535ae36ca4c9616c04ad4f179bec74aac539`.
- [환경 fingerprint](w3-d-live-environment.json), [기여 기록](../portfolio/W3-D.md).

## 실행 환경과 보존

원래 로컬의 unborn `mvp/ai`와 미추적 작업은 유지했습니다. 기존 임시 checkout이 없어
새 QA clone과 해당 QA 커밋의 새 archive 사본에서 진행했습니다. 앱 worktree 생성은
`Git is unavailable`로 실패해 일반 Git clone을 사용했습니다.

Node 22.18.0, pnpm 11.19.0, Python 3.13.7, uv 0.8.17, Playwright 1.55.0,
macOS arm64, PostgreSQL 16.4-alpine, chain 31337의 고정 Foundry 1.4.4 이미지입니다.
개인 기본 Node 24.8.0·개인 `.env`는 바꾸지 않았습니다. 새 clone의 `.env`는 mock/model
기본값만 담고, 새 DB 비밀번호·계정·signer는 ignored `build/w3-qa`에 0700/0600으로
보관합니다. provider는 mock, 모델은 gpt-6-luna이고 OPENAI_API_KEY를 자식 실행에서 제거합니다.

`prepare_w3_live_qa.py`가 새 이름의 PostgreSQL(tmpfs)·Anvil·API를 만듭니다. 포트는
loopback 15433/18543/14803이고 production 웹은 3000입니다. 기존 자원과 개인 env,
기존 seed/key/deployment 파일을 덮어쓰지 않도록 거부 조건을 넣었습니다.
실패 주입은 이 새 DB의 deferred constraint trigger, 새 signer 파일의 임시 보존/교체,
새 Anvil stop/start, 실제 HTTP 응답만 끊는 로컬 relay를 사용합니다. 일반 DB나 서비스에
실행하지 않도록 DB명·Docker 이미지/네트워크/포트·signer/계정 경로를 검사합니다.

공식 배포 스크립트는 기존 카드 MVP용 Bank를 이미 활성화합니다. Bank는 실제 Reader로
그 상태를 확인한 후 대응 DB fixture를 seed했습니다. Office는 실제 신청·운영자 승인·
체인 활성화를 수행했습니다. 두 기관의 신규 발행키 등록은 실제 API·receipt 확정입니다.
이 준비를 W2의 전체 신규 기관 온보딩 검사로 주장하지 않습니다.

최초 실행 manifest의 source SHA는 `e8031b94dadad0eba990ebb97edffb419674b6f2`였고,
새 archive의 재현 manifest는 최종 검사 코드 SHA `53da535...`입니다.
두 QA SHA의 A/B/C 제품·Contract·Schema·lockfile은 시작 phase와 동일합니다.

## 실제 결과

| 실행 명령·검사 | 실제 결과 | 계층·한계 |
| --- | --- | --- |
| `make test` | **241 passed / 4 skipped** | 기본 Python 회귀. 기존 actual opt-in 미설정 4건. 새 fixture live 검사는 별도 명령 |
| `pytest -q fixtures/finals/test_w3_live_api_qa.py` | **1 passed / 3.47초** | 여러 실패·성공 경계를 순차 실행한 통합 검사 1개. 실제 HTTP·PG·Anvil |
| `pytest -q apps/api/tests/test_live_finals.py` | **1 passed / 2.56초** | 기존 C 검사를 D가 같은 새 DB/Anvil에서 실행. ASGI 요청·실제 ECDSA/PG/Reader이며 socket HTTP 검사와 구분 |
| D fixture Playwright | **2 passed / 13.0초** | 두 유형의 긴 실제 API 브라우저 시나리오. 아래 범위 포함 |
| `pnpm --filter originproof-demo-web test:e2e` | **11 passed / 0 skipped / 8.7초** | 기존 9개 mock·UI/접근성 회귀 + 기존 실제 API 2개. 이번에는 합성 계정 파일을 지정해 live 2개도 실행 |
| 웹 `test` | **15 passed** | 컴포넌트. 위 브라우저 수와 합산하지 않음 |
| 웹 `build`·`make lint`·`make typecheck` | 통과 | production build·ESLint·tsc·Ruff. Python typecheck는 compileall |
| `make bootstrap-check`·`make env-fingerprint` | 통과 | 구조·도구·설정 및 비교용 fingerprint |
| `make test-contracts COMPOSE='docker compose -p originproof-w3-d-quality'` | **12 passed** | 공식 Foundry 컨테이너. fuzz 512회 포함, 호스트 forge는 미설치 참고 정보 |
| `MVP_API_URL=... python scripts/ci/mvp_http_e2e.py` | 통과 | 실제 HTTP 정상 VERIFIED+ACTIVE / 금액 변조 TAMPERED+AMOUNT_MISMATCH |
| fixture Python 추가 Ruff·문서 링크·diff | 통과 | Makefile Ruff 범위 밖 새 D 검사도 확인 |

마지막 QA 코드 커밋 후의 fresh archive에서 **새 DB·Anvil·API 준비 전체 → D API 검사 →
D 브라우저 검사**를 다시 수행했습니다. 정확한 최종 건수/시간은 아래 재현 기록입니다.
Python·Node 의존성은 동일 lockfile의 첫 clone 설치를 재사용했고, 웹은 동일 제품 소스의
앞서 빌드한 production 서버를 사용했습니다. 다른 컴퓨터 재현 또는 새 웹 build를
이 archive에서 수행한 것으로 주장하지 않습니다.

- fresh prepare: 새 PostgreSQL·Anvil·API와 두 기관 키 준비 전체 통과.
- fresh actual API: **1 passed / 3.52초**, commit 53da535.
- fresh D actual 브라우저: **2 passed / 0 skipped / 12.9초**, commit 53da535.

## W3-D2 — actual API에서 확인한 경계

1. 익명 발행401, 운영자/수신자403, 잘못된 CSRF403, 임의 issuer/key/nonce/role422,
   타 기관 유형403, 문서 기관 코드·잘못된 수신자422. Proof와 성공 감사 건수 불변.
2. 서로 다른 HTTP 연결의 같은 request_id 동시 발행: 두 응답 동일, DB envelope/서명
   동일, Proof·issue 감사 각각1건. 같은 ID 다른 내용409.
3. 두 유형 실제 새 발행과 지정 수신자의 정상 FULL_COMPARISON, 단일 변조 TAMPERED,
   누락 INCONCLUSIVE/PARTIAL_COMPARISON. ID 조회는 PROOF_ONLY·candidate_match NOT_RUN.
4. 공개 응답은 허용 필드만 포함. 익명 content/compare401, 다른 수신자·기관·운영자404,
   타 기관 목록에 해당 ID 없음. 조회·비교 뒤 저장·감사 건수 불변.
5. signer 파일 누락·다른 합성 키: 현재 실제 구현의 409 ISSUING_KEY_UNAVAILABLE,
   신규 Proof/성공 감사 없음. 원래 signer는 finally에서 복구.
6. 실제 PostgreSQL commit 시점의 deferred trigger 실패: HTTP500, 신규 recipient token·
   Proof·감사 모두 rollback. trigger 제거 후 같은 요청 정상 저장1건.
7. 새 Anvil을 실제 중지: 발행503/CHAIN_UNAVAILABLE, 저장 불변. 기존 Proof 조회는
   INCONCLUSIVE/DEPENDENCY_UNAVAILABLE. 상태 보존 재시작 후 기존 Proof 다시 VERIFIED.
8. 서버가 발행·저장을 끝낸 후 HTTP 응답만 소실: 동일 요청 재시도에 기존 Proof를
   반환하고 Proof·감사1건, 정상 서명 비교 유지.

위는 F01/F02/F05/F06/F12/F14 중 실제 수행한 W3 하위 범위입니다. W4 consume 경쟁,
Proof 상태·폐기·만료 전체를 통과로 표시하지 않습니다. 모든 W3 성공 검사는
**lifecycle_status=null, proof_status=NOT_RUN**을 요구하며 ACTIVE 사용 가능을 주장하지 않습니다.

## W3-D3 — actual 브라우저에서 확인한 범위

각 유형을 새 issuer 세션에서 UI로 발행하고 실제 저장 ID·자기 목록·상세·공개 링크를
확인했습니다. 새 익명 세션의 링크 조회 → 지정 수신자의 다른 로그인 세션에서 정상,
금액/문서번호 단일 변조, 필수 비교값 누락, 누락+변조 우선순위 → 새로고침 → 로그아웃
후 공개 재조회 → 다른 기관·수신자의 제한 조회/비교 거부를 검증했습니다.
비교 요청은 UI가 실제 전송했고 page.route/ASGI/mock으로 대체하지 않았습니다.

기존 A의 검사도 현재 phase 제품과 Node 22.18.0으로 실행했습니다. 실제 계정 파일을
지정했으므로 PR #44의 CI에서 skip했던 두 actual API 검사도 이번 로컬에서는 통과했습니다.
기능 검사는 reduced motion 조건입니다. WebGL/일반 애니메이션 성능이나 모든 GPU 환경의
검증은 아닙니다. 비밀번호·세션을 담을 수 있는 trace/video/screenshot은 새 D 검사에서 끕니다.

## 실패 해결·리뷰·남은 범위

- 최초 웹 build/typecheck의 npm cache 권한 오류: 개인 cache를 바꾸지 않고 명령별
  npm_config_cache를 임시 경로로 지정해 공식 frozen 설치/build/typecheck 통과.
- archive 재현에서 pnpm은 symlink 의존성의 자동 재설치를 시도해 TTY 없음으로 중단했습니다.
  동일 lockfile임을 확인하고 해당 명령에만 pnpm_config_verify_deps_before_run=false를
  지정해 이미 설치한 의존성을 보존했습니다. 브라우저 검사를 skip하지 않았습니다.
- 최초 준비의 Bank 중복 활성화: 공식 MVP seed가 이미 활성화한 Bank를 또 등록해
  CHAIN_REVERTED. 제품을 수정하지 않고 실제 Reader 확인 + fixture seed로 해결.
- 병렬 Codex 검토가 DB 소유·기존 generated 파일/환경 보호·실패 출력의 제한 envelope
  노출을 지적해 guard·bool assertion을 보완했습니다. 팀원 C의 리뷰 승인으로 세지 않습니다.
- B의 get_issuer_key_snapshot은 존재하지만 현재 C 발행/검증은 get_issuer/get_key를
  개별 호출합니다. 동일 블록 snapshot 소비/동시 블록 변화는 **B/C 확인·후속 연결 항목**입니다.
- QR 생성/디코딩·실제 휴대폰 LAN 검사는 미실행이며 A 후속 범위입니다. PC 링크만 확인했습니다.
- 다른 컴퓨터 재현, W4 lifecycle/consume, AI 실호출·추출 평가, 운영 배포는 미실행입니다.
- `make smoke`의 전체 Compose 포트 구성은 띄우지 않았습니다. 격리 API ready와 production
  웹을 직접 확인했고 analyzer/redis 서비스 smoke 전체 성공으로 보고하지 않습니다.
- npm의 기존 official 설치는 high 4건의 취약점 안내를 출력했습니다. dependency/보안 gate
  통과로 표현하지 않으며 원래 lockfile과 제품 의존성은 보존했습니다. A/B의 보안 후속 확인이 필요합니다.
- 원래 기본 회귀의 warning은 Starlette/anyio deprecation입니다. 검사 실패로 숨기지 않았습니다.
- 새 작업의 작성자 외 C 리뷰·CI와 A~D 기여 기록·최종 phase 검사, W1→W2→W3 단계 승격은
  별도입니다. 이 D 결과로 W3 전체 완료나 integration 병합을 선언하지 않습니다.

## 재현 명령

**새 임시 QA checkout에서만** lockfile의 Python·웹 의존성, Node 22.18.0을 준비합니다.
기존 `.env`/seed/deployment가 있는 사본에는 prepare를 실행하지 않습니다.

```sh
docker build -f infra/docker/deployer.Dockerfile -t originproof-w3-d-qa-deployer .
PYTHONPATH=apps/api/src:packages/python:services/analyzer/src \
  .uv-venv/bin/python fixtures/finals/prepare_w3_live_qa.py
source build/w3-qa/runtime.env
# 같은 환경으로 웹 build 후 별도 터미널에서 production start
pnpm --filter originproof-demo-web build
pnpm --filter originproof-demo-web start --hostname 127.0.0.1
# API 실패 검사와 브라우저 발행은 동시에 실행하지 않습니다.
.uv-venv/bin/python -m pytest -q fixtures/finals/test_w3_live_api_qa.py
NODE_PATH="$PWD/apps/web/node_modules" pnpm --dir apps/web exec playwright test \
  --config ../../fixtures/finals/w3_playwright.config.ts
```

API 검사는 recipient_new token의 초기 부재를 요구하므로 재실행도 새 QA DB에서 합니다.
검사 종료 후 build/w3-qa/resources.json의 **이번 실행에서 만든** 두 컨테이너·네트워크와
API PID 및 따로 실행한 웹만 종료합니다. 개인 작업 파일·키·다른 서비스/볼륨은 지우지 않습니다.

이번 검사 종료 후 실제로 두 실행의 task-owned API·DB·Anvil·네트워크와 production 웹,
Foundry 검사에서 만든 별도 네트워크를 정리했습니다. 기존 작업 파일·개인 설정은 보존했습니다.
