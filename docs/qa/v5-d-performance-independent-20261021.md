# D 성능 측정·독립 검증·최신 기준 반영 — 2026-10-21

계획서 **5.1** / 공통 소비 계약 **v5-shared-0.2** / ADR0004. 작업은 D `codex/v5-d-independent-qa` / [PR #76](https://github.com/OriginProof-3web/OriginProof/pull/76)입니다. 코드 커밋 `ebd9b01ef9721ded0124e864cc8283e686ea0141`, 최신 기준 적용 후 실행 SHA `31ba879853c368c92801396b498504343f3a332a`를 이후 문서 커밋과 구분합니다. [구조화 수치·회차 기록](v5-d-performance-independent-20261021.json).

## 기준과 기존 작업 보존

integration `ec8e15c6bc684ae1e8d68f53ea40b4a8e47aad67`(#82), phase/W5 `d757a267c5381e5a9b528f63a6c3acef852da996`(#86/#87)를 D W2→W3→W4→W5→QA에 정상 merge했습니다. D의 이전 커밋·C 대행 구현·기여 이력과 사용자 원본을 보존했습니다. #87 최초 반영의 W5-D 문서 충돌은 양쪽 고유 기록을 모두 보존하고 같은 문단만 중복 제거했으며, 이번 #82/#86 추가 반영에는 충돌이 없었습니다. 공유/보존 branch 직접 개발·force push·reset·과거 PR 순차 재병합은 하지 않았습니다.

#87 보안 수정은 이미 병합됐으므로 새 의존성 변경은 없습니다. #82의 사후 리뷰 완료 및 승격 PR 자체의 작성자 외 리뷰 조건을 적용합니다. D 스택은 단계별 비교를 위해 기존 base를 유지하며 다음 PR의 retarget은 선행 병합 뒤 C가 조율합니다. 준비 계약·mock 성공을 실제 연결/단계 완료로 해석하지 않습니다.

## 100회 검증 성능 도구

[도구](../../fixtures/finals/v5_d_verification_benchmark.py)는 `/v3/verifications`를 서로 다른 request_id로 순차 100회 호출합니다. HTTP200뿐 아니라 공통 VerificationResult schema·VERIFIED/FULL_COMPARISON·chain/contract·document/version·ACTIVE·경고 없음까지 확인합니다. 오류와 잘못된 응답도 전체100개 p50/p95 및 오류율 분모에 포함합니다. p50은 중앙값, p95는 nearest-rank이며 p95≤3초와 기능 일치100/100을 각각 기록합니다. 응답 원문·candidate는 보고서에 넣지 않습니다.

| 환경·템플릿 | 정상/전체·오류율 | p50 | p95 |
| --- | --- | --- | --- |
| 로컬 ASGI/SQLite/합성 Registry · payment | 100/100 · 0% | 6.81ms | 7.50ms |
| 로컬 ASGI/SQLite/합성 Registry · official | 100/100 · 0% | 6.58ms | 7.11ms |
| GitHub CI ASGI/SQLite/합성 Registry · payment | 100/100 · 0% | 11.98ms | 14.15ms |
| GitHub CI ASGI/SQLite/합성 Registry · official | 100/100 · 0% | 8.80ms | 10.86ms |

로컬 수치는 #86 병합 전 동일 benchmark 소스에서 측정했고 보고서의 code SHA256으로 식별합니다. 최신 실행 HEAD의 성능 근거는 위 GitHub CI 수치입니다. 두 합성 템플릿 모두 DB 검증 세션100행과 체인 쓰기0을 확인했습니다. 시간은 client POST 왕복이며 결과 검증은 타이머 밖입니다. 단위·오류 분모 검사와 합성 측정 총16개가 통과했습니다. 현재 수치는 네트워크·PostgreSQL·실제 RPC·브라우저 성능이나 서버 코어 단독 시간, 부하/동시성 수용 결과가 아닙니다. 내부 캐시 효과도 분리하지 않았습니다.

CLI는 config에 source/schema_version/request/expected를 명시합니다. request는 기존 VerificationRequest, expected는 verification_status/comparison_scope/chain_id/verifying_contract/document_id/version/state/warnings입니다. 합성 안내의 실제 검증 근거와 같은 기대값을 소유자가 제공해야 하며 예시 응답을 실제 서버 성공으로 대체하지 않습니다. 기본은 실행 계획 출력뿐입니다:

```sh
.uv-venv/bin/python fixtures/finals/v5_d_verification_benchmark.py \
  --config /path/to/synthetic-config.json --api-origin http://127.0.0.1:8000 \
  --candidate-sha "$CANDIDATE_SHA"
# 지정된 폐기 가능한 합성 서버 준비 후에만 --execute 추가
```

실행은 명시 loopback HTTP+port만 허용하며 redirect/proxy 사용을 끕니다. 대상 SHA는 선언값이고 서버 SHA를 검증하지 않았다는 표시를 유지합니다. 실제 실행은 검증 세션 DB 행을 만들며, 이 CLI로 실제 HTTP 서버 검사는 이번에 하지 않았습니다. 보고서는 기존 파일을 덮지 않고 기본 build/qa 아래0600 파일로 저장합니다.

## 서비스 API 밖 검증의 D 소비 검사

C [#63](https://github.com/OriginProof-3web/OriginProof/pull/63)의 고정 `68ea0c20718937cd0c93d683e3cfa9b3995a9666`에서 독립 검증 CLI·기존 테스트 helper·Golden·ABI 네 파일을 읽기 전용으로 재사용합니다. [D 검사](../../fixtures/finals/test_v5_d_independent_verifier.py)에 네 SHA256을 고정했고 원본이 바뀌면 실패합니다. C branch를 checkout/merge하거나 C 구현을 복제하지 않았습니다. CI는 contents:read의 두 번째 checkout으로 고정 소스를 읽고 현재 D head의 모델/lock을 사용합니다. 원래 C63 전체 환경 재현과 구분합니다.

- C 기존49개: 원본/보호 필드·ABI·RPC 오류·도메인·reorg·CLI 등입니다.
- D 추가22개: 두 템플릿의 후보 필드·서명·체인 commitment/키 변조, export 원본 선검사, 부분 비교, 정상→RPC 장애/chain 불일치/코드 없음→복구 재조회, 철회/대체 상태 보존입니다. 중복 ABI 검사는 C 기존 검사에서만 집계합니다.
- 총 **71 PASS / 실패·skip0**. socket 차단·eth_* 합성 MockTransport이며 서비스 API/AI 호출0입니다. 서명 해시/로컬 원본 검증과 실제 배포/RPC 검증을 구분합니다. 실제 독립 체인 검증 수용은 B/C 배포/근거 인계 후 진행합니다.

재현(고정 Git 객체가 있는 로컬 checkout):

```sh
PYTHONPATH=services/analyzer/src:apps/api/src:packages/python:services/indexer/src:apps/api/tests \
  .uv-venv/bin/python -m pytest -q -o addopts= \
  fixtures/finals/test_v5_d_verification_benchmark.py \
  fixtures/finals/test_v5_d_independent_verifier.py
# C 기존49개까지 함께 실행하려면 C63을 읽기 전용 export한 경로를 사용
D_C63_SOURCE_DIR=/path/to/immutable-c63 .uv-venv/bin/python -m pytest -q -o addopts= \
  fixtures/finals/test_v5_d_independent_verifier.py \
  /path/to/immutable-c63/scripts/ci/test_wallet_independent_verifier.py
```

## G07 병합 후 실제 반복

#86 병합 뒤 clean QA `31ba879853c368c92801396b498504343f3a332a` / 제품 `d757a267c5381e5a9b528f63a6c3acef852da996` / 동일 lock `ff740f712def1f869f0a68c113164fd693507319ccf63b3313d79ced9f1bc112`의 사전 조건을 통과했습니다. 실행 명령은 [절차](v5-d-g07-retest-plan-20261021.md)의 `--execute --mixed-runs 3`입니다.

| 회차 | 실제 모드 | 필수 그룹 통과 | 자원 정리 | runner 판정 |
| --- | --- | --- | --- | --- |
| 1 | FRESH | 18/18 | True | PASS |
| 2 | MIXED_DIAGNOSTIC | 18/18 | True | PASS |
| 3 | MIXED_DIAGNOSTIC | 18/18 | True | PASS |
| 4 | MIXED_DIAGNOSTIC | 18/18 | True | PASS |

총 판정 **PASS_REQUIRES_B_C_REVIEW**입니다. 실제 격리 PostgreSQL·Anvil·HTTP API와 legacy v1/v2 lifecycle/consume, 중단·재시작·projection/worker/reorg 재현입니다. 각 회 새 합성 자원을 만들고 정리했으며 기존 서비스/DB를 건드리지 않았습니다. AI mock/유료0, 브라우저 미실행, 신규 지갑 Registry 연결 완료와 구분합니다. 실패 회차를 숨기거나 최종 성공으로 덮지 않았습니다. **G07은 B/C가 원인 수정과 D 반복 증거를 검토하기 전까지 OPEN입니다.**

## 검사·남은 작업·기여

최신 기준에서 D 스택 stage12/25/31/31/43, consumer각31·guard각16을 재실행해 실패·skip0입니다. 최신 CI 산출물은 stage43/consumer31/성능16/독립71을 확인했습니다. 서로 겹치는 범위는 합산하지 않습니다. YAML/bash·Ruff·diff를 확인했으며 원본 모델·생성물·Schema/OpenAPI/ABI·lockfile은 새로 수정하지 않았습니다.

B/C: G07 반복 증거 검토와 실제 Registry/ABI/manifest·승인 주소·verification material·정상/거부 기대값 인계가 필요합니다. C: #85 seed-only readiness503의 P0 준비 조건과 실제 지갑 연결 절차, 사후 리뷰/승격 조율이 남습니다. A/B/C: 같은 후보의 지갑/QR/기관 격리·상태 UX와 브라우저 검사가 남습니다. A/C: 합성60개 라벨/24·36 분할 리뷰, 팀: 입력 종류·우선순위와 유료 평가 범위/예산 결정이 남습니다. 선택된 gpt-6-luna와 Decisions API 범위 밖 결정은 다시 묻지 않습니다.

Codex가 사용자의 D 개발·공유 지시에 따라 도구/검사/문서를 작성하고 기존 PR에 push했습니다. C의 구현·fixture와 D 기존 기여를 재사용했으며 기여 비율·사람의 확인/Approve를 만들지 않았습니다. 사람 외부 리뷰·실환경 성능/독립 검증·단계 완료·원격 병합은 수행하지 않았습니다.
