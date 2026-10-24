# W3 / B / 여하민 — V5-W3-B 최초 버전 기관 서명 발행

- GitHub 계정 `@hamin1228`, 2026-10-16 (W3는 개발 단계).
- 상태: Contract 독립 구현·검사 완료 / 실제 배포·Adapter·API/DB·지갑·작성자 외 리뷰 대기.
- 브랜치 `codex/v5-w3-b-publication`, 시작 `5f91ac8e3405ac2f3bbe9ae19e15b81dd1f58c6e` (자기 W2).
- 검증 코드 SHA `f8cc461f725340e0a0d4f992aa849288a200780f`; 이후 기록 커밋은 문서만 변경.

## 실제 변경·기여·재사용

Codex가 B 소유의 신규 발행 컨트랙트·실제 ABI·검사와 B 인계/개인 기록을 작성했습니다. W2 기관/키 저장소와 block helper의 내부 상속 접근만 열고 기존 권한 검사·공유 ABI를 유지했습니다. C/A/D 생산 코드와 기존 사용자 변경을 수정하지 않았습니다. 사람의 코드 승인·기여 비율은 대신 기록하지 않습니다.

W2 공동승인/키/정지, C의 공통 원본/서명 계약·두 Golden, OpenZeppelin EIP712/ECDSA/SafeCast와 기존 회귀를 재사용했습니다. 원본/보호 내용 전체는 체인에 넣지 않고 서명된 commitment를 보존합니다. 기관의 현재 키·문서 ID 소유·업무 nonce·시각/schema를 검증하고 최초 버전만 원자적으로 저장합니다. 발행키와 중계자의 msg.sender 권한을 분리합니다.

[과거 W3-B 기록](https://github.com/OriginProof-3web/OriginProof/blob/3ef1fd40943914c1450e8bc05047119ab7eabbc0/docs/portfolio/W3-B.md)은 고정 SHA로 보존하며 그 성과·리뷰/실제 연결을 이번 v5 완료로 합산하지 않습니다.

## 검증·실패·범위

Foundry **68 PASS**(기존48+신규20, fuzz 총5개 각512), Python **179 PASS/1 live SKIP**, Node hash·ABI/생성물·변경 파일 format·문서/diff 검사 통과입니다. macOS arm64, Python 3.13.14, solc 0.8.26, 내부 EVM·합성 데이터 기준입니다. 최초 fmt check의 assembly 줄바꿈은 재포맷해 통과했으며 기능 실패로 기록하지 않습니다.

두 템플릿의 원본 Python Golden은 합성 fixture 주소에 runtime을 etch해 기존 서명을 소비했습니다. 실제 RPC 배포/지갑이나 원본 bytes 내용의 사실성을 검증한 것이 아닙니다. 시각/서명/소유권/nonce·정지·키 교체·16필드 변조 거부·실패 상태 불변을 검사했습니다. 명령·상세 결과·ABI 재생성·인계는 [기존 인계 4.3절](../handoffs/v5_reuse_handoff.md#43-v5-w3-b-최초-버전-기관-서명-발행-2026-10-16)을 기준으로 사용합니다.

## 다음 작업·사실 확인

다음 버전·대체·철회는 W4이며 이번에 구현하지 않았습니다. B 실제 Adapter/manifest·C/A 원본/지갑 연결·D 독립 검사·G07·v2/consume 전체 회귀·공개 체인/성능은 남아 있습니다. 실제 W3 단계 완료로 표시하지 않습니다.

- 본인 기여/계약 확인·작성자 외 리뷰: 미확인.
- 선행 Draft PR: 기준 #64 → W1 #65 → W2 #66, 병합하지 않음.
- W3 PR/CI: 이 기록 이후 생성·조회 결과를 원격 PR 본문에 남기며 원격 CI 통과를 미리 주장하지 않음.

## 이전 계획의 개발 기록 보존

아래는 C의 재사용 기준에 포함된 이전 개발 기록입니다. 당시 검사·연결·리뷰 상태를 보존하며, 위 V5 작업의 완료 근거로 합산하지 않습니다.

### W3 / B / 여하민 — 개인 개발 기록

- GitHub 계정: `@hamin1228`
- 실제 작업일: 2026-10-02 (W3는 달력 주차가 아님)
- 상태: B 독립 구현·교차검사 완료 / C 소비 연결·작성자 외 리뷰 대기
- 작업 ID: `W3-B1`, `W3-B2`, `W3-B3`
- 작업 branch / 시작 기준 SHA: `codex/w3-b-proof-boundaries` / `phase/W3@1f8ed632ea9c74091abaf2fe2ec32882038f731f`
- PR 대상: `phase/W3`

#### 목표와 실제 결과

발행과 검증이 서로 다른 블록의 기관·키 상태를 섞지 않도록 Reader에 동일 블록
Registry snapshot을 추가했다. Finals v2 공개 fixture의 canonical JSON, Keccak digest와
복구 signer를 Python에서 검증하고, 같은 bytes의 EVM digest를 Foundry에서 교차검사했다.
W4 `ProofStatusRegistry` 구현 전에 C와 합의할 ABI·권한·상태·오류·복구 경계를 문서화했다.

#### 개인 기여와 협업

| 작업 ID | 본인이 수행한 일 | 재사용·다른 담당자 기여 | 상태 |
| --- | --- | --- | --- |
| W3-B1 | 기관·키를 동일 canonical block에서 읽는 snapshot, block/deployment 증거, 상태·기간 판정과 오류 검사 | W1/W2 Registry, manifest, Reader 계약 재사용 | 독립 구현 완료, C 연결 대기 |
| W3-B2 | PAYMENT_REQUEST·OFFICIAL_DOCUMENT v2 canonical bytes/digest/signer 및 domain/network/schema/proof type 경계 검사 | C가 확정한 core 모델과 공개 golden fixture 재사용 | 교차검사 완료 |
| W3-B3 | W4 ProofStatusRegistry 후보 ABI, 권한, lifecycle, event/error와 Writer 복구 순서 작성 | ADR 0001과 W2 Operation 복구 계약 재사용 | C 소비 리뷰·W4 구현 대기 |

C의 `feat/w3-c-issuance`는 읽어서 소비 지점을 확인했지만 cherry-pick하거나 C 소유 API를
수정하지 않았다. C는 발행·검증 흐름의 개별 `get_issuer`/`get_key` 조회를
`get_issuer_key_snapshot`으로 연결해야 한다.

#### 주요 결정과 문제 해결

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

#### 검증·시연 증거

| 사례·명령 | 실제 결과 | 환경 |
| --- | --- | --- |
| Ruff format/check | 변경 Python 5개 통과 | macOS, Ruff |
| Python 전체 관련 회귀 | 248개 통과, opt-in 4개 제외 | Python 3.13 |
| `forge test` | 12개 통과(새 v2 digest 경계 2개 포함) | Foundry |
| opt-in live chain | 1개 통과: 임시 Anvil 배포, snapshot, API/Writer 상태 변경 | Anvil chain 31337 |

실제 외부 RPC·유료 호출, 보존 DB 초기화, C API/DB 연결은 실행하지 않았다. 테스트는 공개
합성 fixture와 매 실행 새로 생성한 로컬 키·임시 Anvil만 사용했다.

#### AI 활용과 본인의 판단

Codex로 개발 계획·ADR·담당 인계와 기존 Reader/fixture/C 준비 branch를 조사하고 구현·검사·문서
초안을 작성했다. 동일 블록 snapshot 범위, 오류를 미등록으로 축소하지 않는 정책, Solidity
교차검사의 한계와 W4 후보 계약의 비확정 상태를 직접 확인해 기록했다.

#### 한계와 다음 작업

- C는 snapshot 반환값과 오류를 발행·검증 use case에 연결하고 API/DB 실패 경계를 검사해야 한다.
- C와 B는 W4 구현 전에 register/revoke/consume의 actor binding과 gateway 권한을 함께 검토해야 한다.
- D의 독립 QA, 작성자 외 리뷰, A/C 결과와 `phase/W3` 통합 전에는 W3 전체 완료가 아니다.

#### 사실 확인

- 본인 확인: `@hamin1228` / 2026-10-02 / 작업 내용과 기여 기록 확인 대기
- 작성자 외 리뷰어: 미확인; C 소비자와 B 경로 리뷰 필요
