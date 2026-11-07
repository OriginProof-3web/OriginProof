# W5-D1 — P0 수용 기준 추적표

기준: [개발 계획서 15.6·16절](../development_plan.md), [ADR 0001](../adr/0001-finals-contracts.md). 담당 D `@yijun0330`. 확인일 2026-10-04.

**D1의 근거 매핑을 준비했습니다. D2의 W5 통합 실행은 전 항목 NOT_RUN이며 W5 완료를 선언하지 않습니다.** 작성자 외 사실 확인·리뷰는 대기 중입니다.

`phase/W5`가 없어 최신 `integration@3295a71c10a1a99c523d3cfefde91b5737b737ac`에서 독립 준비했습니다. 문서·운영 계획 PR은 루트 지침에 따라 `integration`을 대상으로 합니다. 기능을 단계 검증 없이 병합하는 PR이 아닙니다.

구조화된 원본은 [w5-d-acceptance.json](w5-d-acceptance.json)입니다. 각 ID에 담당 작업·검사 파일/함수·명령·실행/제품 SHA·보고서·잔여 검사를 연결했습니다. 상세 재현 조건은 아래 고정 SHA 보고서에 있습니다.

## 상태와 증거 사용

- `PARTIAL`: 과거 실행에서 해당 하위 범위 근거가 있습니다. F 항목 전체 통과가 아닙니다.
- `PARTIAL_WITH_FAILURE`: 부분 근거와 알려진 이전 브라우저 실패가 함께 있습니다.
- `NOT_RUN`: 같은 W5 통합 제품에서 아직 실행하지 않았습니다. 구현 부재를 뜻하지 않습니다.
- 실제 API·DB·체인 성공과 브라우저 관리 흐름 성공을 분리합니다. 원 실행의 한 테스트에 여러 F 사례가 있어도 통과 개수를 중복 합산하지 않습니다.
- 기존 v1 정상/금액 변조는 별도 회귀입니다. W3 `VERIFIED + null`과 W4 `ACTIVE`를 합쳐 최종 `VERIFIED + ACTIVE/FULL_COMPARISON`의 증거로 쓰지 않습니다.

## 후보 독립 API·체인 실행 추가

제품 `9651062c9f36e124b76796278c996764678e1c77`, QA `a3f55c6991061ac445d2223f19ff1b2a48acab0e`의 clean clone에서 **fresh18PASS/0FAIL, mixed17PASS/1FAIL**을 실행했습니다. [실행 보고](w5-d-api-verification.md)와 [JSON](w5-d-api-results.json)에 명령·계층·hash·불변·정리 결과를 기록했습니다. 아래 과거 근거와 별도이며 통합 D2 웹 판정은 전부 NOT_RUN입니다.

F06 unknown 조회, F09 승인 대기/반려 거부, F11 중지 중 새 발행, F15 기본 제한·선택 비밀정보, 실제 projection replay/프로세스 재시작/reorg 근거를 보완했습니다. F03 v1 만료와 현 후보의 fresh lifecycle도 별도 실행했습니다. 혼합 스택 재기동 후 Reader UNAVAILABLE 실패는 **G07, B/C 원인 확인 대기**입니다. 다른 RPC guard는 Contract 재배포/서명 제출 검사가 아닙니다.

## F01~F15 매핑

| ID · 기대 결과 | 기존 D 근거 | 남은 D 검사 | 소유자 선행 작업 | W5 실행 |
| --- | --- | --- | --- | --- |
| **F01** 두 기관·두 유형 신규 발행, VERIFIED + ACTIVE와 인증 대상자의 FULL_COMPARISON | W3 새 발행·실제 서명·자료 비교 통과. W4 ASGI 신규 발행·현재 ACTIVE 확인. 서로 다른 제품 실행입니다.<br>[w3_core](#w3-core), [w3_socket_api](#w3-socket-api), [w3_browser](#w3-browser), [w4_core_and_actual_asgi](#w4-core-and-actual-asgi), [w4_d3_preparation](#w4-d3-preparation) | 같은 W5 통합 SHA에서 브라우저 신규 발행 → 지정 수신자 새 세션 → 전체 비교 → ACTIVE를 함께 확인합니다.<br>QR 생성·PNG 해석·새 세션 조회는 D 독립 검사 미실행입니다. API seed 성공은 브라우저 발행 성공이 아닙니다. | `W3-A1`, `W3-A2`, `W3-A3`, `W3-B1`, `W3-C1`, `W3-C2`, `W3-C3`, `W4-B3`, `W4-C2`, `W5-C3` | NOT_RUN |
| **F02** 같은 ID에서 금액/문서번호 하나만 변경하면 TAMPERED와 해당 불일치 사유 | W3 socket·브라우저의 금액 +1/문서번호 변경 통과. 누락만 있으면 INCONCLUSIVE, 누락과 실제 불일치는 TAMPERED입니다.<br>[w3_core](#w3-core), [w3_socket_api](#w3-socket-api), [w3_browser](#w3-browser) | W5 통합본에서 lifecycle과 비교 범위·실제 사유를 함께 재검사합니다. | `W3-A3`, `W3-C3`, `W5-A3` | NOT_RUN |
| **F03** v2 수행한 서명/요청 범위 성공 + EXPIRED, 사용 불가; v1 INCONCLUSIVE + EXPIRED 보존 | W4 실제 DB/chain + ASGI에서 만료 -1/0/+1초, EXPIRED와 consume 거부 확인. 최초 매핑에서 v1 만료 실행 근거가 없었고 위 후보 독립 실행에서 전용 pytest1 PASS로 보완했습니다.<br>[w3_core](#w3-core), [w4_core_and_actual_asgi](#w4-core-and-actual-asgi) | 통합 UI의 만료·사용 불가 표시를 검사합니다. 후보 fresh lifecycle과 v1 만료 회귀는 실제 실행됐으며 브라우저 결과와 분리합니다. | `W4-A2`, `W4-B2`, `W4-C2` | NOT_RUN |
| **F04** 순차/동시 consume 체인 전이 한 번, 새 ID 재사용 거부·같은 ID 기존 Operation·조회 불변 | W4 ASGI + 실제 chain에서 서로 다른 ID 경쟁 200/409·event 1개, 같은 ID 동일 Operation/tx, 새 ID REPLAY_DETECTED·읽기 불변 통과.<br>[w4_core_and_actual_asgi](#w4-core-and-actual-asgi), [w4_d3_preparation](#w4-d3-preparation) | 새 수신자 세션의 UI consume → 재조회 → 재사용 거부를 검사합니다.<br>미확정/실패 UI는 receipt와 현재 체인 재조회 전 성공 표시 금지를 확인합니다. W4 준비 수집기의 RPC 중지는 제출 후 응답 유실 검사와 다릅니다. | `W4-A3`, `W4-B2`, `W4-B3`, `W4-C3` | NOT_RUN |
| **F05** 기관 A의 기관 B 키·Proof 변경을 서버/계약에서 거부하고 B 상태 불변 | W1 신청·W2 키/이력 격리, W3 제한 조회, W4 타 기관 폐기/consume 거부와 상태/event 불변 근거가 있습니다.<br>[W1-LIVE](#w1-live), [W2-LATEST-RECOVERY-RERUN](#w2-latest-recovery-rerun), [W2-BROWSER-CONNECTED](#w2-browser-connected), [w3_socket_api](#w3-socket-api), [w4_core_and_actual_asgi](#w4-core-and-actual-asgi) | W5 현재 통합본에서 키·Proof의 UI와 직접 HTTP 변경을 대조하고 거부 전후 DB·chain·event를 확인합니다. | `W2-A2`, `W2-B1`, `W2-C3`, `W3-C2`, `W4-B1`, `W4-C2`, `W5-C1` | NOT_RUN |
| **F06** 미등록 Proof/발행자는 NOT_REGISTERED, 위조라고 단정하지 않음 | W3 코어의 합성 issuer=None은 NOT_REGISTERED/ISSUER_NOT_FOUND. key=None은 INCONCLUSIVE/KEY_NOT_FOUND입니다. 최초 과거 D 선택 파일에는 실제 HTTP unknown Proof가 없었고 후보 독립 실행에서 보완했습니다.<br>[w3_core](#w3-core) | 후보 API unknown Proof와 미등록 issuer 근거를 기록했습니다. 통합 UI의 NOT_REGISTERED 문구·동선을 확인합니다. | `W3-A3`, `W3-B1`, `W3-C2`, `W3-C3`, `W5-A3` | NOT_RUN |
| **F07** Proof 폐기 후 새 사용자 세션에서 VERIFIED + PROOF_REVOKED, 사용 불가 | W4 실제 DB/chain + ASGI에서 적법한 폐기·반복 폐기 event 불증가·소비 후 폐기 이력 보존 통과. 새 브라우저 세션은 미실행입니다.<br>[w4_core_and_actual_asgi](#w4-core-and-actual-asgi), [w4_d3_preparation](#w4-d3-preparation) | 브라우저 실제 폐기 후 새 수신자 세션에서 두 유형의 현재 상태·사유·사용 불가를 확인합니다. | `W4-A2`, `W4-B1`, `W4-C2` | NOT_RUN |
| **F08** 정상 교체·키 기간 종료는 과거 정상 Proof 보존, 유출 폐기는 사용 차단·미확인 키 발행 금지 | W4 ASGI/chain에서 두 기관 정상 교체·선택 키·과거 ACTIVE·키 기간 종료 보존·유출 ISSUER_KEY_REVOKED 통과.<br>[w4_core_and_actual_asgi](#w4-core-and-actual-asgi), [w4_d3_preparation](#w4-d3-preparation) | UI 교체 → 새 발행 → 새 사용자 세션의 과거/신규 Proof 확인을 수행합니다.<br>등록 미확정/실패 시 발행 키 선택 유지와 발행 금지를 확인합니다. 준비 manifest 기대값을 실행 성공으로 바꾸지 않습니다. | `W4-A1`, `W4-B3`, `W4-C1` | NOT_RUN |
| **F09** 미승인 기관 발행·키 등록 거부; DB 승인만으로 허용하지 않고 체인 활성화 후 허용 | 미승인/반려/DB 승인 체인 미완료 키 등록 거부·Operations/sends 0 확인. W3 발행 권한 거부. W2 UI 활성화·키 경로 6개 capability 검사 실패가 남습니다.<br>[W1-LIVE](#w1-live), [W2-LATEST-RECOVERY-RERUN](#w2-latest-recovery-rerun), [W2-BROWSER-CONNECTED](#w2-browser-connected), [W2-BROWSER-GAPS](#w2-browser-gaps), [w3_socket_api](#w3-socket-api) | W5 UI 신청 → 검토 → 체인 활성화 → 키 등록 → 발행을 완료합니다. 후보 API pending/rejected/approved_pending_chain 거부 검사는 통과했습니다. | `W2-A1`, `W2-A2`, `W2-B1`, `W2-C2`, `W2-C3`, `W3-A1`, `W3-C1` | NOT_RUN |
| **F10** 무권한 승인·consume 및 역할/기관 ID 주입 거부 | W1 실제 역할·자체 승인·CSRF·주입 거부, W4 ASGI/실제 chain에서 비인가 consume·직접 gateway 우회 거부 근거가 있습니다.<br>[W1-LIVE](#w1-live), [W2-LATEST-RECOVERY-RERUN](#w2-latest-recovery-rerun), [w4_core_and_actual_asgi](#w4-core-and-actual-asgi) | W5 세 역할·다른 기관/수신자·익명 세션의 UI와 직접 HTTP/Contract 호출을 대조합니다. 숨긴 버튼만으로 서버 권한 성공을 주장하지 않습니다. | `W1-C2`, `W2-C2`, `W4-A3`, `W4-B2`, `W4-C3`, `W5-C1` | NOT_RUN |
| **F11** 기관 중지 중 신규 발행 거부, 기존 Proof ISSUER_SUSPENDED | W4 실제 chain 중지 → 기존 문서 Proof VERIFIED + ISSUER_SUSPENDED → 복귀 ACTIVE 확인. 중지 중 새 발행 POST는 이 D 검사에 없습니다.<br>[w4_core_and_actual_asgi](#w4-core-and-actual-asgi) | 후보 두 유형 중지 중 새 발행 거부·불변 검사를 통과했습니다. 새 브라우저 세션의 중지·복귀 표시를 검사합니다. | `W2-A1`, `W3-B1`, `W3-C1`, `W4-A2`, `W4-C2` | NOT_RUN |
| **F12** 등록·발행 timeout 재시도 시 기존 작업 조회, 중복 키/Proof/체인 변경 없음 | W2 실제 응답 유실·receipt timeout/API 재시작 후 같은 tx 복구. W3 동시 발행 동일 envelope·저장 1개/서명·저장 실패 거부. W4 같은 ID consume 동일 Operation.<br>[W2-LATEST-RECOVERY-RERUN](#w2-latest-recovery-rerun), [w3_socket_api](#w3-socket-api), [w4_core_and_actual_asgi](#w4-core-and-actual-asgi) | 통합 UI 중복 클릭·timeout·재시도에서 같은 Operation/tx·Proof를 확인합니다.<br>PR #50의 전송 전 저장 실패/취소 nonce 수정은 별도 B/C 리뷰 대상이며 이 선택 D 실행 증거에 포함되지 않았습니다. | `W2-A1`, `W2-A2`, `W2-C1`, `W3-A1`, `W3-C1`, `W5-C1`, `W5-C2` | NOT_RUN |
| **F13** RPC·미확인 제출·재시작에서 대기/실패 구분, 현재 판정 보류와 복구 상태 일치 | W2 socket RPC/UNKNOWN/실제 프로세스 재시작·실패 receipt 구분, UI UNKNOWN 대기 표시. W4 실제 RPC 단절 → null/503 → ACTIVE 복구. 최초 과거 자료에 Indexer/reorg 실제 D 근거가 없었고 후보 독립 실행에서 보완했습니다.<br>[W2-LATEST-RECOVERY-RERUN](#w2-latest-recovery-rerun), [W2-BROWSER-CONNECTED](#w2-browser-connected), [W2-BROWSER-GAPS](#w2-browser-gaps), [w3_socket_api](#w3-socket-api), [w4_core_and_actual_asgi](#w4-core-and-actual-asgi), [w4_d3_preparation](#w4-d3-preparation) | 통합 UI pending/UNKNOWN/FAILED·복구 조회·현재 판정 보류를 검사합니다. 후보 실제 projection replay/API 프로세스 재시작/reorg는 통과했습니다.<br>G07 혼합 RPC/reorg 스택에서 재기동 후 Reader UNAVAILABLE 실패는 B/C 원인 확인·수정 인계 뒤 재검사합니다. | `W5-A1`, `W5-A3`, `W5-B1`, `W5-B2`, `W5-B3`, `W5-C2`, `W5-C3` | NOT_RUN |
| **F14** 수신자 binding·domain/network 불일치 거부, 다른 chain ID 서명 재사용 금지 | 코어 network/domain 오류, 실제 지정 수신자 제한 조회·잘못된 binding 체인 receipt 0/상태 불변 근거. 실제 두 번째 chain 재사용은 D 미실행입니다.<br>[w3_core](#w3-core), [w3_socket_api](#w3-socket-api), [w3_browser](#w3-browser), [w4_core_and_actual_asgi](#w4-core-and-actual-asgi) | 후보의 실제 다른31338/새31337 RPC identity guard는 통과했습니다. 빈 RPC 검사와 다른 Contract로의 실제 서명 제출 거부는 분리하며 후자는 B의 배포/검사 경계 인계 후 확인합니다.<br>W5 지정/다른 수신자의 UI 비교/consume과 binding을 확인합니다. | `W3-B2`, `W3-C3`, `W4-A3`, `W4-B2`, `W4-C3` | NOT_RUN |
| **F15** 비밀정보 비노출, 키보드·결과 읽기 가능, 과도한 요청 제한 | W1 선택 화면 axe 0, W2 키 응답·W3 공개/제한 필드 비노출 근거. W2 approved 화면 definition-list 접근성 실패. 전체 보안·요청 제한 검사는 미매핑입니다.<br>[W1-LIVE](#w1-live), [W2-LATEST-RECOVERY-RERUN](#w2-latest-recovery-rerun), [W2-BROWSER-CONNECTED](#w2-browser-connected), [W2-BROWSER-GAPS](#w2-browser-gaps), [w3_socket_api](#w3-socket-api), [w3_browser](#w3-browser) | 세 역할 키보드·focus·label·오류/결과 읽기·대비·작은 화면을 독립 검사합니다.<br>후보 기본 rate/Origin/body/time 제한과 선택 응답·signer·known synthetic secret의 Git/체인 검사는 통과했습니다. UI 요청 복구·URL/QR/DOM/저장소·전체 로그 감사는 연결 후 수행합니다. | `W5-A1`, `W5-A2`, `W5-A3`, `W5-C1` | NOT_RUN |

## 고정된 실행 근거

각 명령은 **그 QA 코드 SHA와 보고서의 환경 준비 조건**에서 실행된 명령입니다. 이번 준비 checkout에는 앞 단계 검사 파일이 포함되지 않습니다. 원본을 복사해 현재 제품의 성공으로 치환하지 않습니다.

<a id="w1-live"></a>
### W1-LIVE

- [PR #41](https://github.com/OriginProof-3web/OriginProof/pull/41) · QA `f1de961d8f94405d5a143cd853421eee8878b4f1` · 제품 기준 `0308cb24f9e4aed157095131e2552243767d16eb`
- 파일: [scripts/ci/w1_live_qa.py](https://github.com/OriginProof-3web/OriginProof/blob/f1de961d8f94405d5a143cd853421eee8878b4f1/scripts/ci/w1_live_qa.py), [apps/web/e2e/w1-live.spec.ts](https://github.com/OriginProof-3web/OriginProof/blob/f1de961d8f94405d5a143cd853421eee8878b4f1/apps/web/e2e/w1-live.spec.ts)
- 검사: `scripts/ci/w1_live_qa.py::main`, `real W1 roles, CSRF, application decisions, session persistence and isolation`
- 계층: actual_socket_http; actual_postgresql; actual_chromium_browser; actual_web_to_api
- 원 결과: {"status": "PASS_SCOPED", "browser_passed": 1, "db_checks": "PASS", "claims": ["Anonymous/operator-request 401; recipient/issuer 403", "login role and application issuer_id injection 422", "CSRF missing 403; no application creation", "separate issuer A/B applications and mine/read isolation", "operator approve/reject => APPROVED_PENDING_CHAIN/REJECTED; DB matches", "issuer/self approval 403; duplicate decision 409; state unchanged", "reload/logout/fresh login preserves decisions and revokes sessions", "cookie HttpOnly/SameSite=Lax/Max-Age=28800; synthetic DB-expired session auth/me 401", "two successful decision AuditEvent rows", "axe violations zero at login/operator/approved issuer screens after dl fix"]}
- 한계: W1 has no actual institution activation/key/proof issuance/consume browser path; Several denial/injection checks use Playwright APIRequestContext actual HTTP, not user UI actions; The session-expiry DB timestamp was changed only for disposable synthetic session, not OS clock; No general request-limit or whole logging/secret audit claim
- 보고서: [docs/qa/w1-final-verification.md@94488b1](https://github.com/OriginProof-3web/OriginProof/blob/94488b13d80df991bc5b861d1d4d44da267355ee/docs/qa/w1-final-verification.md)

```sh
W1_QA_DISPOSABLE=1 W1_LIVE_API_URL=http://127.0.0.1:18081 W1_LIVE_BASE_URL=http://127.0.0.1:13000 PYTHONPATH=apps/api/src:packages/python .uv-venv/bin/python scripts/ci/w1_live_qa.py
```

<a id="w2-latest-recovery-rerun"></a>
### W2-LATEST-RECOVERY-RERUN

- [PR #51](https://github.com/OriginProof-3web/OriginProof/pull/51) · QA `a66ac7205119369774c62466ae0ea4d3c5259aff` · 제품 기준 `6f508fe6ae5ce106999c171e8205978dd2201333`
- 파일: [scripts/ci/test_w2_recovery_qa.py](https://github.com/OriginProof-3web/OriginProof/blob/a66ac7205119369774c62466ae0ea4d3c5259aff/scripts/ci/test_w2_recovery_qa.py), [apps/api/tests/test_live_w1_w2.py](https://github.com/OriginProof-3web/OriginProof/blob/a66ac7205119369774c62466ae0ea4d3c5259aff/apps/api/tests/test_live_w1_w2.py), [apps/api/tests/test_live_w2_chain.py](https://github.com/OriginProof-3web/OriginProof/blob/a66ac7205119369774c62466ae0ea4d3c5259aff/apps/api/tests/test_live_w2_chain.py), [services/indexer/tests/test_live_chain.py](https://github.com/OriginProof-3web/OriginProof/blob/a66ac7205119369774c62466ae0ea4d3c5259aff/services/indexer/tests/test_live_chain.py)
- 검사: `test_live_failure_recovery_and_process_restart`, `test_existing_postgres_and_chain_acceptance`, `test_existing_indexer_local_chain_acceptance`, `test_postgres_login_application_and_operation_flow`, `test_postgres_chain_lock_releases_on_cancellation`, `test_live_approval_keys_failure_and_restart`, `test_live_reader_and_m1_api`
- 계층: actual_socket_http; actual_postgresql; actual_anvil; actual_api_process_restart; wrapper-contained ASGI HTTP with actual PostgreSQL/Anvil; v1 Reader regression; not actual Indexer process/reorg evidence
- 원 결과: {"status": "PASS_SCOPED", "passed": 3, "duration_seconds": 25.53, "inner_not_additive": "C live3 and B localEVM1 included"}
- 한계: 하나의 순서 있는 socket 장애 시나리오와 C/B 검사 wrapper 두 개입니다. wrapper 내부 C 3개와 B 1개를 총 3개에 더하지 않습니다.; 실제 socket/API 프로세스 재시작과 내부 ASGI/DB/chain 검사를 구분합니다. 실제 PostgreSQL Indexer 서비스 재시작·reorg, Proof/consume와 전체 브라우저 쓰기 흐름의 통과를 주장하지 않습니다.; 전송 전 save_prepared 실패/취소의 PR50 수정과 전체 키 파일/로그/비밀정보·요청 제한은 이 원 실행의 검사 범위가 아닙니다.
- 보고서: [docs/qa/w2-d-browser.md@17f78e3](https://github.com/OriginProof-3web/OriginProof/blob/17f78e300b04aa9395fb20f6f76f5313d705db3d/docs/qa/w2-d-browser.md), [docs/qa/w2-d-recovery.md@17f78e3](https://github.com/OriginProof-3web/OriginProof/blob/17f78e300b04aa9395fb20f6f76f5313d705db3d/docs/qa/w2-d-recovery.md)

```sh
W2_RECOVERY_QA=1 LLM_PROVIDER=mock OPENAI_MODEL=gpt-6-luna PYTHONPATH=apps/api/src:packages/python:services/analyzer/src:services/indexer/src UV_PROJECT_ENVIRONMENT=.uv-venv uv run --no-sync pytest -q scripts/ci/test_w2_recovery_qa.py
```

<a id="w2-browser-connected"></a>
### W2-BROWSER-CONNECTED

- [PR #51](https://github.com/OriginProof-3web/OriginProof/pull/51) · QA `a66ac7205119369774c62466ae0ea4d3c5259aff` · 제품 기준 `6f508fe6ae5ce106999c171e8205978dd2201333`
- 파일: [fixtures/finals/prepare_w2_browser_qa.py](https://github.com/OriginProof-3web/OriginProof/blob/a66ac7205119369774c62466ae0ea4d3c5259aff/fixtures/finals/prepare_w2_browser_qa.py), [fixtures/finals/w2_browser_qa.spec.ts](https://github.com/OriginProof-3web/OriginProof/blob/a66ac7205119369774c62466ae0ea4d3c5259aff/fixtures/finals/w2_browser_qa.spec.ts), [fixtures/finals/w2_browser_qa.config.ts](https://github.com/OriginProof-3web/OriginProof/blob/a66ac7205119369774c62466ae0ea4d3c5259aff/fixtures/finals/w2_browser_qa.config.ts)
- 검사: `[connected] actual application APPROVE, issuer refresh, fresh login and logout`, `[connected] actual application REJECT, issuer refresh, fresh login and logout`, `[connected] real confirmed Operation and own audit events are read through the UI`, `[connected] real UNKNOWN Operation is shown without a confirmed success`, `[connected] another issuer is denied another institution Operation through the actual UI`, `[connected] anonymous, operator and recipient see the actual issuer-only key access gate`
- 계층: actual_chromium_browser; production_next; actual_socket_http; actual_postgresql; actual_anvil_seed
- 원 결과: {"status": "PASS_SCOPED", "connected_passed": 6, "claims": ["fresh UI application approve/reject with DB matching states", "separate context reload/login/logout persisted decisions", "real confirmed operation and institution-isolated audit displayed", "real hash response loss seed yields UNKNOWN shown pending rather than confirmed", "other issuer Operation404 through UI", "anonymous401 and issuer-only key access gate"]}
- 한계: Active institution/key/UNKNOWN preparation uses actual API seed, not UI success; No page.route mock but full activation/register/revoke UI does not exist; Default CI does not run these disposable opt-in browser acceptance projects
- 보고서: [docs/qa/w2-d-browser.md@17f78e3](https://github.com/OriginProof-3web/OriginProof/blob/17f78e300b04aa9395fb20f6f76f5313d705db3d/docs/qa/w2-d-browser.md), [docs/qa/w2-d-browser-environment.json@17f78e3](https://github.com/OriginProof-3web/OriginProof/blob/17f78e300b04aa9395fb20f6f76f5313d705db3d/docs/qa/w2-d-browser-environment.json)

```sh
W2_BROWSER_QA=1 PYTHONPATH=apps/api/src:packages/python:services/analyzer/src:services/indexer/src .uv-venv/bin/python fixtures/finals/prepare_w2_browser_qa.py
```

<a id="w2-browser-gaps"></a>
### W2-BROWSER-GAPS

- [PR #51](https://github.com/OriginProof-3web/OriginProof/pull/51) · QA `a66ac7205119369774c62466ae0ea4d3c5259aff` · 제품 기준 `6f508fe6ae5ce106999c171e8205978dd2201333`
- 파일: [fixtures/finals/w2_browser_qa.spec.ts](https://github.com/OriginProof-3web/OriginProof/blob/a66ac7205119369774c62466ae0ea4d3c5259aff/fixtures/finals/w2_browser_qa.spec.ts)
- 검사: `[acceptance] W2-A1 approved application offers an actual chain activation control`, `[acceptance] W2-A2 key screen actually queries the current institution key list`, `[acceptance] W2-A2 valid key form performs a real registration instead of only inspecting dates`, `[acceptance] W2-A2 registered key offers an explicit revoke control`, `[acceptance] W2-A1 displays the actual ACTIVE application status`, `[acceptance] approved application satisfies the definition-list accessibility rule`
- 계층: actual_chromium_browser; production_next; actual_socket_http
- 원 결과: {"status": "FAIL", "failed": 6, "skipped": 0, "total_browser": 12, "runner_exit": 1, "claims": ["activation control absent", "key-list GET absent", "registration POST absent despite dates inspected", "revoke control absent", "actual API ACTIVE displayed status-needs-check", "axe definition-list fails from direct dl/p structure"]}
- 한계: Six capability assertions fail; not six full write E2Es executed; Actual activation/register/revoke + new-session lifecycle and mutation failure UX NOT_RUN until A connects UI; Do not xfail/skip or infer pass from green basic CI
- 보고서: [docs/qa/w2-d-browser.md@17f78e3](https://github.com/OriginProof-3web/OriginProof/blob/17f78e300b04aa9395fb20f6f76f5313d705db3d/docs/qa/w2-d-browser.md)

```sh
W2_BROWSER_QA=1 PYTHONPATH=apps/api/src:packages/python:services/analyzer/src:services/indexer/src .uv-venv/bin/python fixtures/finals/prepare_w2_browser_qa.py
```

<a id="w3-core"></a>
### w3_core

- [PR #46](https://github.com/OriginProof-3web/OriginProof/pull/46) · QA `cbe8aaeea59e18bd4e8529bf59b618683f3e3964` · 제품 기준 `1f8ed632ea9c74091abaf2fe2ec32882038f731f`
- 파일: [services/analyzer/tests/test_w3_proof_qa.py](https://github.com/OriginProof-3web/OriginProof/blob/cbe8aaeea59e18bd4e8529bf59b618683f3e3964/services/analyzer/tests/test_w3_proof_qa.py)
- 검사: `test_w3_case`, `test_w3_manifest_reproduces_and_preserves_signed_goldens`
- 계층: Pydantic input model and deterministic core with real public ECDSA Golden vectors and synthetic trust; no DB/RPC/API/browser
- 원 결과: 65 passed (64 parameterized cases + one manifest/Golden preservation test)
- 한계: All core results have lifecycle_status=null and proof_status=NOT_RUN. Each manifest case has live_execution_status=NOT_RUN. Case counts are not final acceptance counts.
- 보고서: [docs/qa/w3-d-acceptance.md@5908457](https://github.com/OriginProof-3web/OriginProof/blob/59084570960e94a76bf041c513043816e6075ae1/docs/qa/w3-d-acceptance.md)

```sh
PYTHONPATH=packages/python .uv-venv/bin/python -m pytest -q services/analyzer/tests/test_w3_proof_qa.py
```

<a id="w3-socket-api"></a>
### w3_socket_api

- [PR #47](https://github.com/OriginProof-3web/OriginProof/pull/47) · QA `53da535ae36ca4c9616c04ad4f179bec74aac539` · 제품 기준 `121e1cade40f9ac3b001dc7aa24256d9033f0214`
- 파일: [fixtures/finals/test_w3_live_api_qa.py](https://github.com/OriginProof-3web/OriginProof/blob/53da535ae36ca4c9616c04ad4f179bec74aac539/fixtures/finals/test_w3_live_api_qa.py)
- 검사: `test_w3_actual_http_permissions_failures_and_atomic_storage`
- 계층: Actual socket HTTP / PostgreSQL / ECDSA / Anvil Reader and Writer
- 원 결과: 1 ordered integration test passed / 3.47 seconds; fresh archive on final QA code 1 passed / 3.52 seconds
- 한계: Many assertions inside one test; do not count them as separate passed pytest tests. VERIFIED does not mean ACTIVE: requires lifecycle_status=null and proof_status=NOT_RUN.
- 보고서: [docs/qa/w3-d-live-acceptance.md@5908457](https://github.com/OriginProof-3web/OriginProof/blob/59084570960e94a76bf041c513043816e6075ae1/docs/qa/w3-d-live-acceptance.md), [docs/qa/w3-d-live-environment.json@5908457](https://github.com/OriginProof-3web/OriginProof/blob/59084570960e94a76bf041c513043816e6075ae1/docs/qa/w3-d-live-environment.json)

사전 조건: 해당 QA SHA의 prepare_w3_live_qa.py로 소유한 폐기 가능한 DB/Anvil/API를 준비하고 원 보고서의 build/w3-qa/runtime.env를 사용합니다. W3_QA_API_URL, TEST_DATABASE_URL, ORIGINPROOF_TEST_ACCOUNTS, W3_QA_SIGNER_DIRECTORY, W3_QA_RPC_CONTAINER 등 환경 인계가 필요합니다. flag만 설정해서 개인 서비스에 실행하지 않습니다.

```sh
W3_LIVE_QA=1 W3_QA_DISPOSABLE=1 PYTHONPATH=apps/api/src:packages/python:services/analyzer/src .uv-venv/bin/python -m pytest -q fixtures/finals/test_w3_live_api_qa.py
```

<a id="w3-browser"></a>
### w3_browser

- [PR #47](https://github.com/OriginProof-3web/OriginProof/pull/47) · QA `53da535ae36ca4c9616c04ad4f179bec74aac539` · 제품 기준 `121e1cade40f9ac3b001dc7aa24256d9033f0214`
- 파일: [fixtures/finals/w3_browser_qa.spec.ts](https://github.com/OriginProof-3web/OriginProof/blob/53da535ae36ca4c9616c04ad4f179bec74aac539/fixtures/finals/w3_browser_qa.spec.ts)
- 검사: `D live PAYMENT_REQUEST: new issuance, fresh sessions, comparison boundaries and privacy`, `D live OFFICIAL_DOCUMENT: new issuance, fresh sessions, comparison boundaries and privacy`
- 계층: Chromium / production Next UI / actual socket API / PostgreSQL / Anvil, fresh BrowserContexts
- 원 결과: D 2 passed / 13.0 seconds; fresh archive D 2 passed / 0 skipped / 12.9 seconds. Existing A suite separately 11 passed / 0 skipped (9 mock/UI + 2 actual). Do not add overlapping suites.
- 한계: PC proof_id links only. QR generation/decoding and phone LAN NOT_RUN by D. W3 lifecycle=null/proof_status=NOT_RUN. Matching dependency cache and earlier identical product web build reused for fresh archive.
- 보고서: [docs/qa/w3-d-live-acceptance.md@5908457](https://github.com/OriginProof-3web/OriginProof/blob/59084570960e94a76bf041c513043816e6075ae1/docs/qa/w3-d-live-acceptance.md)

```sh
NODE_PATH="$PWD/apps/web/node_modules" pnpm --dir apps/web exec playwright test --config ../../fixtures/finals/w3_playwright.config.ts
```

<a id="w4-core-and-actual-asgi"></a>
### w4_core_and_actual_asgi

- [PR #49](https://github.com/OriginProof-3web/OriginProof/pull/49) · QA `0bb5da42d64b9ce298cb2de2951b327da6bc4fc7` · 제품 기준 `8011f7fe3da033c9253894a9de0fd98aa7bbcc16`
- 파일: [fixtures/finals/test_w4_lifecycle_qa.py](https://github.com/OriginProof-3web/OriginProof/blob/0bb5da42d64b9ce298cb2de2951b327da6bc4fc7/fixtures/finals/test_w4_lifecycle_qa.py)
- 검사: `test_w4_policy`, `test_w4_real_database_and_chain`
- 계층: 20 deterministic core vectors plus one ordered ASGI HTTP integration with actual PostgreSQL, ECDSA, Reader/Writer, Anvil Contract, receipts and events
- 원 결과: 21 passed / 0 skipped / 12.02 seconds; fresh archive 21 passed / 0 skipped / 12.04 seconds
- 한계: ASGI transport, not socket HTTP/browser. API trusted clock controlled, actual chain timestamp moved for expiry. Fresh DB/Anvil deployment and migrations; identical locked Python install and same product deployer image reused. Pass counts include all F items inside one live test, never add per-row.
- 보고서: [docs/qa/w4-d-acceptance.md@f2e9774](https://github.com/OriginProof-3web/OriginProof/blob/f2e9774003badb692fb4de6b89de640a155c1fa6/docs/qa/w4-d-acceptance.md), [docs/qa/w4-d-environment.json@f2e9774](https://github.com/OriginProof-3web/OriginProof/blob/f2e9774003badb692fb4de6b89de640a155c1fa6/docs/qa/w4-d-environment.json)

```sh
W4_LIVE_QA=1 W4_QA_DISPOSABLE=1 PYTHONPATH=apps/api/src:packages/python:services/analyzer/src .uv-venv/bin/python -m pytest -q fixtures/finals/test_w4_lifecycle_qa.py
```

<a id="w4-d3-preparation"></a>
### w4_d3_preparation

- [PR #49](https://github.com/OriginProof-3web/OriginProof/pull/49) · QA `78cce405357ae1f509a9bfebdbb07af4b02b2411` · 제품 기준 `8011f7fe3da033c9253894a9de0fd98aa7bbcc16`
- 파일: [fixtures/finals/prepare_w4_d3.py](https://github.com/OriginProof-3web/OriginProof/blob/78cce405357ae1f509a9bfebdbb07af4b02b2411/fixtures/finals/prepare_w4_d3.py)
- 검사: `main`, `seed`, `snapshot`
- 계층: Owned environment preparation, API seeding, read-only DB/chain/receipt/event evidence collection, socket HTTP initial verdicts only
- 원 결과: PASS preparation and fresh clone preparation; two initial VERIFIED + ACTIVE socket verdicts; six confirmed status=0x1 receipts; collector outage/recovery, DB invariance and cleanup checks PASS. 12 browser cases NOT_RUN.
- 한계: Initial API seeding is not UI issuance/rotation/revoke/consume evidence. RPC outage snapshot validates collector, not browser outage acceptance. No web build/Playwright, no submitted-transaction response-loss/failure receipt injection. Node/browser unused.
- 보고서: [docs/qa/w4-d3-browser.md@f2e9774](https://github.com/OriginProof-3web/OriginProof/blob/f2e9774003badb692fb4de6b89de640a155c1fa6/docs/qa/w4-d3-browser.md), [docs/qa/w4-d3-preparation.json@f2e9774](https://github.com/OriginProof-3web/OriginProof/blob/f2e9774003badb692fb4de6b89de640a155c1fa6/docs/qa/w4-d3-preparation.json)

```sh
W4_D3_PREPARE=1 PYTHONPATH=apps/api/src:packages/python:services/analyzer/src:services/indexer/src .uv-venv/bin/python fixtures/finals/prepare_w4_d3.py --serve
```

<a id="legacy-v1-core"></a>
### LEGACY-V1-CORE

- [PR #30](https://github.com/OriginProof-3web/OriginProof/pull/30) · QA `54f09e4e8db162db078c9347015c47cae881301d` · 제품 기준 `3295a71c10a1a99c523d3cfefde91b5737b737ac`
- 파일: [services/analyzer/tests/test_v1_qa_regression.py](https://github.com/OriginProof-3web/OriginProof/blob/54f09e4e8db162db078c9347015c47cae881301d/services/analyzer/tests/test_v1_qa_regression.py)
- 검사: `test_existing_card_fixture_through_real_verification_core`
- 계층: actual_verification_core; ephemeral_real_ecdsa; in_memory_mock_repository_reader
- 원 결과: {"status": "PASS_REGRESSION_ONLY", "passed": 2, "normal": "VERIFIED + ACTIVE", "amount_change": "TAMPERED + ACTIVE / AMOUNT_MISMATCH"}
- 한계: CARD_PAYMENT_NOTICE v1, not PAYMENT_REQUEST/OFFICIAL_DOCUMENT finals-v2; Golden digest is verified and ephemeral in-memory signer signs; Golden not modified; Source report initial execution 3295a71 plus D working tree; committed code54f09e4 identifies same D source
- 보고서: [docs/qa/w1-results.md@94488b1](https://github.com/OriginProof-3web/OriginProof/blob/94488b13d80df991bc5b861d1d4d44da267355ee/docs/qa/w1-results.md)

```sh
python -m pytest -q services/analyzer/tests/test_v1_qa_regression.py
```

## 현재 차단·재검사 목록

| ID | 상태·근거 | 선행 담당 | D가 연결 후 할 일 |
| --- | --- | --- | --- |
| G01 | phase/W5와 A/B/C 공통 통합 검증 SHA·웹/API/Contract manifest·기동 안내가 아직 없습니다. [PR #37](https://github.com/OriginProof-3web/OriginProof/pull/37) | `W5-C3`, `W5-A1`, `W5-A2`, `W5-A3`, `W5-B3` | 소유자가 전달한 후보를 read-only 확인 후 W5-D2를 같은 SHA에서 실행합니다. |
| G02 | PR51: W2 브라우저 6 통과/6 실패/0 skipped. 활성화·키 목록/등록/폐기·ACTIVE 표시·definition-list 결함. [PR #51](https://github.com/OriginProof-3web/OriginProof/pull/51) | `W2-A1`, `W2-A2`, `W5-A1`, `W5-A2` | A 수정 handoff 후 실패 6개와 전체 기관/키 흐름을 재검사합니다. |
| G03 | A QR 후속 PR48은 열려 있으며 D의 실제 QR 생성/해석→새 세션 조회는 미실행입니다. [PR #48](https://github.com/OriginProof-3web/OriginProof/pull/48) [PR #47](https://github.com/OriginProof-3web/OriginProof/pull/47) | `W3-A2`, `W3-D3`, `W5-D2` | 승인된 QR 화면과 최신 API의 같은 후보에서 D가 재현합니다. |
| G04 | PR49의 D3 환경/수집기 준비는 통과했으나 실제 W4 브라우저 사례 12개는 NOT_RUN입니다. [PR #49](https://github.com/OriginProof-3web/OriginProof/pull/49) | `W4-A1`, `W4-A2`, `W4-A3`, `W4-D3`, `W5-D2` | 연결 화면 handoff 후 실제 UI 변경과 DB/체인·receipt·새 세션 결과를 대조합니다. |
| G05 | 후보 API 요청 제한·선택 응답/서명기·known synthetic secret Git/체인 검사 통과. 전체 통합 웹 접근성·DOM/로그/저장소 감사는 미실행입니다. [실제 보고](w5-d-api-verification.md) | `W5-C1`, `W5-A2`, `W5-D2` | A/C 화면 인계 뒤 UI 한계/복구·접근성과 전체 공개 surface를 검사합니다. |
| G06 | 후보 실제 projection replay/API process restart/reorg와 다른 RPC identity guard 통과. 다른 Contract 실제 서명 제출은 별도 B 경계 인계가 필요합니다. [실제 보고](w5-d-api-verification.md) | `W3-B2`, `W5-B1`, `W5-B2`, `W5-B3`, `W5-C2`, `W5-D2` | 현재 scoped 결과를 소비하고 통합 후보·직접 서명 재사용의 범위를 B/C와 대조합니다. |
| G07 | 혼합 RPC/reorg 스택의 추가 재기동 뒤 Reader UNAVAILABLE가 재현됨. 기본 fresh18PASS와 구분, 원인·제품 결함 여부 미확정. [재현·실패 보고](w5-d-api-verification.md) | `W5-B1`, `W5-B2`, `W5-C2` | B/C 확인·수정 인계 뒤 D가 같은 mixed 명령으로 재검사합니다. |

C의 [PR #37](https://github.com/OriginProof-3web/OriginProof/pull/37)은 Draft이며 현재 임시 base가 `phase/W4`입니다. 작성자가 W4 병합 금지를 명시했습니다. W5 준비 코드와 이후 W6 실제 Compose 결과를 구분합니다. 다른 담당자의 기능을 D가 대신 구현하거나 C의 통합 승격을 D 완료 조건으로 추가하지 않습니다.

D2의 구체적인 실행 순서·증거 형식은 [전체 흐름 계획](w5-d-e2e-plan.md)에 있습니다. 각 G 항목의 PR/작업 ID를 차단 근거로 연결했으며, 추측으로 새 결함 이슈를 만들지 않았습니다.

## 완료 판단

D1: 15개 기준의 매핑과 누락을 기록했습니다. 사실 확인·리뷰 후 근거가 보완되면 추적표를 갱신합니다. D2: 동일 통합 SHA의 세 역할 UI·실제 API/DB/chain·오류·접근성 실행 결과가 필요합니다. D3: D1/D2와 P0 완료 확인 후에만 선택 기능을 논의하며 현재 보류입니다.

## 준비 문서 검증

`make bootstrap-check`와 `make env-fingerprint`를 실행해 통과했습니다. Node 22.18.0, pnpm 11.19.0, Python 3.13.7(지정 3.13.0과 patch 차이), uv 0.8.17을 기록했습니다. 서비스는 기동하지 않았습니다. 호스트 forge 미설치는 참고 정보이며 Foundry 컨테이너 기준을 유지합니다. lockfile·container config 해시와 검증 범위는 JSON의 `preparation_validation`에 있습니다.

F03의 기존 v1 만료 코드는 [test_verification.py@3295a71](https://github.com/OriginProof-3web/OriginProof/blob/3295a71c10a1a99c523d3cfefde91b5737b737ac/packages/python/tests/test_verification.py)의 `test_expired_proof_is_not_reported_as_verified`입니다. 기대값 `INCONCLUSIVE/PROOF_EXPIRED/EXPIRED`를 읽어 확인했으며, 이번에 실행하거나 과거 전체 suite 결과를 개별 실행 결과로 세지 않았습니다. 후속 명령은 JSON `F03.existing_unexecuted_test`에 기록했습니다.
