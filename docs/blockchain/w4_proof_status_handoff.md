# W4-B1/B2/B3 Proof 상태 Contract·Adapter 인계

- 담당: B / `@hamin1228`
- 준비 기준: `origin/integration@3295a71`에서 시작하여 본인 W3-B 선행 SHA `92e0e94`까지 fast-forward
- 작업 브랜치: `codex/w4-b-proof-lifecycle`
- 상태: B 독립 구현·로컬 EVM 검사 완료; C 소비 리뷰·실제 API/DB 연결과 `phase/W4` PR 대기
- 근거: 개발 계획서 v3.0 W4-B1/B2/B3, ADR 0001 §6–7, [W3-B3 후보](w3_trust_and_proof_status_contract.md)

## 계약·권한

새 `ProofStatusRegistry` ABI는 `packages/contracts/abi/ProofStatusRegistry.json`이다. 기존
Issuer/Key ABI는 변경하지 않는다. `proofId`, `issuerId`, `keyId`는 기존 문자열의
Keccak-256 bytes32이며 signing digest와 subject binding hash는 이미 32바이트 hash다.
온체인에는 원문·계정 ID·salt·개인키를 저장하지 않는다.

| 함수 | 입력/결과 | 허용 주체·거부 조건 |
| --- | --- | --- |
| `registerProof` | proof/issuer/key ID hash, signing digest, subject binding hash, issued/expires Unix 초, singleUse → event | 현재 기관 account 또는 `GATEWAY_ROLE`; 기관/키 ACTIVE, 키 소속·발행 시각의 키 기간, 유효한 commitment·Proof 기간·중복 금지 |
| `revokeProof` | proof ID → `bool changed`; 처음만 `ProofRevoked` event | 해당 Proof 기관의 현재 account만. 수신자·gateway·타 기관 직접 호출 거부. 반복은 `false`, event 없음. consume 이력 보존 |
| `consumeProof` | proof ID, `ISSUER=0`/`RECIPIENT=1`, actor binding → event | `GATEWAY_ROLE`만. 발행기관 ID hash 또는 불변 subject binding hash 일치, 현재 기관/키 ACTIVE, 발행 당시 키 기간, 현재 Proof 기간·singleUse·미폐기·미소비 필수 |
| `getProof`, `proofStatus`, `isConsumable` | 불변 commitment/상태/지정 시각 사용 가능 여부 | 읽기 전용. 조회는 consume하지 않음 |

`proofStatus` 값은 NONE=0, ACTIVE=1, REVOKED=2, CONSUMED=3이다. CONSUMED 뒤 적법한
폐기를 허용하며 상태는 REVOKED가 되고 `consumedAt`은 남는다. 같은 Proof의 경쟁 consume은
한 번만 성공·event를 낸다. Contract는 JSON/signature/로그인 자체를 검사하지 않는다.
서버가 원본 envelope와 세션을 검증한 결과를 gateway가 전달한다는 ADR 신뢰 경계다.

실제 event 서명은 `ProofRegistered(bytes32,bytes32,bytes32)`, `ProofRevoked(bytes32,uint64)`,
`ProofConsumed(bytes32,uint8,uint64)`이다. 생성 ABI가 기준이다. 권한 오류는 OZ
`AccessControlUnauthorizedAccount` 또는 `UnauthorizedIssuerOperator`, 상태·binding·기간
오류는 Contract custom error로 revert된다. revert receipt는 성공이 아니다.
상태 시각은 `uint64`로 저장한다. 발행 시각 0은 commitment로 표현할 수 있지만,
폐기·소비를 실행하는 블록 시각이 0이거나 `uint64` 범위를 벗어나면
`InvalidBlockTime`으로 거부해 미처리 상태의 0 표식과 섞이지 않게 한다.

## C 호출·복구 순서

1. C가 인증 주체, 원본 envelope의 domain/network/hash/signature, 기관·키 snapshot,
   issued/expires와 수신자 binding을 확인한다. `registerProof`는 검증되지 않은 digest를
   스스로 재검증하지 않으므로 C의 검증이 필수다.
2. `prepare_register_proof(sender, proof_id, issuer_id, key_id, signing_digest,
   subject_binding_hash, issued_at, expires_at, single_use)`를 호출한다. 폐기와 consume은
   각각 `prepare_revoke_proof(sender, proof_id)`,
   `prepare_consume_proof(gateway, proof_id, actor_kind, actor_binding)`이다. 선택 `nonce`는
   복구 시 동일 값으로 다시 준비한다.
3. C는 Operation과 `prepared.recovery_reference`를 영속 저장한 뒤
   `execute_prepared(prepared, persistence)` 또는 `submit_prepared`를 호출한다. tx hash는
   receipt 대기 전에 영속 저장한다. 저장 실패·전송 timeout은 UNKNOWN으로 보류한다.
4. `confirm_prepared(prepared, tx_hash)`는 제출 hash와 canonical receipt, 1 confirmation,
   `getProof`/`proofStatus` 재조회를 모두 확인한다. 실패 receipt는 FAILED, 조회 실패·reorg는
   UNKNOWN이다. UNKNOWN에 새 nonce·새 작업을 무조건 만들지 않는다.
5. 재시작 시 같은 입력·nonce로 prepare하고 `restore_prepared`로 저장된 scan 시작점을
   복원한 뒤 `recover_prepared(prepared, saved_tx_hash)`로 기존 제출을 확인한다.
   등록 CONFIRMED 전에는 Proof를 ACTIVE로 응답하지 않는다. 새 요청 ID로 이미 소비된
   Proof를 처리하면 재사용 거부를 반환한다.

Reader `get_proof_state(proof_id, at)`은 현재 체인과 배포 identity·bytecode를 확인하고
하나의 block에서 commitment, lifecycle과 `at` 시각의 `isConsumable`을 읽는다. 반환은
`ProofChainState` 또는 미등록 `None`이다. RPC/ABI/network/reorg 오류는
`DependencyUnavailableError`로 보류한다. `at`에는 C가 신뢰하는 현재 시각을 넣고,
Projection 결과만으로 현재 사용 가능하다고 판정하지 않는다.

## 배포·projection·전환

로컬 배포는 다섯 번째 별도 unlocked 계정을 gateway로 사용한다. 새 manifest에는
`ProofStatusRegistry` 주소·constructor 인자·ABI SHA-256과 `roles.gateway`가 추가된다.
기존 W1–W3 manifest는 Registry Reader/Writer 회귀용으로 계속 읽을 수 있지만 Proof
메서드에는 새 계약이 필수다. 같은 chain ID의 새 배포도 새 `deployment_id`이며 과거
Operation/Proof를 새 체인의 ACTIVE로 간주하지 않는다.

`decode_proof_log`는 세 Proof event topic만 해석한다. `ProjectionStore.apply_proof_log`는
원본 event identity와 Proof event를 한 DB transaction에 저장하며 재시작 replay는
중복 적용하지 않는다. `projected_proof_status`는 이벤트 이력 표시용이다. 실제 EVM
`eth_getLogs` 요청은 새 Proof contract 주소와 세 topic을 필터링해야 한다. 배포 시
OpenZeppelin 권한 event도 나오므로 전체 로그를 무조건 Proof decoder에 보내지 않는다.
checkpoint 공통 조상 검증·복구 강화는 W5-B1/B2 범위이며 현재 체인 Reader가 판정 권위다.

W3에 DB만 저장된 Proof의 소급 등록은 C가 보존된 검증 envelope를 다시 확인하고 새
Operation으로 진행해야 한다. 재서명하거나 미등록 Proof를 ACTIVE로 추정하지 않는다.
C의 실제 발행/폐기/consume API·DB wiring, D 독립 QA, W4 A 화면과 작성자 외 리뷰는
별도 후속이다.
