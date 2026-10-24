# V5-W5-B / B-C01 — 고정 승인자 배포 근거 확인

- B 여하민 @hamin1228, AI(Codex)가 사용자 다음 개발 지시로 수행.
- 작업 branch codex/v5-w5-b-live-recovery, 기존 [#79](https://github.com/OriginProof-3web/OriginProof/pull/79), 시작a5707c3. 실행 코드 `429280140269510d062da9fc046d6519ae6cc2a3`.
- C 원본 Address·DependencyUnavailableError와 B 기존 WalletRpc/ABI/deployment pinning을 소비. C 생산 코드·Schema·ABI·Contract·새 의존성·lock 변경 없음.
- **B 고정 승인자 검증 독립 구현·합성/실제 로컬 검사 완료. C 생산 주입·소비 리뷰·API/DB/Operation 연결·단계 완료는 대기.** 전체 공유 계약이나 운영 배포 결정을 새로 확정하지 않음.

## 신뢰 설정과 호출

```python
from infrastructure.blockchain.wallet_adapter import WalletRegistryReadAdapter
from infrastructure.blockchain.wallet_creation import WalletCreationProof

proof = WalletCreationProof(
    tx_hash=verified_deployment_tx_hash,
    creation_bytecode=trusted_build_creation_bytecode,  # bytes
)
adapter = WalletRegistryReadAdapter(rpc, creation_proof=proof)
is_member = await adapter.is_approver(wallet_address)
```

`rpc`는 기존 검증된 chain ID·계약 주소·배포 block/hash·runtime code hash·컴파일 ABI로 설정한 WalletRpc입니다. proof.tx_hash는 같은 배포의 실제 생성 거래이며, creation_bytecode는 잠긴 소스·컴파일러·의존성으로 만든 **신뢰할 build artifact의 bytecode.object 전체 bytes**입니다. RPC 거래의 input에서 임의로 잘라 만든 코드나 사용자 요청·업로드 manifest의 값을 신뢰 root로 쓰면 안 됩니다. 이 기능이 artifact 공급 경로·C production 설정을 자동으로 신뢰 검증하는 것은 아닙니다. 운영자는 승인된 코드/build fingerprint와 배포 reference를 설정해야 합니다.

승인자 주소 목록을 config/API 인자로 받지 않고 실제 거래 constructor에서 도출합니다. proof 객체는 frozen이며 bytes만 받습니다. proof 없는 기존 인스턴스는 읽기 동작을 유지하지만 is_approver는 기존과 같이 명시적 dependency 오류입니다. 임의 리스트/dict를 proof로 넣는 구성도 거부합니다.

## 매 호출 검증

1. 기존 snapshot으로 chain·배포 block/hash·현재 runtime을 검증합니다.
2. 지정 생성 거래와 receipt가 모두 있어야 하고 hash·chain·sender·value=0·to=None·생성 계약 주소를 대조합니다.
3. 거래/receipt의 block/hash가 설정한 배포 블록과 같고 canonical block의 정확한 transaction index에 같은 hash가 있어야 합니다. 성공 receipt(status1)가 필수입니다.
4. 실제 input은 신뢰 생성 bytecode로 시작해야 합니다. 나머지를 기존 ABI의 nonpayable `address[3]` constructor로 decode하고 재encode bytes가 완전히 같은지 확인합니다. padding·후행 bytes·짧은 인자를 거부하고 0/중복 주소를 거부합니다. ABI는 기존 원본 그대로입니다.
5. 배포 block에서도 code를 hash-pin 조회해 설정한 runtime hash와 대조합니다. 끝에 배포/관측 head가 여전히 canonical인지 재확인합니다.
6. 검증한 세 주소의 membership만 bool로 반환합니다. proof·RPC·코드 불일치는False로 숨기지 않고 dependency 오류(C runtime503)입니다. 승인자/비승인자 모두 증거가 온전할 때만 판정합니다. 검증 결과를 캐시하지 않으므로 다음 호출의 reorg/노드 변경을 건너뛰지 않습니다.

이 검증은 신뢰 RPC의 canonical 거래/receipt/code 응답을 사용하는 기존 B 신뢰 경계입니다. 독립적인 Merkle receipt 증명이나 악성 RPC 전체를 배제하는 검증으로 표현하지 않습니다.

## 지원 경계

- 현재 Registry의 **top-level CREATE 배포만** 지원합니다. factory/CREATE2 내부 배포(to가 factory인 경우)는 거부하며 trace 검색을 추가하지 않았습니다. 기존 legacy 배포에 이 근거를 섞지 않습니다.
- 과거 배포 tx/receipt/code를 제공하지 않는 provider, proof가 없거나 잘못된 build, reorg/노드 단절은 사용 불가입니다. 다른 주소 목록·DB 역할·deployer 주소로 대체하지 않습니다.
- 기관 발행키·가스 relayer·고정 승인자 역할을 구분합니다. 실제 하네스에서 세 승인자는True, institution/relayer는False였습니다.
- proof를 생성하는 생산 manifest loader/lifespan·설정 주입과 소비 리뷰는 C/B 후속입니다. C main.py를 수정하지 않았으므로 서비스에 자동 활성화되지 않습니다.
- submit·find_transaction의 C 연결은 계속 명시적 사용 불가입니다. API 인증·DB·Operation·동시성·배포 운영·finality·공개 체인·G07 종료를 완료로 바꾸지 않습니다.

## 실제 검사

| 검사 | 결과·한계 |
| --- | --- |
| test_wallet_approvers.py | 43 PASS. 실제 ABI를 소비하는 합성 CREATE RPC:3명/비승인자/대소문자, 거래·receipt 누락/변조·wrong domain·블록 위치·code·ABI·padding/후행/0/중복 거부, 무캐시·reorg·C factory503·잘못된 config |
| 기존 read Adapter 합성 | 42 PASS. proof 없는 is_approver 거부를 포함해 기존 조회 동작 유지 |
| 전체 Python | 831 PASS/11 SKIP, 기존 Starlette TestClient 경고1. skip을 실제 환경 통과로 합산하지 않음 |
| 별도 실제 Anvil | 1 PASS at4292801. 기존 실제 합성 배포에 proof를 구성해 세 승인자True·기관/relayerFalse·wrong build 거부·노드 종료 후 사용 불가를 확인. [실행 증거](evidence/v5_wallet_approvers_4292801.json)에 tx/constructor·runtime/creation code hash·source/compiler/lock fingerprint 보존 |
| 공식 Ruff·compileall·구조·Node hash·원본 생성물/Golden 불변 | PASS. 초기 test 줄길이 lint를 정리한 뒤 최종 통과. sandbox cache 쓰기 제한으로 실패한 읽기 전용 Ruff 호출도 권한 있는 동일 검사로 재실행 |
| 실제 API 서버/DB·PostgreSQL·브라우저·공개 RPC·D mixed QA | 미실행. factory 주입 단위 검사는 asyncpg 미연결 엔진만 사용하며 실제 DB 접근/lifespan 실행 없음 |
| 전체 Foundry fuzz/웹 검사 | 이번 미실행, Contract/ABI·웹 변경 없음. Anvil 하네스의 기존 forge build는 실행 |

실제 Anvil은 새 임의 localhost 포트의 폐기 가능한 합성 체인이며 실행 후 종료했습니다. 기존 배포 파일·원본 사용자 변경5개를 덮어쓰지 않았습니다. 개인키/토큰·실제 기관 자료를 저장하지 않았습니다.

## 인계·완료 구분

B-C01은 기존 ABI 유지·top-level 생성 거래 근거를 선택한 B 구현입니다. C가 모델/생산 소비를 승인한 것으로 기록하지 않습니다. 다음은 C/B의 trusted build/배포 설정 소비 검토와 실제 API/DB 통합 검사, submit relayer·UNKNOWN 진행점 연결입니다. D의 독립 실패 사례·G07 mixed QA는 별도입니다. 사용자 입력은 회의 후 확정, Decisions API 범위 밖, 기존 v1/v2 서명·권한·consume 회귀 보존. 현재 head 사람/작성자 외 리뷰는 미확인이며 이전 확인 댓글·#83/#86 승인을 재사용하지 않습니다.
