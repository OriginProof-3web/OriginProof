# W5-B 인덱서 복구·권한 점검 인계 (2026-10-02)

- 담당: B / `@hamin1228`
- 브랜치: `codex/w5-b-indexer-recovery` (`origin/integration@3295a71` + W4-B `58e819e` 선행)
- 범위: W5-B1/B2 저장·복구 경계, W5-B3 배포/권한 점검. `phase/W5`와 팀 연결·리뷰는 별도다.

## 이벤트 저장과 재시작

`ProjectionStore.apply_block(chain_id, deployment_id, block_number, block_hash, logs)`에
해당 블록의 Proof 로그를 logIndex 순서로 전달한다. 빈 블록은 `logs=()`로 호출한다.
한 DB transaction에서 블록 identity, 이벤트, Proof 이벤트, checkpoint를 저장한다.
저장 실패 시 checkpoint도 전진하지 않는다. 같은 블록 hash의 재실행은 `False`,
서로 다른 hash 또는 블록 공백은 오류다. 이 경로를 시작한 배포에서는 기존
`update_checkpoint`로 checkpoint를 앞세울 수 없다. 기존 `apply`/`apply_proof_log`와
`update_checkpoint`는 이전 소비자 호환을 위해 남아 있지만, 신규 스캐너는 사용하지 않는다.

1. 배포 manifest의 `chain_id`·`deployment_id`·`deployment_block`으로 스캔 범위를 정한다.
2. `sync_confirmed(chain_id, deployment_id, deployment_block, latest_block_at,
   block_hash_at, logs_at, confirmations=2)`에 현재 체인 조회 callback을 제공한다.
   기본값 2 confirmations는 tip을 한 블록 남기며, 처리 상한은
   `latest - confirmations + 1`이다. `logs_at(number)`는 해당 블록의
   ProofStatusRegistry 주소와 세 Proof topic만 조회·decode한 순서 있는 로그를 반환한다.
   RPC·decode 실패는 예외로 전달한다.
3. 재시작할 때 함수가 checkpoint hash를 현재 canonical hash와 비교하고, 불일치 시
   `recover_reorg`로 저장된 실제 공통 조상을 찾는다. 처리 중 블록 hash가 바뀌거나
   chain tip이 후퇴하면 성공을 반환하지 않는다.
4. `recover_reorg`는 저장된 블록 hash와 현재 체인 hash가 일치하는 가장 높은 블록만
   공통 조상으로 채택한다. 이후 로그·Proof 상태·checkpoint를 함께 되돌린다.
   일치하는 조상이 없으면 이전 배포 데이터에 덧쓰지 않고 배포 시작점부터 별도로
   재구축한다. RPC 오류도 성공/부재로 바꾸지 않는다.

`verified_projected_proof_status(..., confirmed_tip, block_hash_at)`은 조회 전후의
checkpoint hash를 확인하고 미확정 checkpoint 또는 reorg이면 오류를 낸다. 원래
`projected_proof_status`는 과거 이벤트 표시용으로 남아 있다. C는 동기화/검증 오류를
복구 중·조회 보류로 전달하고 projection을 현재 사용 가능 판정에 쓰지 않는다. 현재
판정은 체인 Reader의 canonical block 재조회가 권위다. 백그라운드 스캐너 실행과
API/DB 상태 연결은 C의 서비스 조율 범위다.

## 배포와 직접 호출 경계

로컬 배포 스크립트는 admin, issuer manager, key manager, issuer account, gateway에
서로 다른 unlocked 계정을 배정한다. manifest loader도 중복 주소를 거부한다.
manifest loader는 Registry/Key/Proof constructor의 admin·gateway·참조 주소가
manifest의 역할·주소와 맞는지 검사한다. Reader/Writer는 manifest의 chain ID·배포
블록/hash·주소·ABI SHA를 검증한다. 실제 Anvil에서는 admin·issuer manager·key
manager·gateway의 `hasRole` 결과와 admin의 manager/gateway 역할 부재를 확인했다.
Foundry에서 admin/타 기관 직접 `registerProof`와 admin/issuer/타인 직접 `consumeProof`가
거부됨을 확인한다. gateway의 `registerProof` 권한은 ADR의 서버 대행 신뢰 경계다.
계약 자체는 JSON 서명·로그인을 검증하지 않으므로 C가 원본 envelope·세션·binding을
검증하지 않으면 gateway를 통한 우회는 막을 수 없다. 이는 W5-C 연결 전 남은 경계다.

## 실행 근거

- Python Indexer/API/Core 회귀: `131 passed, 4 skipped` (단위/mock)
- Foundry 계약: `forge test --summary`에서 `22 passed, 0 failed`
- 임시 Anvil + 실제 배포/권한/eth_getLogs/2-confirmation projection: `1 passed`
- 미실행: C의 실제 DB/API 스캐너 연결, 외부 테스트넷, 상시 장애 복구 운영

실행 명령과 최종 SHA는 PR 제출 시 고정한다. 이 문서는 팀 단계 완료 판정이 아니다.
