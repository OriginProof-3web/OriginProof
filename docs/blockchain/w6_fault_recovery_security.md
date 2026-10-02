# W6-B 장애·재배포·보안 점검 기록 (2026-10-02)

- 담당: B / `@hamin1228`
- 브랜치: `codex/w6-b-recovery-security` (최신 W5-B `b7a4107` 선행)
- 상태: B Adapter/indexer의 장애 주입·임시 로컬 EVM 재현과 보안 점검 실행.
  공유 Python 의존성 취약점 수정, C의 보존 DB/서비스 연결과 작성자 외 리뷰는 남았다.

## W6-B1 장애 주입

| 주입 | 기대/실제 근거 |
| --- | --- |
| receipt RPC 단절 뒤 복구 | `test_receipt_rpc_outage_then_recovery_reuses_submission`: UNKNOWN과 보존된 tx hash → 같은 nonce/hash 재조회 CONFIRMED; send 1회 |
| receipt 지연·실패·canonical hash 오류 | `test_failure_and_ambiguous_results_are_not_confirmed`: missing/failed/hash 불일치/RPC 오류는 성공 거부. 실제 Anvil에서 automine 중지→UNKNOWN→채굴→동일 tx 복구 확인 |
| 재조회 중 reorg | Writer가 receipt 블록과 상태 재조회 블록을 읽기 전후 비교. `reorg_after_reread`, `reread_block_reorg` 주입 시 UNKNOWN, 재전송 없음 |
| 이벤트 중복·DB 실패·reorg | `test_atomic_block_replay_restart_and_failed_write`, `test_reorg_requires_verified_common_ancestor`, 확인 블록 동기화 검사: checkpoint 불전진, 저장된 canonical 공통 조상만 rewind, RPC 오류 전파. 임시 Anvil snapshot/revert로 다른 블록 hash를 만들고 기존 checkpoint 복구 확인 |
| 계약 직접 호출·경쟁 consume | Foundry `ProofStatusRegistryTest`: 무권한 거부, 허가된 1회 전이 |

미확인 전송은 `PreparedChainWrite.recovery_reference`와 가능하면 tx hash를 보존하고,
`recover_prepared`로 기존 제출을 먼저 확인한다. C는 이 정보를 Operation DB에 실제로
영속 저장해야 한다. 보존 실패를 새 nonce·새 전송으로 자동 복구하지 않는다.

## W6-B2 폐기 가능한 로컬 체인 재기동 runbook

이 절차는 임시 Anvil에서만 실행한다. 보존 DB나 운영 체인을 reset하지 않는다.

1. 첫 Anvil에 합성 signer 공개 주소로 배포하고 manifest의 `chain_id`,
   `deployment_id`, `deployment_block/hash`, Registry 주소, 역할을 저장한다.
2. 임시 체인을 종료하고 같은 chain ID로 새 Anvil을 시작한다. 비교를 위해 합성
   빈 트랜잭션을 하나 보낸 뒤 **다시 배포**한다.
3. 새 manifest를 읽어 배포 ID·주소·시작 블록이 바뀌었는지, 기존 주소의 bytecode와
   새 체인의 기존 주소 이벤트가 없는지 확인한다. 기존 manifest Reader는 현재 체인
   조회를 dependency 오류로 거부해야 한다.
4. 새 manifest Reader로 seed key signer 공개 주소를 읽어 보존한 signer와 대조한다.
   새 deployment ID의 indexer/checkpoint와 Operation을 별도로 시작한다. 같은 chain ID를
   이유로 이전 배포의 Proof나 이벤트를 성공 상태로 복사하지 않는다.
5. 다른 chain ID를 사용할 때는 새 network/domain용 데이터를 별도 서명한다.
   로컬 배포 스크립트 자체는 chain ID 31337만 허용한다.

실제 실행: `W6_LIVE_TEST=1 pytest -q services/indexer/tests/test_chain_restart.py`에서
`1 passed`. 임시 체인 두 개, pending receipt 복구, snapshot/revert 후 canonical
checkpoint 복구, 실제 재배포,
이전/새 주소·manifest·시작 블록·seed signer를 검사했다. C의 Compose/DB 보존 복구
(`W5-C3`, `W6-C3`)와 다른 노트북 재현은
이번 검사 범위 밖이다.

## W6-B3 보안 경계

- `forge test --summary`: 22 passed. Issuer/Key/Proof 권한, 재사용, binding, 서명
  digest Golden Vector를 실행했다. `forge coverage --report summary`는 성공했지만
  라이브러리 anchor 경고가 많아 전체 비율을 보안 증거로 사용하지 않는다. 프로젝트
  `ProofStatusRegistry.sol`의 line 96.39%, branch 70.00%만 참고한다.
- `git grep -l -I -E`로 추적된 소스의 일반적인 private-key/token 패턴을 검색해
  해당 파일이 없음을 확인했다. fixture/docs는 이 검색에서 제외했다. 이 결과는
  모든 비밀정보 형식에 대한 부재나 의존성 취약점 부재를 증명하지 않는다.
- `packages/contracts/dependencies.lock`의 OpenZeppelin 5.7.0과 forge-std 1.16.2,
  Python `uv.lock` 고정을 확인했다. OpenZeppelin 공식 [보안 공지](https://github.com/OpenZeppelin/openzeppelin-contracts/security/advisories)와 대조했다. 확인한
  `Bytes.lastIndexOf` 공지의 수정 버전은 5.4.0이고 현재 고정 버전은 5.7.0이다.
- `uv audit --frozen`은 49 패키지 중 `starlette 0.46.2` 14항목,
  개발용 `pytest 8.4.2` 2항목으로 종료 코드 1이었다. 중복 ID를 포함한 보고 건수다.
  `uv audit --frozen --no-dev`도 런타임 Starlette 14항목으로 종료 코드 1이다.
  Starlette의 [Host 검증](https://github.com/Kludex/starlette/security/advisories/GHSA-86qp-5c8j-p5mr),
  [form 제한](https://github.com/Kludex/starlette/security/advisories/GHSA-82w8-qh3p-5jfq) 등의
  공지와 pytest [수정 릴리스](https://github.com/pytest-dev/pytest/releases/tag/9.0.3)를 확인했다.
  API `fastapi>=0.115,<0.116`와 공유 dev `pytest<9`, `uv.lock`을 함께 올려야 하므로
  C/API 및 공유 설정 담당자가 호환성·회귀를 검토해야 한다. 이 항목은 **미해결**이다.
- 중요한 신뢰 경계: issuer account 또는 gateway는 직접 `registerProof`를 호출할 수
  있다. Contract는 JSON 서명·로그인 자체를 확인하지 않는다. issuer/gateway 계정
  보호와 C의 세션·서명·binding 검증이 필수이며, 전체 API 정책 우회 불가를
  Contract 단위 검사만으로 선언하지 않는다.

최종 검증 SHA와 명령 결과는 개인 기여 기록에 고정하고, `phase/W6` 생성 후 PR에
반영한다. `make security`는 안내
명령이므로 보안 검사 성공으로 세지 않았다. 감사에서 발견한 공유 의존성 위험을
무시하거나 성공으로 표시하지 않는다.
