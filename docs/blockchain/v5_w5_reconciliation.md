# V5-W5-B / 2차 — 미등록·승인 이력·거래 상태 대조

- 날짜: 2026-10-17 / B 여하민 `@hamin1228`.
- 작업 브랜치: `codex/v5-w5-b-reconciliation`.
- 시작/선행: 자기 W5 1차 `7666bb9bf2d85804b9abe9be5a87ea122e1d914d`, [Draft #69](https://github.com/OriginProof-3web/OriginProof/pull/69).
- 기준: 계획서 5.1, v5-shared-0.1, [ADR 0004](../adr/0004-v5-governance-wallet-versioning.md).
- 판정: **B 대조 로직 독립 구현·합성 검사 완료 / C port·실제 연결·W5 전체 수용·작성자 외 리뷰 대기**.

## 문제와 변경 후 흐름

[1차](v5_w5_chain_evidence.md)는 실제 calldata·receipt를 해석했지만 거래 의도/이벤트/상태를 대조하지 않았습니다. RPC 오류와 정확한 미등록도 모두 dependency 오류로 처리했습니다. 이번에 B의 `WalletRpc`를 보강하고 별도 `WalletReconciler`를 추가했습니다. C의 공통 모델·API orchestration을 수정하거나 port 사본을 만들지 않습니다.

1. `WalletRpc.read(name, args)`는 새 배포 검증 snapshot에서 읽습니다. `getIssuer/getKey/getProposal/getDocument`가 각각 컴파일 ABI의 `UnknownIssuer()/UnknownKey()/UnknownProposal()/UnknownDocument()` **정확한 4바이트 revert**를 반환한 경우에만 `values=None`입니다. 다른 getter의 미등록 selector, trailing bytes, empty/nested/malformed revert, 네트워크·ABI 실패는 dependency 오류입니다. 미등록 응답도 canonical block을 재검사합니다.
2. `WalletReconciler(rpc).proposal(proposal_id)`는 제안 tuple로 chain/address를 포함한 ID를 재계산하고, 같은 snapshot까지의 생성·승인·실행 이벤트를 직접 조회합니다. 생성은 한 번, 서로 다른 주소 승인 1→2, count와 getter 일치, 실행은 두 번째 승인과 같은 tx여야 합니다. 누락·중복·다른 issuer/action·불일치 시 실패합니다. 결과는 `block/proposal/approvals/executed`이며 C의 ProposalView 상태 모델이 아닙니다. PREPARED/STALE/EXPIRED 변환은 C port 연결 시 처리합니다.
3. `WalletReconciler.transaction(tx_hash, function=..., arguments=..., sender=...)`는 `publish/revoke/propose/approve/suspendIssuer`를 지원합니다. `arguments`에는 **기존 저장 intent의 전체 ABI 이름/값**을 전달합니다. 누락 필드·변경된 서명·bool/int 혼용·부분 tuple을 허용하지 않습니다. 원본 receipt와 calldata의 chain/address/hash/sender/value 확인에 더해 canonical block의 transaction index 위치에도 tx hash가 있어야 합니다. `propose/approve/suspendIssuer`에는 저장한 직접 제출자의 소문자 `sender`가 필수이며, 누락되면 RPC 이전에 configuration 오류입니다. 다른 승인자의 같은 제안을 자기 작업으로 확정하지 않습니다. relayer publish/revoke에서는 생략할 수 있지만 실제 sender는 증거에 남습니다.
4. pending/미발견은 `None`, 실패 receipt는 `receipt_status=0`이며 성공 상태를 덧붙이지 않습니다. 성공 거래는 이벤트의 **전체 순서/필드**, receipt 블록 상태, 새 현재 snapshot 상태를 대조합니다. 결과에 `receipt_state/current_state/current_block`을 추가합니다. 이 메서드는 전송하지 않습니다. C의 WalletTransaction/Operation `CONFIRMED`를 직접 반환하거나 DB에 기록하지 않습니다.
5. 발행은 소유·document ID·버전·키/hash/schema·기간·publishedAt/block·nonce 소비를 대조합니다. 다음 버전은 `DocumentSuperseded`→`DocumentPublished` 두 이벤트가 필요합니다. 철회는 동일 소유/버전의 REVOKED를 확인합니다. 발행은 ACTIVE 이전 버전만 SUPERSEDED로 바꾸므로 다음 버전이 발행돼도 철회 버전은 REVOKED여야 하며, SUPERSEDED로 보이면 거부합니다. 불변 필드/nonce/latest 역행과 과거 비활성 버전의 ACTIVE 복구를 거부합니다. 기관 상태와 원 발행키의 퇴역/사고 이력도 각 snapshot에서 읽어 반환합니다. `issuer/publication_key`는 원본 ABI tuple이며 C 모델 변환은 후속입니다.
6. 과거 publish 성공 뒤 최신 상태가 철회·대체·정지·키 사고인 경우 현재 경고 근거를 따로 반환합니다. receipt 블록 끝에 이미 다음 거래가 상태를 바꿨을 수도 있습니다. publish의 상태가 이미 REVOKED/SUPERSEDED이거나 첫 승인 뒤 같은 블록에서 두 번째 승인이 실행된 경우에도 이력을 대조합니다. 현재 유효/EXPIRED/최신 여부를 과거 성공과 혼동하지 않습니다.
7. 제안 생성/승인은 고정 tuple/ID·승인 집합·실행 플래그를 과거/현재에 대조합니다. 정지는 receipt 블록의 SUSPENDED를 확인하며 이미 정지한 no-op은 이벤트 없이 허용합니다. KEY_COMPROMISE는 해당 receipt 블록의 기관 키 compromiseBlock이 필요합니다. 정지 뒤 나중 블록에서 재활성화된 경우 현재 ACTIVE를 별도로 반환합니다.

모든 조회는 1차의 신뢰 설정 chain/deployment/runtime code 검증·EIP-1898 hash pin을 사용하며 projection DB를 읽지 않습니다. 마지막 receipt/current canonical hash 재확인 후 반환합니다. RPC 불가 때 journal·저장 intent를 성공 응답으로 대신 쓰지 않습니다. runtime code hash와 RPC 설정이 신뢰 전제이며 독립 합의/최종성 증명은 아닙니다.

## 실패·보류 경계와 남은 작업

- **동일 블록 정지 후 재활성화/키 교체:** receipt 블록 끝 상태만으로 정지 순간을 분리할 수 없으면 dependency 오류입니다. 이번에는 trace/replay를 추가하지 않았으며, 필요한 경우 transaction-level 증거 수용 기준과 provider 지원을 후속 검토합니다. 새 거래를 자동 전송하지 않습니다.
- **B-C01:** 임의 주소에 대한 `is_approver`와 승인자 3개 constructor/manifest provenance 확인은 남습니다. 이번 승인 목록은 검증 설정된 runtime의 canonical 이벤트와 getter를 대조한 결과이며, 별도 배포 manifest 검증 완료를 뜻하지 않습니다.
- **B-C02:** 승인 목록/count/동일 tx 실행 대조의 B 저수준 구현과 합성 검사는 완료했습니다. C 원본 ProposalView/port 변환·실제 소비 검토/실제 RPC 검증은 대기입니다.
- **B-C03:** 전체 intent·canonical receipt inclusion·이벤트/과거 및 현재 상태 대조는 보강했습니다. UNKNOWN 원본 검색 범위, `find_transaction/submit`, 중계·최종성/확정 깊이와 C Operation/DB 복구 연결은 남습니다. pending과 미발견의 세부 port 상태도 후속입니다.
- C [#63](https://github.com/OriginProof-3web/OriginProof/pull/63)는 조회 당시 Draft/Open, head `6e0e924c77e9a5b83a8522df4d3cfdc797e8822c`입니다. 원본 `wallet_ports.py`는 현재 B 브랜치/원격 integration에 없으며 사본을 만들지 않았습니다.
- 착수 fetch에서 원격 integration `4a9b92d951251658542d924bf48180039041fc5b`의 D 기준/검사 반영을 확인했습니다. 이번 검사는 자기 W5 선행 위의 B 작업 트리 기준이며 D 변경을 병합·수정한 결과로 보고하지 않습니다. 후속 integration 반영/통합 검사에서는 최신 기준을 다시 확인해야 합니다. 과거 phase/종료 PR을 재병합하지 않았습니다.
- **G07 미해결.** 신규 합성 실패 경계 통과는 기존 mixed RPC/reorg·재시작 실패 원인의 재현/해결이 아닙니다. B/C 진단·D 같은 후보 SHA 재검사가 필요합니다.

## 실제 검사

macOS arm64 / Python 3.13, httpx MockTransport·SQLite 합성 기준입니다.

```sh
.uv-venv/bin/pytest -q
.uv-venv/bin/ruff check apps packages/python services scripts
.uv-venv/bin/python scripts/ci/validate_structure.py
node scripts/ci/check_wallet_browser_hashes.mjs
make generate
git diff --exit-code -- packages/schemas/generated fixtures/golden
git diff --check
```

- Python 전체 **281 PASS / 1 live SKIP**, 기존 anyio deprecation warning 1개. 신규 2차 **52 PASS**, 기존 1차 **50 PASS** 포함입니다. 최초 신규 37 PASS 뒤 15개 경계를 추가했습니다.
- 미등록 정확/다른 selector/잘린·nested revert·reorg, 승인 0/1/2·생성/승인/실행 누락·중복/count/tuple/원자성 불일치, intent 전체·numeric type·sender 및 governance sender 필수·receipt 포함 위치, 원본 hash/소유/키/nonce/발행 위치, 다음 버전 원자 대체, 철회 뒤 SUPERSEDED 표시·부활 거부, 첫/둘째 승인·no-op 정지·키 사고·후속 재활성화와 RPC 실패를 검사했습니다.
- 공식 lint·구조·Node hash·원본 재생성 후 생성물 diff·공백 검사 PASS. 초기 줄길이/변수명 lint 경고를 수정했습니다. 기능 검사 실패를 숨기거나 거부 기대값을 완화하지 않았습니다.
- Solidity/ABI 무변경으로 로컬 Foundry 재실행은 생략했습니다. 원격 CI는 PR에서 실제 최종 결과를 별도로 기록합니다.
- 실제 EVM/RPC 배포·직접 제출·PostgreSQL·API/C port·브라우저·독립 QA·v2/consume 전체 실환경·G07·공개 체인·유료 AI는 **미실행**입니다. SG01~16 공유 상태는 변경하지 않았습니다.

## 보존·기여

사용자 미커밋 5개는 SHA256으로 보존하며 C/A/D 생산 코드·공통 모델·생성물/ABI·의존성·배포 파일을 변경하지 않습니다. Codex가 B 구현/합성 검사와 기록을 작성했고 기존 1차 RPC·생성 ABI·W2~W4 컨트랙트·검사 fixture와 설치된 httpx/eth-abi를 재사용했습니다. 사람의 직접 작성·기여 비율·작성자 외 리뷰/단계 승인을 추정하지 않습니다. 팀 Draft PR·개인 비공개 포트폴리오에 검증한 커밋을 공유합니다.
