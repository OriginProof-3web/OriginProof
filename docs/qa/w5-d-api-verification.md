# W5 — D 후보 독립 API·체인 검사 보고

검사일: 2026-10-04. D / M2 여인준님 `@yijun0330`. 제품 후보 `9651062c9f36e124b76796278c996764678e1c77` ([C PR #37](https://github.com/OriginProof-3web/OriginProof/pull/37)), QA 코드 `a3f55c6991061ac445d2223f19ff1b2a48acab0e`.

**기본 fresh fixture 18그룹 PASS / 0 FAIL, 혼합 장애 진단 17 PASS / 1 FAIL입니다. W5 통합 브라우저 D2-01~15는 NOT_RUN이며 단계 완료를 선언하지 않습니다.**

[QA 코드](https://github.com/OriginProof-3web/OriginProof/tree/a3f55c6991061ac445d2223f19ff1b2a48acab0e/fixtures/finals), [구조화된 실제 결과](w5-d-api-results.json), [수용 기준 추적표](w5-d-acceptance.md).

## 실행 기준과 보존

- 최신 integration `3295a71c10a1a99c523d3cfefde91b5737b737ac`에서 D 준비 branch를 만들었습니다. 확인 시 phase/W5는 없으며 C 후보는 임시 W4 base의 Draft입니다. W4에 병합하지 않았습니다.
- C/B의 branch를 checkout·merge·cherry-pick하거나 제품 소스를 수정하지 않았습니다. 전체 제품을 `git archive`로 임시 디렉터리에 내보내 동일 후보의 앱·migration·Dockerfile을 실행했습니다.
- D의 W4 helper `0bb5da42d64b9ce298cb2de2951b327da6bc4fc7`, 준비 helper `78cce405357ae1f509a9bfebdbb07af4b02b2411`를 고정 객체로 재사용했습니다. 사본은 임시 제품 디렉터리에만 추가했습니다. QA branch에는 새 D fixture 두 파일만 있습니다.
- 기존 사용자 checkout·개인 .env·Graphify·Serena 메모리·기존 서비스·공유 branch를 보존했습니다. 새 tmpfs PostgreSQL·Anvil·loopback API·private signer와 설정만 사용했습니다. 생성한 container/network/API process의 종료·부재를 확인했습니다.
- provider `mock`, 모델 `gpt-6-luna`, 유료 호출 0입니다. QA child에서 OPENAI_API_KEY를 제거합니다. 운영 DB 초기화나 운영 배포는 수행하지 않았습니다.

## 재현 명령

QA branch의 clean clone에서 실행합니다. `git fetch origin`은 고정 제품/helper 객체를 받기 위한 읽기이며 다른 branch를 작업 checkout으로 전환하지 않습니다.

```sh
git clone --branch test/w5-d-api-qa https://github.com/OriginProof-3web/OriginProof.git OriginProof-w5-d-qa
cd OriginProof-w5-d-qa
git fetch origin
git checkout --detach a3f55c6991061ac445d2223f19ff1b2a48acab0e
UV_PROJECT_ENVIRONMENT=.uv-venv uv sync --frozen --all-packages --all-groups
# 새 소유 DB·Anvil만 생성/종료하는 명시적 opt-in
W5_D_API_QA=1 .uv-venv/bin/python fixtures/finals/w5_p0_api_qa.py
# 혼합 RPC/reorg 환경의 알려진 실패 재현: 이번 실행 exit 1
W5_D_API_QA=1 W5_D_MIXED_STACK_QA=1 .uv-venv/bin/python fixtures/finals/w5_p0_api_qa.py
```

Docker가 필요하고 컨테이너 기반 Foundry를 사용합니다. 호스트 forge는 필요 없습니다. macOS에서 Xcode license 오류가 있는 이 기기에서는 `DEVELOPER_DIR=/Library/Developer/CommandLineTools`로 Git/Make를 실행했습니다. 실행 결과는 `build/w5-d-api/<새 UUID>/summary.json`에 저장되고 credential/settings 원본은 보호된 로컬 build에만 있습니다.

## 기본 fresh 실행 — 18 보고 그룹

| 그룹 | F | 결과·실제 계층 |
| --- | --- | --- |
| `two_types_comparison` | F01, F02 | PASS — socket API seed의 두 유형 VERIFIED/ACTIVE/FULL_COMPARISON, 단일 변조 TAMPERED, 조회 불변 |
| `mutation_permission_matrix` | F05, F10, F12, F15 | PASS — 10 변경 경로 anonymous401·관리 wrong-role403·consume nonowner404·CSRF403·actor injection422; recover 비소유404; 같은 ID 다른 금액409; DB/event 불변 |
| `unregistered` | F06 | PASS — unknown GET404, verify NOT_REGISTERED/null/all NOT_RUN; 실제 Reader 미등록 issuer=None |
| `ownership` | F05, F10, F14, F15 | PASS — 다른 기관/수신자/운영자 제한 자료·키·Proof 조회/변경 거부와 불변 |
| `operation_audit_reconciliation` | F05, F13, F15 | PASS — 실제 저장 Operation/감사 격리·pagination, canonical reconciliation·권한, 역사 projection authority |
| `suspended_new_issuance` | F11 | PASS — 두 기관 suspend 확정, 새 발행409 ISSUER_NOT_ACTIVE, 기존 ISSUER_SUSPENDED, 복귀 ACTIVE |
| `rpc_outage_recovery` | F13 | PASS — 소유 Anvil stop/start, INCONCLUSIVE/null·reconciliation=null, 복구 ACTIVE·불변 |
| `same_operation_recovery` | F12, F13 | PASS — 실제 제출 뒤 프로세스 내부 반환 hash 소실: UNKNOWN→같은 Operation/tx CONFIRMED, 실제 전송1회. socket 응답 유실/OS process restart가 아님 |
| `private_fields` | F15 | PASS — 선택 응답 필드·signer0700/0600, 실제 생성 합성 secret의 응답/owned chain input·log/추적 파일 scan 0누출. 전체 DOM·로그 감사 아님 |
| `approval_chain_boundary` | F09 | PASS — PENDING_REVIEW/APPROVED_PENDING_CHAIN/REJECTED에서 key·Proof409, 거부 전후 DB/event 불변 |
| `default_request_limit` | F15 | PASS — 별도 기본 앱 120건401 후121번째429, spoof XFF 우회 거부, Retry-After/no-store, health live200 |
| `default_login_limit` | F15 | PASS — 별도 기본 앱 실패 로그인10회401 후11번째429 |
| `origin_body_boundaries` | F15 | PASS — Origin/cross-site403, 기본65536bytes 초과 declared/chunked413, 기본10초 느린 body408 |
| `different_rpc_chain` | F14 | PASS — 실제 다른31338 RPC에서 기존 manifest·서명 자료 INCONCLUSIVE/DEPENDENCY_UNAVAILABLE |
| `same_chain_fresh_rpc_guard` | F14 | PASS — 같은31337의 빈 새 RPC·다른 배포 block hash에서 동일 거부. Contract 재배포/서명 제출 아님 |
| `projection_replay_process_restart_reorg` | F13 | PASS — 실제 PostgreSQL/Anvil·별도 API PID: replay False/4table 불변, 재시작 checkpoint 보존·전진, 실제 orphan REVOKED 삭제→ACTIVE/canonical 두 Proof |
| `current_candidate_lifecycle_regression` | F01, F03, F04, F05, F07, F08, F10, F14 | PASS — 별도 fresh DB/Anvil에서 기존20 core 함수 호출+1 ordered ASGI 함수: consume 경쟁/event1, revoke/rotation/expiry/binding. 브라우저21개 검사로 합산하지 않음 |
| `legacy_v1_expiry` | F03 | PASS — 기존 v1 만료 pytest1 PASS, INCONCLUSIVE/EXPIRED/PROOF_EXPIRED; v2/browser와 별도 |

정상 기능 검사는 요청 1000/분·로그인100/분으로 한계 검사를 격리했고 기본 한계120/10은 별도 fresh 앱으로 실제 확인했습니다. projection poll은 QA에서1초(제품 기본5초)로 설정했습니다. OS 시각은 변경하지 않고 기존 lifecycle fixture의 trusted API/EVM 시간 제어를 사용했습니다.

## 혼합 장애 실패 — 미해결 인계

**같은 고정 제품/QA 커밋에서 MIXED_DIAGNOSTIC 모드는 17 PASS / 1 FAIL(exit1)입니다.** 실패 그룹은 `current_candidate_lifecycle_regression`입니다.

- 순서: 두 유형 API seed·소유 RPC stop/start·실제 projection worker 재시작/reorg 검사 후, 같은 DB/Anvil에 원래 W4 ordered lifecycle 함수를 재사용합니다. 해당 함수에도 별도의 Anvil stop/start가 포함돼 있습니다.
- 재기동 후 `VERIFIED`를 기대한 verify에서 `INCONCLUSIVE`, lifecycle null, `DEPENDENCY_UNAVAILABLE`, issuer check `UNAVAILABLE`가 관찰돼 helper verify assertion(line395)이 실패했습니다. 예상된 최초 outage 관측도 진단 배열에 함께 들어 있으므로 배열2개를 실패2건으로 세지 않습니다.
- 원인과 제품 결함 여부는 미확정입니다. Anvil 상태 저장/여러 restart/reorg 조합과 B Reader의 deployment/historical RPC 경계를 B·C가 확인해야 합니다. 제품 수정으로 해결됐다고 표시하지 않습니다.
- 기본 회귀는 기존 pytest fixture의 새 DB/chain 범위를 유지해18/18 통과했습니다. 혼합 모드는 별도 명시적 flag로 보존했으며 실패를 기본 통과에 숨기거나 P0 완료로 처리하지 않습니다.
- 재현에 실제 계정/개인 manifest/비밀값은 필요 없습니다. 두 모드 모두 생성한 자원 정리가 확인됐습니다.

## 구조·환경·기존 회귀

| 검사 | 실제 결과 | 한계 |
| --- | --- | --- |
| candidate Makefile `bootstrap-check`, `env-check` | PASS | immutable 제품 export와 후보 lock의 전용 venv |
| candidate Makefile `make test` | 284 PASS / 4 skipped / 1 warning | 기존 live opt-in4개 미설정; mock/SQLite/core/analyzer 기본 suite. D 실제18그룹과 합산하지 않음 |
| candidate Makefile `make test-contracts` | 22 PASS / 0 FAIL / 0 skipped | pinned Foundry container, 독립 Compose 이름, no-deps; fuzz512회는 별도 test512개로 세지 않음 |
| D QA Ruff·compileall·diff | PASS | Python compileall은 정적 타입 검사 아님 |
| clean clone frozen uv | 51 packages, PASS | 같은 lockfile, fresh 실행 당시 qa_git_dirty=false, source hash 일치 |
| D QA clone `make bootstrap-check env-check env-fingerprint` | PASS | Node22.18.0/pnpm11.19.0/uv0.8.17/Python3.13.7(선언3.13.0과 patch 차이); host forge 없음 참고 |
| W5 통합 UI/QR/키보드·axe/전체 로그 감사 | NOT_RUN | A/C 같은 통합 화면·handoff 대기; API/seed 결과로 대체하지 않음 |

제품 compose/API/deployer/lockfile SHA256와 QA 소스 SHA256는 [JSON](w5-d-api-results.json)의 각 실행 environment에 있습니다. QA checkout의 integration 기반 fingerprint와 제품 후보 config 해시는 서로 다른 범위로 분리했습니다.

## 다음 담당

- D: 통합 화면 handoff 뒤 D2-01~15의 실제 브라우저 관리·QR·새 세션·접근성과 수정 결함을 재검사합니다. D3 선택 확장은 P0 완료 후로 보류합니다.
- B·C: 위 혼합 장애의 Reader/RPC/state 원인 확인과 필요 수정·동일 QA 명령 재검증. D의 정상 결과를 제품 장애 해결로 재사용하지 않습니다.
- A: 승인/키 관리/교체/폐기/consume/QR·오류·접근성의 같은 API 연결 화면을 제공합니다. C는 해당 단계 통합 SHA·manifest·기동 인계를 조율합니다.
- 리뷰: D 자기 검사 및 앞선 에이전트 읽기 검토와 작성자 외 사람 리뷰는 다릅니다. 사람 리뷰·본인 기여 사실 확인은 PENDING입니다.

## AI 활용과 실제 기여

Codex가 D fixture·실패 재현·실행 보고·추적 문서를 작성·실행했습니다. C의 API/모델/기동, B의 Contract/Reader/Writer/projection, 앞 단계 D helper는 고정 SHA로 재사용했습니다. 타 담당 구현·사람의 리뷰·기여 비율을 만들어 기록하지 않았습니다. 새로운 SDK/프레임워크·유료 호출·Serena 온보딩·Graphify 재생성은 없습니다.
