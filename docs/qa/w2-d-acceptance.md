# W2-D 검증 준비 — 기관 승인과 공개키 관리

기준: `phase/W2` `e40191f405763666c11fc42058ccf6ac516473ae` (부모 `phase/W1` `322416e8556cea42de0016b6bb1461f56b69b4e5`)

담당: D / 여인준님 (`@yijun0330`)

상태: 독립 검증 준비. 아래 W2-C API·연결 브라우저 사례는 실제 실행 전이며 모두 `NOT_RUN`입니다.

W2는 계획서 §15.3의 개발 단계입니다. `phase/W2`는 생성되어 W1 작업 PR #23/#26/#27/#30과 기준 동기화 #31, W2-A2 PR #28을 포함합니다. W1-C3 PR #32는 아직 열려 있고 `integration`은 여전히 `3295a71c10a1a99c523d3cfefde91b5737b737ac`이므로 W1 단계가 `integration`으로 승격된 상태는 아닙니다. 이번 W2 D 브랜치는 이제 `phase/W2` 최신 SHA에서 시작해 독립 검증 준비를 진행하며 단계 완료를 뜻하지 않습니다.

## D1 — API·체인 경계 실패 사례

### 현재 phase/W2의 B 회귀 스모크

검사 대상 SHA `e40191f405763666c11fc42058ccf6ac516473ae`에서 계획서 15.9의 Indexer 검사를 시도했습니다.

| 명령/환경 | 결과와 범위 |
| --- | --- |
| `UV_PROJECT_ENVIRONMENT=.uv-venv uv run pytest -q services/indexer/tests` | 실행 전 uv가 macOS `system-configuration` 경로에서 `Attempted to create a NULL object`로 panic하여 pytest 미실행 |
| `PYTHONPATH=services/indexer/src:packages/python:apps/api/src /private/tmp/originproof-w1-completion/.uv-venv/bin/python -m pytest -q services/indexer/tests` | Python 3.13.7의 기존 locked dependency 환경에서 **60 passed, 1 skipped**. 현재 phase/W2 소스의 Reader/Writer/projection 테스트; skipped 사례는 opt-in live chain |

이 스모크는 현재 B 코드의 단위 회귀 확인이며, D1 API·DB·chain 경계 또는 실제 RPC 연결 검증을 대신하지 않습니다. live-chain 검사는 실행하지 않았습니다.

| 사례 | F 기준 | 합성 사전조건과 입력 | 기대 불변조건 | 실행 증거 |
| --- | --- | --- | --- | --- |
| W2-D1-01 미승인 기관 키 작업 | F09 | `PENDING_REVIEW` 기관 계정으로 기관 활성화 또는 키 등록 요청 | 승인과 확인된 체인 상태 이전에는 등록/활성 성공을 응답하지 않고, 키·기관 체인 상태가 바뀌지 않음 | `NOT_RUN` — W2-C/B 실제 연결 필요 |
| W2-D1-02 무권한 승인/변조된 역할 | F10 | issuer 또는 일반 계정에서 승인·중지 API 호출; 요청의 role/issuer ID 변조 | 서버 권한과 기관 소유권 검사에서 거절; DB·체인 상태 불변 | `NOT_RUN` — W2-C API 필요 |
| W2-D1-03 타 기관 키 조작 | F05 | 기관 A 세션으로 기관 B의 key ID 조회·폐기 시도 | API와 권한이 적용된 체인 경계에서 거절; B의 키 및 감사 이력 상태 불변 | `NOT_RUN` — W2-C/B 연결 필요 |
| W2-D1-04 중복 등록·요청 충돌 | F12 | 같은 `request_id`·같은 본문 재시도, 같은 ID·다른 기관/본문 재시도, 같은 공개키의 중복 등록 | 동일 요청은 기존 Operation을 식별하고 이중 체인 변경을 만들지 않음; 본문/기관 불일치는 계약된 충돌 응답; 중복 등록은 계약대로 거절 또는 기존 결과 재사용 | `NOT_RUN` — Operation/Adapter 상태 계약 리뷰 필요 |
| W2-D1-05 RPC timeout 후 재조회/재시도 | F12/F13 | 제출 후 응답 timeout 또는 RPC 단절을 합성 주입하고 동일 Operation 조회·재시도 | 결과 불명 상태를 성공으로 표시하지 않음; 재시도 전에 chain state/receipt를 재조회하고 중복 트랜잭션을 만들지 않음 | `NOT_RUN` — W2-B Adapter·W2-C Operation 연결 필요 |
| W2-D1-06 실패 receipt | F13 | 로컬 EVM에서 revert/실패 receipt 발생 | 기관/키를 활성으로 표시하지 않음; Operation·receipt·감사 상태가 실패 또는 확인 보류로 구분됨 | `NOT_RUN` — W2-B 배포·W2-C 상태 전이 필요 |
| W2-D1-07 미확정 작업 중 재시작 | F13 | Operation 제출 후 confirmation 전 API/indexer 재시작; 재기동 후 동일 ID와 chain 상태 조회 | 기존 Operation 복구, DB·receipt·체인 결과 재조정; 무조건 재전송하지 않고 상태를 성공으로 추정하지 않음 | `NOT_RUN` — 복구 동작 미연결 |
| W2-D1-08 응답 손실 후 중복 방지 | F12 | 성공 receipt를 받은 직후 클라이언트 응답이 유실된 상황을 재현하고 동일 요청 재전송 | 동일 등록/체인 상태를 반환하고 두 번째 키·Operation·이벤트를 만들지 않음 | `NOT_RUN` — B/C 실제 연결 필요 |

각 실행 시 이 표의 행을 갱신하고 다음 근거를 기록합니다: 작업 SHA, 실행 환경/fingerprint, 합성 입력 식별자, 기대·실제 HTTP/Operation/receipt/체인 상태, 상태 변화 전후 값, 재현 명령, 실패 이슈 링크. API 응답 코드나 Operation enum이 합의된 계약과 다르면 D가 임의로 맞춰 쓰지 않고 담당자 확인이 필요한 불일치로 보고합니다.

## D2 — 브라우저와 재현 체크리스트

실제 A·B·C 연결이 준비되면 깨끗한 브라우저 세션에서 두 합성 기관을 사용해 아래 순서로 실행합니다. 전 과정은 실제 API·로컬 EVM 상태를 확인하며, mock 응답을 성공 증거로 쓰지 않습니다.

1. 발행자 계정에서 기관 신청을 제출하고 로그아웃합니다.
2. 운영자 계정에서 신청을 승인 또는 반려하고 사유·감사 이력을 확인합니다.
3. 합성 로컬 RPC의 체인 반영/receipt가 확인된 뒤 발행자 계정으로 재로그인하여 기관 상태를 다시 조회합니다. timeout/미확정이면 대기 또는 오류여야 합니다.
4. 승인 기관 계정에서 공개 키 등록·목록·상세를 수행합니다. 화면·응답·로그에 개인키·seed·session token이 없는지 확인합니다.
5. 키 폐기를 수행한 뒤 새로고침 및 새 세션에서 폐기 상태·감사 이력을 재조회합니다. 승인 전, 타 기관 ID, 중복 제출, 만료/폐기 키 동작도 확인합니다.
6. 다른 clean 환경에서 문서화된 lockfile·기동 절차로 로컬 DB/Anvil/API/web을 재현하고, RPC URL(비밀정보 제외), chain ID, 배포 manifest/SHA, 실행 SHA, 서비스 버전을 기록합니다.

| 항목 | 값 |
| --- | --- |
| 실행 SHA / branch | `NOT_RUN` |
| 실행 환경 / fingerprint | `NOT_RUN` |
| API·web·DB·RPC 상태 | `NOT_RUN` |
| chain ID / 배포 manifest SHA | `NOT_RUN` |
| 신청 → 승인 → 키 등록 → 폐기 → 재조회 | `NOT_RUN` — W2-A1/A2 및 B/C 연결 필요 |
| 새로고침·새 세션·권한 경계 | `NOT_RUN` — 실제 연결 필요 |
| clean 환경 재현 | `NOT_RUN` — 재현 가능한 W2 배포/기동 절차 필요 |
| blockers / 담당 PR | W1-C3 PR #32 및 W1 `phase/W1` → `integration` 승격 대기; W2-C API PR #33 미병합. W2-B1/B2·W2-A2 구현은 현재 `phase/W2`에 있으나 D 독립 검증 전 |

## 진행 경계

- W2-B1/B2의 Writer·배포·projection과 그 상태·복구 계약은 B의 PR #26으로 `phase/W2`에 들어왔습니다. B의 보고는 자체 Anvil 검사이며 D의 독립 검사로 대체하지 않습니다.
- W2-A2 PR #28은 `phase/W2`에 병합됐습니다. W2-C API/Operation 복구 PR #33은 `feat/w2-c-chain-keys`에서 `phase/W2`로 열린 상태이며 아직 병합 전입니다. 그 결과 W2-D1의 API·DB·체인 교차 확인과 W2-D2 전체 브라우저 흐름은 아직 실행할 수 없습니다.
- W1-C3 PR #32는 `phase/W1` 대상으로 열려 있습니다. 현재 `phase/W2`는 W1-C3를 포함하지 않으므로 그 모델에 직접 의존하는 연결 검사는 PR #32 반영 후 다시 확인해야 합니다.
- W2-D는 준비된 API·Adapter·화면을 독립 검증합니다. D 자료에서 API/Contract 구현, 타 담당 브랜치 merge/cherry-pick, 미구현 경로의 성공 판정은 하지 않습니다.
- 이번 커밋에서는 application source, 개인 `.env`, Golden Fixture를 변경하지 않았고 DB 초기화·운영 배포·유료 모델 호출도 하지 않았습니다.
