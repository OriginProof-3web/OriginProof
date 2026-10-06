# W3 / B / 여하민 — 개인 개발 기록

- GitHub 계정: `@hamin1228`
- 실제 작업일: 2026-10-02 (W3는 달력 주차가 아님)
- 상태: B 독립 구현·교차검사 완료 / C 소비 연결·작성자 외 리뷰 대기
- 작업 ID: `W3-B1`, `W3-B2`, `W3-B3`
- 작업 branch / 시작 기준 SHA: `codex/w3-b-proof-boundaries` / `phase/W3@1f8ed632ea9c74091abaf2fe2ec32882038f731f`
- PR 대상: `phase/W3`

## 목표와 실제 결과

발행과 검증이 서로 다른 블록의 기관·키 상태를 섞지 않도록 Reader에 동일 블록
Registry snapshot을 추가했다. Finals v2 공개 fixture의 canonical JSON, Keccak digest와
복구 signer를 Python에서 검증하고, 같은 bytes의 EVM digest를 Foundry에서 교차검사했다.
W4 `ProofStatusRegistry` 구현 전에 C와 합의할 ABI·권한·상태·오류·복구 경계를 문서화했다.

## 개인 기여와 협업

| 작업 ID | 본인이 수행한 일 | 재사용·다른 담당자 기여 | 상태 |
| --- | --- | --- | --- |
| W3-B1 | 기관·키를 동일 canonical block에서 읽는 snapshot, block/deployment 증거, 상태·기간 판정과 오류 검사 | W1/W2 Registry, manifest, Reader 계약 재사용 | 독립 구현 완료, C 연결 대기 |
| W3-B2 | PAYMENT_REQUEST·OFFICIAL_DOCUMENT v2 canonical bytes/digest/signer 및 domain/network/schema/proof type 경계 검사 | C가 확정한 core 모델과 공개 golden fixture 재사용 | 교차검사 완료 |
| W3-B3 | W4 ProofStatusRegistry 후보 ABI, 권한, lifecycle, event/error와 Writer 복구 순서 작성 | ADR 0001과 W2 Operation 복구 계약 재사용 | C 소비 리뷰·W4 구현 대기 |

C의 `feat/w3-c-issuance`는 읽어서 소비 지점을 확인했지만 cherry-pick하거나 C 소유 API를
수정하지 않았다. C는 발행·검증 흐름의 개별 `get_issuer`/`get_key` 조회를
`get_issuer_key_snapshot`으로 연결해야 한다.

## 주요 결정과 문제 해결

- snapshot은 chain ID, genesis/deployment identity와 Registry bytecode를 확인한 뒤 하나의
  명시적 block tag로 기관·키를 읽고 block hash를 함께 반환한다.
- 미등록은 `None`, 중지·폐기는 실제 상태, RPC·network·manifest·ABI·block 오류는
  `DependencyUnavailableError`로 구분한다. projection의 오래된 상태를 발행 허가로 쓰지 않는다.
- `key_valid_at`은 기관 ACTIVE, 키 ACTIVE, 소속 일치와 반개구간
  `valid_from <= at < valid_until`을 모두 만족할 때만 true다.
- Solidity 교차검사는 canonical JSON을 구현하는 테스트가 아니라 Python fixture의 동일 bytes가
  EVM `keccak256`에서도 같은 digest인지 확인하는 경계 검사다.
- W3-B3 문서는 배포 ABI가 아니라 W4 후보 계약이다. C 소비 리뷰 전에는 확정 계약이나
  단계 완료로 간주하지 않는다.

## 검증·시연 증거

| 사례·명령 | 실제 결과 | 환경 |
| --- | --- | --- |
| Ruff format/check | 변경 Python 5개 통과 | macOS, Ruff |
| Python 전체 관련 회귀 | 248개 통과, opt-in 4개 제외 | Python 3.13 |
| `forge test` | 12개 통과(새 v2 digest 경계 2개 포함) | Foundry |
| opt-in live chain | 1개 통과: 임시 Anvil 배포, snapshot, API/Writer 상태 변경 | Anvil chain 31337 |

실제 외부 RPC·유료 호출, 보존 DB 초기화, C API/DB 연결은 실행하지 않았다. 테스트는 공개
합성 fixture와 매 실행 새로 생성한 로컬 키·임시 Anvil만 사용했다.

## AI 활용과 본인의 판단

Codex로 개발 계획·ADR·담당 인계와 기존 Reader/fixture/C 준비 branch를 조사하고 구현·검사·문서
초안을 작성했다. 동일 블록 snapshot 범위, 오류를 미등록으로 축소하지 않는 정책, Solidity
교차검사의 한계와 W4 후보 계약의 비확정 상태를 직접 확인해 기록했다.

## 한계와 다음 작업

- C는 snapshot 반환값과 오류를 발행·검증 use case에 연결하고 API/DB 실패 경계를 검사해야 한다.
- C와 B는 W4 구현 전에 register/revoke/consume의 actor binding과 gateway 권한을 함께 검토해야 한다.
- D의 독립 QA, 작성자 외 리뷰, A/C 결과와 `phase/W3` 통합 전에는 W3 전체 완료가 아니다.

## 사실 확인

- 본인 확인: `@hamin1228` / 2026-10-02 / 작업 내용과 기여 기록 확인 대기
- 작성자 외 리뷰어: 미확인; C 소비자와 B 경로 리뷰 필요
