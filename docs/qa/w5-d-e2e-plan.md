# W5-D2 — 세 역할 P0 E2E 실행 계획

담당 D `@yijun0330`. 기준은 [계획서 15.6·15.9·16절](../development_plan.md)과 [ADR 0001](../adr/0001-finals-contracts.md)입니다. 확인일 2026-10-04.

**아래 15개 통합 UI 사례는 모두 NOT_RUN입니다. 후보 독립 API·체인 검사는 별도로 실행됐습니다.** A/B/C의 같은 W5 통합본을 받은 뒤 D가 독립 실행합니다. 현재 `phase/W5`가 없고 최신 `integration@3295a71c10a1a99c523d3cfefde91b5737b737ac`에는 그 기능 통합본이 없습니다. [D1 추적표](w5-d-acceptance.md)의 과거 부분 성공은 이번 전체 흐름 성공을 대신하지 않습니다.

## 후보 부분 실행과 통합 UI 판정

[별도 실제 보고](w5-d-api-verification.md): 기본 fresh18PASS/0FAIL, 혼합 장애17PASS/1FAIL입니다. D2-04의 권한, D2-05 unknown 조회, D2-08 중지 중 새 발행 거부, D2-13 실제 projection replay/restart/reorg, D2-14 기본 rate/body/Origin과 선택 API/키/체인/Git 검사를 실행했습니다. D2-07 v1 만료와 fresh ASGI lifecycle도 별도 통과했습니다.

API seed·ASGI·socket HTTP 결과는 브라우저 관리·QR·키보드 성공이 아닙니다. 혼합 RPC/reorg 스택에서 추가 재기동 후 Reader UNAVAILABLE가 재현돼 B/C 원인 확인을 기다립니다. 제출 뒤 hash loss는 프로세스 내부 주입이며 실제 socket 응답 소실이 아닙니다. 전체 UI/로그 감사는 여전히 미실행입니다.

## 1. 실행 전 인계 확인

| 제공할 내용 | 담당 작업 | D가 확인할 조건 |
| --- | --- | --- |
| 웹 연결·화면 상태·접근성 수정 | `W5-A1/A2/A3` | W2 승인/활성화·키 관리, W3 두 유형/QR, W4 교체/폐기/consume 화면이 같은 API에 연결됩니다. [PR #51](https://github.com/OriginProof-3web/OriginProof/pull/51)의 실패 6개, [PR #48](https://github.com/OriginProof-3web/OriginProof/pull/48)의 QR와 [PR #49](https://github.com/OriginProof-3web/OriginProof/pull/49)의 D3 사례를 재검사할 수 있어야 합니다. |
| canonical Reader/Writer·manifest·배포 권한·projection/reorg 절차 | `W5-B1/B2/B3` | ABI/주소/source SHA/chain ID/deployment ID/배포 block·hash가 일치합니다. Foundry 컨테이너를 사용하며 호스트 forge를 필수로 요구하지 않습니다. |
| API 인증/권한/제한·Operation/감사·reconciliation·기동/seed | `W5-C1/C2/C3` | API 모델/OpenAPI와 실제 설정·명령·migration·보호된 계정 준비 안내를 받습니다. pending/UNKNOWN/FAILED와 current lifecycle을 구분합니다. |
| 공통 검증 대상 | 통합 조율 C, 각 소유자 | phase/통합 후보의 전체 SHA, 웹 빌드 SHA, QA 코드 SHA와 manifest를 기록합니다. 외부 작성자 리뷰는 실제 리뷰 링크만 사용합니다. |

위 인계가 없으면 관련 사례를 BLOCKED/NOT_RUN으로 기록합니다. D는 자기 사례·실행·재현 결과를 제공하고, A/B/C의 제품 수정과 C의 단계 승격은 각 담당자가 수행합니다. 단계 브랜치가 없는 동안 D의 독립 문서 준비·후보 API/체인 검사를 계속할 수 있습니다.

### 현재 C 후보와 명령의 범위

C의 [PR #37](https://github.com/OriginProof-3web/OriginProof/pull/37)은 Draft `9651062c9f36e124b76796278c996764678e1c77`이며 임시 base `phase/W4`로 **W4 병합 금지**가 명시돼 있습니다. [이 head의 integration 계약](https://github.com/OriginProof-3web/OriginProof/blob/9651062c9f36e124b76796278c996764678e1c77/docs/api/w5_c_integration_contract.md)은 준비 후보의 근거입니다. 오래된 초안 첫 문단이나 W6 실행 결과를 W5 현재 구현/통합 성공으로 사용하지 않습니다.

- 후보 `make finals-up`, `make finals-seed`는 **현재 integration Makefile에 없습니다**. 공통 후보로 인계된 뒤 실제 Makefile·부작용·격리 환경을 확인하고 사용합니다.
- 현재 준비 checkout에서 쓸 수 있는 구조/환경 명령은 `make bootstrap-check`, `make env-check`, `make env-fingerprint`입니다. 환경 검사는 서비스 준비 상태나 실제 API 연결을 증명하지 않습니다.
- `make smoke`에는 서비스가 필요합니다. `make mvp-e2e`는 기동·migration·seed·배포를 수반하며 기존 카드 회귀 범위입니다. 본선 전체 성공으로 사용하지 않습니다.
- `make demo-reset`이나 `reset`을 개인/공유 DB에 실행하지 않습니다. D 실행은 별도 이름·포트·경로로 소유한 폐기 가능한 합성 환경에서 합니다. 기존 `.env`·서명기·manifest·서비스를 덮어쓰지 않습니다.

## 2. 데이터·환경 준비

1. 해당 phase/통합 후보를 새 checkout에 고정하고 적용 지침·lockfile을 확인합니다. Node **22.18.0**, 기본 provider **mock**, 기본 모델 **gpt-6-luna**를 사용합니다. 의도된 개인 설정은 유지하며 비밀값을 출력하지 않습니다. Python·Docker·Compose·uv·pnpm 차이와 container config/lockfile 해시도 기록합니다.
2. 합성 `Origin Mock Bank`와 `Origin Mock Office`, 운영자 1명·기관별 발행자 2명·지정 수신자와 다른 수신자 2명 등 세 역할을 준비합니다. 계정/비밀번호는 보호된 로컬 저장소만 사용하고 로그·스크린샷·Git에 넣지 않습니다.
3. 역할마다 독립 BrowserContext를 사용합니다. 사용자 조회/비교/consume은 발행자 세션을 재사용하지 않습니다. 적어도 한 기관은 **브라우저에서 신규 신청 → 승인 → 체인 활성화 → 키 등록**을 합니다. 미리 활성화한 seed만으로 온보딩 성공을 선언하지 않습니다.
4. 새 `PAYMENT_REQUEST`와 `OFFICIAL_DOCUMENT`를 만듭니다. 발행 당시 키/Proof 기간·domain·schema·chain ID·수신자 binding은 승인 계약을 따릅니다. 실제 자료가 아닌 합성 입력을 사용하고 v1 Golden을 변경하거나 v2로 재서명하지 않습니다.
5. D1에 링크된 W2/W3/W4의 helper·사례를 재사용할 수 있으나, 현재 후보의 API/ABI와 맞는지 확인하고 그 QA 변경 SHA를 기록합니다. 앞 단계 helper가 후보 통합본에 존재하는 것으로 가정하거나 개인 경로를 유일한 근거로 쓰지 않습니다.
6. 실제 web origin을 API 허용 목록에 맞춥니다. PR37 후보의 `API_BROWSER_ORIGINS`에는 사용하는 정확한 origin이 필요합니다. 다른 origin/CSRF 실패와 미연결 UI를 혼동하지 않습니다. 정상 흐름과 요청 제한 검사는 rate limiter/프록시 peer 영향이 섞이지 않도록 격리합니다.

API seed는 준비 자료입니다. 화면의 관리 작업을 API 호출로 대신해 E2E PASS로 기록하지 않습니다. `page.route` 성공 응답이나 미리 만든 verdict는 연결 성공 근거가 아닙니다. PC 로컬 QR/링크를 기본으로 하고 휴대폰 스캔은 설정한 LAN 환경에서 실행한 경우만 기록합니다.

## 3. 순서대로 실행할 사례

각 행은 준비 시점 **NOT_RUN**입니다. 행 안의 하위 동작별 기대/실제값도 기록해 부분 성공이 전체 PASS로 확대되지 않도록 합니다.

| 순서 · 사례 | 역할·동작 | 기대와 관측 근거 | F 기준 |
| --- | --- | --- | --- |
| D2-01 온보딩 | 기관 신규 신청 → 운영자 검토 승인/반려 → 활성화 → 기관 키 생성·등록·목록·재조회 | 미승인/반려/DB 승인 체인 미완료는 키 등록·발행 거부. 성공은 receipt 1 confirmation + canonical 상태 재조회 + DB + UI·새 세션 일치. 개인키 입력/노출 없음. | F09, F10, F15 |
| D2-02 두 유형 신규 발행 | 두 기관이 브라우저에서 새 지급 요청·문서 발행 → 다른 지정 수신자 새 세션으로 조회/전체 비교 | 실제 새 ID·서명·저장·상태 등록. `PROOF_ONLY`는 내용 일치를 주장하지 않음. 전체 비교는 `VERIFIED + ACTIVE/FULL_COMPARISON`; 현재 RPC 근거와 비교 범위를 함께 확인. | F01, F14 |
| D2-03 QR·단일 변조·누락 | 새 Proof QR를 생성/해석 → 새 사용자 세션 조회 → 금액 +1 또는 문서번호 하나 변경 → 누락 자료 비교 | QR/링크는 공개 ID만 전달. 실제 불일치 `TAMPERED`와 필드 사유, 누락만 있으면 `INCONCLUSIVE/PARTIAL_COMPARISON`, 누락+불일치는 `TAMPERED`. unsigned 입력 변경과 signed envelope 변조를 구분. | F01, F02, F15 |
| D2-04 권한·공개성 | 익명/다른 수신자/타 기관/운영자로 키·Proof·Operation·감사·제한 payload 조회/변경 시도; actor/기관 ID 주입·CSRF·Origin 거부 | API 401/403 또는 존재 은닉 404, 형식 주입은 계약대로 422. 숨겨진 버튼만으로 권한 검사를 대신하지 않음. 거부 전후 해당 기관 DB/chain/event 불변. 일반 운영자는 제한 payload·서명/consume 권한을 자동 획득하지 않음. | F05, F10, F14, F15 |
| D2-05 미등록 | 실제 저장소에 없는 ID와 미등록 발행자 자료 조회 | `NOT_REGISTERED`와 실제 원인; 위조라고 단정하지 않음. 키 미등록 `INCONCLUSIVE/KEY_NOT_FOUND`와 혼동 금지. | F06 |
| D2-06 정상 키 교체 | 기관 UI 새 키 준비 → 등록 확정 → 발행 키 전환 → 새 발행; 수신자 새 세션 과거/신규 조회 | 전환 키와 실제 발행 서명키 일치. 이전 정상 Proof는 키 교체/키 기간 종료 후에도 정책에 따라 유효. 이전 키 자동 revoke 금지. 미확정 새 키로 발행 금지. | F01, F08, F12 |
| D2-07 만료 | 두 유형 만료 직전/경계/직후 조회·사용, v1 만료 회귀 별도 | QA가 소유한 환경의 trusted clock·chain 시간 기록. v2 수행 검사 성공은 `VERIFIED + EXPIRED`, 사용 거부; v1 `INCONCLUSIVE + EXPIRED`. OS 시간/개인 데이터를 바꾸지 않음. | F03 |
| D2-08 기관 중지 | 운영자 UI 기관 중지 → 중지 중 새 발행 직접 시도 → 새 수신자 세션 기존 Proof 검증 → 복귀 | 새 발행 거부와 상태 불변, 기존 `ISSUER_SUSPENDED`·사용 불가; 복귀 뒤 실제 현재 상태 일치. 이 새 발행 거부는 앞선 W4 D 자료의 누락 검사였고 후보 socket API 검사에서 보완됨. UI/새 세션은 미실행. | F11 |
| D2-09 유출 키·Proof 폐기 | 정상 교체와 다른 유출 키 폐기; 기관 UI Proof 폐기; 수신자 새 세션 재검증 | 과거 Proof `ISSUER_KEY_REVOKED` 또는 `PROOF_REVOKED`, 현재 사용 불가. 반복 적법 폐기는 tx/event 불증가. 소비 후 폐기는 소비 이력을 보존. 여러 lifecycle의 대표 우선순위와 모든 사유도 ADR대로 대조. | F07, F08 |
| D2-10 소비·재사용 | 지정 수신자 UI 소비 → 새 세션 재조회 → 새 ID 재사용; 같은 ID 재시도; 발행자/수신자 병렬 연결 | 체인 `ProofConsumed` 전이 한 번. 같은 ID는 기존 Operation/tx, 새 ID는 `REPLAY_DETECTED`. 다른 입력 ID 재사용은 conflict. 문서형 consume 거부. API DB lock만으로 원자성 성공을 주장하지 않음. | F04, F10, F14 |
| D2-11 조회 불변·직접 우회 | 여러 세션 반복 조회; 타 기관/틀린 binding/gateway 외 직접 Contract 변경 | 조회 전후 Operation/Audit/event/consume 불변. 직접 우회 호출 실패 receipt와 현재 상태 불변. 서버의 세션 actor 전달과 체인의 commitment 대조라는 trusted gateway 범위를 기록. | F04, F05, F10, F14 |
| D2-12 timeout·중복·실패 | 중복 클릭·같은 ID 동시 요청·제출 전 RPC 오류·제출 응답 유실/receipt 미확인·실패 receipt·API 재시작 | 같은 작업 조회/복구, 새 nonce의 무조건 재전송 금지. 확실한 실패는 실패, 불명확한 제출은 보류. Proof/키/체인 변경 중복 없음. 실제 제출 후 응답 유실과 단순 RPC stop을 따로 기록. | F08, F12, F13 |
| D2-13 상태·동기화·배포 | Operation/감사/DB-chain reconciliation·Indexer 재시작/replay/reorg·잘못된 deployment/chain | 주체/대상/시각·필터·기관 격리·pagination. checkpoint 저장 순서와 rewind 공통 조상, canonical Reader 상태 일치. projection SYNCED만으로 현재 유효성을 보증하지 않음. 같은 chain ID 재배포도 새 deployment로 구분. | F12, F13, F14 |
| D2-14 제한·비밀정보 | 정상 흐름과 분리해 C 계약의 입력 크기/timeout/요청 제한을 초과; 합성 응답/URL/QR/DOM/저장소/로그/키 파일/Git/chain 점검 | 408/413/429 등 계약의 오류·Retry-After·복구를 기록. 제한 임계치는 실제 C 설정을 사용. 개인키·인증값·원문/제한 필드 비노출; 보호된 의도적 세션 저장/공개 signer와 노출 결함 구분. `make security` 출력은 검사 통과 아님. | F15 |
| D2-15 접근성·경로 회복 | 키보드만으로 신청·승인·발행·조회/비교·폐기·consume; 새로고침/뒤로가기/로그아웃/세션 만료·작은 화면 | focus 이동/유실, label·오류/결과 읽기·대비를 기록하고 axe 결과를 보조 근거로 사용. 미등록/범위/시각/network/현재 상태 안내 정확. 화면 이동이나 재시도가 허위 성공/중복 변경을 만들지 않음. | F01~F15의 웹, 특히 F15 |

시간·폐기·중지·소비를 바꾸는 사례마다 별도 합성 Proof를 사용해 앞선 변경이 다음 기대값을 오염시키지 않도록 합니다. 여러 상태 동시 존재 검사는 의도된 조합임을 명시합니다. 서비스 stop·실패 주입은 QA가 소유한 자원에만 적용하고 종료 후 정리 결과를 기록합니다.

### PR37 상태 계약을 소비할 때 추가 대조

다음은 **후보 head 계약**이며 통합 후 실제 생성 모델/API와 재대조합니다.

- `UNKNOWN/SUBMITTED`: `recovery_required`와 `RECOVER_SAME_OPERATION`; `PENDING_SUBMISSION`: `RETRY_SAME_REQUEST`; `CONFIRMED/FAILED`: `NONE`. FAILED의 자동 재전송을 허용하지 않습니다.
- `GET /v1/operations`, `GET /v1/audit-events`: 주체·기관·대상·status·limit/offset 접근과 오류를 확인합니다. 내부 recovery 입력/제한 payload는 공개하지 않습니다.
- `GET /v2/issuer/proofs/{proof_id}/reconciliation`: 자기 기관/운영자 접근 범위·DB/canonical Reader·nullable consistency·deployment 일치, 제한 payload/binding 비노출을 검사합니다.
- `GET /v1/chain-sync`: STARTING/SYNCED/CATCHING_UP/WAITING_CONFIRMATIONS/RECOVERING/STALE/DISABLED 표시와 `HISTORICAL_EVENTS_ONLY`의 한계를 확인합니다. 현재 lifecycle은 canonical Reader로 판정합니다.
- readiness의 DB migration·합성 계정·signer 권한·배포 주소/code·projection 검사와 미준비 503을 확인합니다. DB 승인/기동 HTTP 200만으로 발행 준비 성공을 선언하지 않습니다.
- W5 후보 보안 검사 목록만으로 W4 Proof register/revoke/consume까지 전수 확인됐다고 하지 않습니다. D2-04/09/10/11에서 실제 변경 API별 인증·CSRF·입력/요청 제한·소유권을 별도로 대조합니다.

## 4. 실행 명령과 기록

후보 checkout의 실제 Makefile·package scripts를 확인하고 [15.9절](../development_plan.md)을 따릅니다. 아래는 표준 명령이며 이번 문서 작성에서 기능 검사로 실행하지 않았습니다.

```sh
make bootstrap-check
make env-check
make env-fingerprint
# 본선 서비스가 준비된 환경에서
make smoke
make test-api
make test
make test-contracts
UV_PROJECT_ENVIRONMENT=.uv-venv uv run pytest -q services/indexer/tests
pnpm --filter originproof-demo-web lint
pnpm --filter originproof-demo-web typecheck
pnpm --filter originproof-demo-web test
pnpm --filter originproof-demo-web build
pnpm --filter originproof-demo-web test:e2e
```

기본 suite나 mock E2E가 자동으로 위 사례를 덮는다고 가정하지 않습니다. opt-in DB/chain/browser 검사의 필요한 flag·명령은 현재 QA 파일/보고서와 대조해 실행 증거에 적습니다. `make lint`, `make typecheck`도 변경 범위에 맞게 사용하며 Python typecheck는 현재 compileall입니다. 기존 카드 회귀 `make mvp-test`/`make mvp-e2e`는 본선 검사와 결과를 분리합니다.

| 사례별 기록 필드 | 내용 |
| --- | --- |
| ID·검증 계층 | D2/F ID, UI/core/ASGI/socket/DB/chain/indexer 등 실제 사용 계층 |
| 실행 기준 | 제품 전체 SHA, QA SHA, 웹 빌드 SHA, lockfile·container config 해시·환경 차이 |
| 데이터·배포 | 합성 fixture 버전, 기관 별칭, 공개 Proof/Operation ID, chain ID·deployment ID·contract 주소·배포/관측 block/hash |
| 기대/실제 | 수행한 UI 동작, 요청 경로·HTTP 상태, 검사 범위/check/reason/lifecycle, 명령·종료 코드·pass/fail/skip 수 |
| 변경 근거 | DB 전후 요약, tx hash·receipt status/confirmations·canonical 재조회·event 개수; 같은 ID 재조회와 새 변경 구분 |
| 화면·재현 | 안전하게 마스킹한 스크린샷/CI run/고정 SHA 검사 파일·보고서 링크, 브라우저/세션/새로고침 조건 |
| 결론·후속 | PASS/FAIL/BLOCKED/NOT_RUN, 실패 입력·원인 확인 여부·담당 작업 ID/PR, 재검사 SHA·결과 |

전체 envelope·payload·계정 ID/비밀번호·토큰·salt/binding·private key·recovery 원문을 보고서에 넣지 않습니다. request ID/tx/공개 ID도 합성 자원임을 확인합니다. 공개 endpoint 밖의 개인 주소는 기록하지 않습니다. 실패 원인을 모르면 관측 사실과 가설을 구분합니다.

## 5. 종료와 후속

1. D2-01~15와 각 하위 사례의 실제 결과를 D1 원본 JSON/보고서에 연결합니다. 실패를 xfail/skip으로 바꿔 완료시키지 않습니다.
2. A UI 실패, B 체인/Adapter/indexer 실패, C API/DB·권한 실패를 각 소유자의 작업/PR에 재현 자료로 연결합니다. 수정 후 **수정된 SHA**를 D가 재검사합니다. 다른 소유자 코드의 대리 구현·승인·병합은 이번 범위가 아닙니다.
3. QA가 만든 서비스·임시 자료 정리와 개인/기존 서비스 보존을 확인합니다. D 자료의 사실 확인·외부 리뷰를 받은 뒤 단계 근거로 제공합니다.
4. P0 D1/D2 완료 확인 뒤에만 `W5-D3` 선택 기능을 논의합니다. 현재 로그인 확장·인터넷 공개·AI/OCR·테스트넷은 보류입니다. 기존 정책을 다시 미결정으로 바꾸거나 유료 모델 호출을 하지 않습니다.

W5 실행을 끝냈다는 것은 준비 표나 CI가 있다는 뜻이 아닙니다. 같은 통합본의 실제 세 역할 흐름·실패/접근성 근거가 있어야 하며, 단계 승격과 W6 안정성 검증은 별도 절차입니다.
