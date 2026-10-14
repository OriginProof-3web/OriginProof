# W4-D3 — 실제 브라우저 실행 준비

- 담당 D / 여인준님 `@yijun0330`, 준비일 2026-10-03.
- 제품 기준 `phase/W4@8011f7fe3da033c9253894a9de0fd98aa7bbcc16`.
- 작업 branch `test/w4-d-lifecycle-qa`, [PR #49](https://github.com/OriginProof-3web/OriginProof/pull/49).
- 기준: [계획서 §15.5](../development_plan.md), [ADR 0001](../adr/0001-finals-contracts.md).
- **실행 절차·합성 입력·초기 환경·증거 수집 준비입니다. D3 실제 브라우저는 NOT_RUN입니다.**
  A W4-A1/A2/A3 화면 연결 후 같은 단계 코드에서 실행합니다.

## 1. 준비물과 인계

| 자료 | 내용 |
| --- | --- |
| [prepare_w4_d3.py](../../fixtures/finals/prepare_w4_d3.py) | 기존 D1/D2의 새 tmpfs PostgreSQL·Anvil 배포 fixture 재사용. 실제 socket HTTP API, 새 계정·승인·활성화·초기 키·과거 Proof 준비. 이후 읽기 전용 snapshot 수집 |
| [w4_d3_cases.json](../../fixtures/finals/w4_d3_cases.json) | 두 유형의 교체·폐기와 요청형 consume·재사용, 읽기·권한·장애·미확정 화면의 12개 기대 사례 |
| [D1/D2 결과](w4-d-acceptance.md) | 기존 21 passed 증거. 브라우저 결과와 합산하지 않음 |
| [키 교체 계약](../api/w4_c_key_rotation_contract.md) · [상태/consume 계약](../api/w4_c_proof_lifecycle_contract.md) | C 현재 API. `/v1/issuer/keys/rotate`, `/v2/issuer/proofs`, revoke/consume/verify/Operation |

준비기는 키 교체·Proof 폐기·consume을 수행하지 않습니다. 초기 Proof는 정상 교체 뒤에도
과거 발행이 유효한지 확인하기 위한 데이터입니다. D3에서 검사할 **새 발행과 상태 변경은
실제 화면에서 수행**합니다. API 준비 성공을 해당 UI 동작의 성공으로 기록하지 않습니다.
브라우저 locator와 자동 실행 spec은 A의 실제 연결 화면을 확인한 뒤 맞춥니다.

## 2. 환경과 실행 명령

Node **22.18.0**, 현재 `.tool-versions`·frozen lockfile, Python 3.13·uv를 사용합니다.
provider mock/model gpt-6-luna이며 유료 호출은 없습니다. 개인 `.env`·기존 DB/RPC를 받지 않습니다.
제품 deployer 이미지는 기존 fixture의 `PRODUCT_SHA` 라벨을 검사합니다. 준비기는 API·코어·Contract·
deployer Dockerfile이 그 SHA와 다른 경우 중단합니다. A 연결 후 API/Contract 기준도 바뀌었다면
C/B와 최신 phase를 맞추고 fixture의 SHA·이미지를 갱신해야 합니다. 오래된 이미지와 새 제품을
혼합해 완료 판정하지 않습니다. 호스트 forge는 필요하지 않습니다.

최초 clone에서는 `UV_PROJECT_ENVIRONMENT=.uv-venv uv sync --frozen`으로 의존성을 준비합니다.
현재 제품 기준의 이미지가 없다면 동일 clone에서 공식 Dockerfile로 만듭니다.

```sh
docker build -f infra/docker/deployer.Dockerfile \
  --label org.opencontainers.image.revision=8011f7fe3da033c9253894a9de0fd98aa7bbcc16 \
  -t originproof-w4-d-qa-deployer:8011f7f .
```

기존 동명 이미지가 다른 제품이면 덮어쓰지 않고 fixture의 새 이름·기준을 함께 지정합니다.
현재 이번 준비에는 이미 검증한 동일 제품의 이미지와 locked Python 설치를 재사용했습니다.

기본 명령은 **준비 → 초기 HTTP/DB/chain 확인 → 이번 자원만 종료**합니다.

```sh
W4_D3_PREPARE=1 \
PYTHONPATH=apps/api/src:packages/python:services/analyzer/src:services/indexer/src \
.uv-venv/bin/python fixtures/finals/prepare_w4_d3.py
```

macOS에서 Xcode license 대신 설치된 Command Line Tools를 사용하는 이 컴퓨터의 명령에는
`DEVELOPER_DIR=/Library/Developer/CommandLineTools`를 앞에 붙입니다. 개인 설정을 바꾸지 않습니다.

A 화면 연결 후 `--serve`로 새 자원을 준비한 채 유지합니다.

```sh
W4_D3_PREPARE=1 \
PYTHONPATH=apps/api/src:packages/python:services/analyzer/src:services/indexer/src \
.uv-venv/bin/python fixtures/finals/prepare_w4_d3.py --serve
```

- 출력의 새 loopback API 주소와 전용 결과 디렉터리를 사용합니다.
- 다른 터미널에서 `ORIGINPROOF_API_ORIGIN=<이번 API 주소>`를 지정하고 현재 웹의 공식
  `pnpm --filter originproof-demo-web build`를 실행합니다. 같은 origin으로
  `pnpm --filter originproof-demo-web exec next start --hostname 127.0.0.1 --port <빈 포트>`를 실행합니다.
  Next rewrite가 build에 포함되므로 기존 다른 API를 가리키는 build를 재사용하지 않습니다.
- 준비기 터미널에 `snapshot`을 입력하면 새 `snapshot-<id>.json`을 만듭니다. `stop` 또는 Ctrl+C로
  이번 API/DB/Anvil/네트워크만 종료합니다. 웹 프로세스는 웹 터미널에서 종료합니다.
- API 요청/DB 쓰기를 page.route 등으로 가짜 성공 처리하지 않습니다. UI가 없는 동작을
  `APIRequestContext`로 실행하고 브라우저 검사 통과로 세지 않습니다.

## 3. 생성 데이터·계정·보존

새 디렉터리 `build/w4-d3/<uuid>/`는 Git ignore 대상이며 권한 0700, JSON은 0600입니다.
이미 있는 출력은 덮어쓰지 않습니다. 다음 파일은 **로컬 전용**이며 PR에 올리지 않습니다.

| 파일 | 사용 방법 |
| --- | --- |
| `accounts.json` | operator, bank issuer, office issuer, 지정 recipient, other_recipient의 새 임의 비밀번호. 로컬 파일로 로그인하며 터미널·스크린샷·PR에 비밀번호를 출력하지 않음 |
| `inputs.json` | 기관별 `old_key_id`, `historical_proof_id`, 현재 유효한 교체 기간, 새 발행/별도 consume 발행 입력. 동적 recipient_id와 합성 내용 포함 |
| `session.json` | 이번 API 주소와 **이번 owned Anvil 이름**. 다른 DB/RPC/컨테이너를 대상으로 삼지 않음 |
| `baseline.json` | 초기 DB 선택 키·Proof key ID·Operation·Audit, 실제 chain block/hash·상태·이벤트·receipt |
| `results.json` | 12개 사례의 최초 `NOT_RUN`, evidence 빈 목록. 실제 UI 결과 확인 뒤 상태·근거를 작성 |
| `summary.json` | 초기 준비 성공과 자원 종료 여부. `d3_browser=NOT_RUN`은 준비만으로 바뀌지 않음 |

Bank는 요청형, Office는 문서형입니다. 활성 키는 기관당 1개, 과거 Proof는 유형당 1개입니다.
기간은 초기 키 14일, Proof 7일이며 매 실행마다 현재 시각으로 생성합니다. 만료 -1/0/+1 경계는
D1의 통제 시간 검사와 구분합니다. 새 UI 발행의 요청 ID·대상 참조/문서번호는 사례마다 바꿔
기존 발행 idempotency 응답을 새 발행 성공으로 잘못 세지 않습니다.
예시의 `consume_issue_input`은 요청형 별도 새 발행에 사용합니다. 문서형 consume은 거부 대상입니다.
종료하면 tmpfs DB·체인은 제거되므로 예전 accounts.json은 다음 새 환경에서 재사용하지 않습니다.

## 4. 실제 브라우저 실행 순서

각 역할 전환은 새 BrowserContext/독립 프로필로 합니다. 쿠키·localStorage·인메모리 상태를
재사용하지 않습니다. 창 새로고침만 한 결과를 새 세션으로 표현하지 않습니다.
자동화 시 trace/video/자동 스크린샷은 끄고 필요한 합성 화면만 자격증명·제한 값 제거 후 저장합니다.

### 흐름 A — 두 유형 각각 키 교체 → 새 발행 → 폐기 → 재검증

1. 초기 `snapshot`을 저장하고 해당 issuer로 **새 세션 로그인**합니다.
2. 화면에서 정상 교체를 실행합니다. 실제 POST `/api/v1/issuer/keys/rotate`와 Operation을 기록합니다.
   CONFIRMED 뒤 키 목록을 새로 조회해 새 selected key와 기존 key의 selected=false를 확인합니다.
   정상 교체가 이전 키를 유출 폐기하지 않았는지 확인합니다.
3. 화면에서 새 Proof를 발행합니다. 준비된 입력을 사용하되 **새 요청 ID·합성 참조**를 씁니다.
   등록 CONFIRMED, DB key_id=새 선택 키, 실제 chain key hash 일치와 성공 receipt를 기록합니다.
4. 별도 지정 recipient 세션에서 과거·새 Proof를 조회합니다. 둘 다 VERIFIED + ACTIVE,
   signature/proof_status PASS, 실제 수행한 scope/checks를 확인합니다.
5. issuer가 화면에서 새 Proof를 폐기합니다. Operation CONFIRMED 뒤 `snapshot`을 저장합니다.
6. **새 recipient 세션**에서 재검증합니다. VERIFIED + PROOF_REVOKED,
   PROOF_REVOKED 사유·현재 사용 불가와 chain revoked_at을 확인합니다.
7. 적법한 반복 폐기는 상태를 유지하며 추가 tx/event가 없어야 합니다. 화면이 반복 동작을
   제공하지 않으면 버튼 제한을 기록하고 API 보충 검사는 별도 계층으로 기록합니다.

### 흐름 B — 별도 요청형 새 발행 → 지정 수신자 consume → 재사용 거부

1. 이미 폐기한 흐름 A Proof를 사용하지 않고 issuer가 **화면에서 별도 요청형을 새로 발행**합니다.
2. 새 anonymous/recipient 세션에서 조회·새로고침·검증을 반복하고 전후 `snapshot`을 저장합니다.
   ACTIVE 유지, Operation/Audit 수·consume event·consumed_at이 변하지 않아야 합니다.
3. 지정 recipient가 화면에서 consume합니다. 실제 request_id, Operation, tx hash와 성공 receipt,
   consumed_at·ProofConsumed event **1개**를 기록합니다. tx hash만으로 완료 표시하면 실패입니다.
4. 새 recipient 세션에서 VERIFIED + CONSUMED, REPLAY_DETECTED, 사용 불가를 확인합니다.
5. 같은 request_id 재시도는 같은 Operation/tx입니다. **새 ID 재사용**은 409 REPLAY_DETECTED,
   추가 consume event 없음이어야 합니다. UI가 재시도를 막는 경우 UI 제한과 API 보충을 구분합니다.

### 거부·장애·미확정 화면

- 활성 문서형에는 consume 쓰기가 없어야 합니다. 직접 API의 409 PROOF_NOT_SINGLE_USE는
  D2/보충 API 증거이며 UI 버튼 검사를 대신하지 않습니다.
- other_recipient/operator/다른 issuer/anonymous의 fresh 세션에서 제한 접근·권한 표시와
  가능한 실제 요청의 401/404, DB·체인 불변을 기록합니다. 권한을 client 값으로 주입하지 않습니다.
- RPC 장애는 `session.json`의 **owned_anvil_container만** stop/start합니다. 장애 중 verify는
  INCONCLUSIVE/null/DEPENDENCY_UNAVAILABLE, consume은 503이며 성공 표시·DB 쓰기가 없어야 합니다.
  새 Proof를 이 시나리오에 사용하고 복귀 후 ACTIVE를 다시 확인합니다.
- UNKNOWN/FAILED의 선택 키 보존·consume 보류 표시는 사례에 기대값을 준비했습니다.
  구체적인 제출 후 응답 유실/실패 receipt 주입과 Playwright locator는 연결된 A 화면의 실제
  요청·C/B 복구 경계에 맞춰 적용합니다. **이번 준비기에 제출 후 장애 주입 기능은 없습니다.**
  단순 Anvil 정지를 UNKNOWN 상태나 실패 receipt 재현으로 세지 않습니다.

## 5. DB·체인 증거 판정

snapshot은 DB를 SELECT하고 Reader/RPC를 호출하며 상태 변경을 제출하지 않습니다.
계정 비밀번호/hash, signer secret_ref, 원문 envelope, token/salt/binding, 복구 참조는 직렬화하지 않습니다.

- 키 교체: DB keys.selected의 유일성과 새 Proof key_id, chain key_id_hash=
  db_key_id_hash, 교체/등록 Operation receipt status=0x1을 비교합니다.
- 폐기/소비: DB Operation/tx + canonical receipt + chain 상태/시각 + 해당 event 수를 함께 봅니다.
  Snapshot의 DB key status만으로 현재 chain key 상태를 단정하지 않습니다.
- 조회·거부: 전후 Operation/Audit 수, consumed_at/revoked_at/event가 같아야 합니다.
- RPC 조회 실패는 chain_error/receipt_error=DEPENDENCY_UNAVAILABLE로 기록합니다.
  읽지 못한 events=null을 0개 또는 정상 상태로 바꾸지 않습니다.
- 각 Reader의 block/hash를 보존합니다. 모든 snapshot 읽기가 하나의 전역 atomic block이라는
  보장은 없으므로 화면의 쓰기가 완료된 뒤 정지 상태에서 비교하고 변경이 끼면 다시 읽습니다.
- 화면·응답 관찰 없이 snapshot만으로 D3 PASS를 기록하지 않습니다.

결과 보고에는 제품/QA/웹 SHA, Node·lockfile·환경 fingerprint·배포 identity,
사례별 기대/실제 값·UI 요청·snapshot 링크·실패 원인을 기록합니다.
미구현 화면은 BLOCKED/NOT_RUN, 실행했으나 다르면 FAIL, 근거를 갖춘 성공만 PASS입니다.
계정 파일·로그 전체 대신 비밀을 제거한 필요한 근거만 PR에 올립니다.

## 6. 준비 확인과 현재 남은 경계

준비기의 실제 실행·최종 코드 SHA·정적 검사 결과는 [준비 확인 기록](w4-d3-preparation.json)에 남깁니다.
기존 D1/D2 결과를 다시 전체 실행하거나 이번 브라우저 성공으로 바꾸지 않습니다.
이번 준비에서 웹 build/Playwright/실제 UI 상태 변경·회귀 suite는 실행하지 않았습니다.
A W4 UI 연결과 최신 phase 반영 후 현재 Makefile·계획서 §15.9의 변경 영역 검사 및 실제
브라우저 두 흐름을 실행합니다. C/B 리뷰, #49 phase 반영과 팀 전체 단계 승격은 별도입니다.
