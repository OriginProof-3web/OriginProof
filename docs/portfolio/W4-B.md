# W4 / B / 여하민 — V5-W4-B 버전·철회·키 이력

- 계정 `@hamin1228`, 작업일 2026-10-16 (W4는 개발 단계).
- 상태: Contract 독립 구현·검사 완료 / 실제 배포·Adapter·API/DB·지갑·D 독립 검증·작성자 외 리뷰 대기.
- 브랜치 `codex/v5-w4-b-document-lifecycle`, 시작 `004f774e89a278ec8ab4c5dba233d0d7c3eb0a97` (자기 W3).
- 검증 코드 `a7b47fdd91e516d67c1a7d1db6be43f967ceabe8`. 이후 문서 커밋은 코드/검사 결과와 구분합니다.

## 문제·실제 결과·재사용

Codex가 B의 기존 발행 컨트랙트를 버전별 저장·최신+1·원자적 대체와 기관 현재 키의 EIP-712 철회로 확장하고 ABI/검사·기록을 작성했습니다. W2/W3 권한·키 이력·서명·nonce/Golden·OpenZeppelin·Foundry와 기존 회귀를 재사용했습니다. C/A/D 생산 코드·공유 인터페이스·의존성을 수정하지 않았습니다. 사람의 직접 작성·기여 비율·리뷰 승인은 대신 기록하지 않습니다.

원본/hash를 덮어쓰지 않고 과거 상태와 최신 포인터를 분리했습니다. 정지 중에도 비사고 현재 키 철회를 허용하며, 정상 교체와 사고 키를 구분합니다. 최신 철회로 과거 버전을 되살리지 않습니다. 이미 철회된 최신 뒤 새 버전 발행 시 이전 현재 state는 공유 대체 규칙상 SUPERSEDED로 전이하고 철회 이벤트는 남깁니다. 실제 소비자는 상태와 이벤트 이력을 구분해야 합니다.

[과거 W4-B 기록](https://github.com/OriginProof-3web/OriginProof/blob/3ef1fd40943914c1450e8bc05047119ab7eabbc0/docs/portfolio/W4-B.md)을 고정 SHA로 보존하며 기존 v2/gateway/consume의 당시 검사와 이번 v5 성과를 섞지 않습니다. W3 단일 버전 저장에서 layout이 바뀌므로 실제 연결은 별도 새 배포·manifest와 검증이 필요합니다. 주소 덮어쓰기/업그레이드/migration은 실행하지 않았습니다.

## 실패·검증·한계

최초 W4 검사 6개가 memory struct의 검사 도우미 alias 때문에 실패했습니다. 사본 생성으로 기대값을 분리한 뒤 전체 Foundry **88 PASS**, 추가한 철회 high-s/v 사례의 대상 검사 **1 PASS**를 확인했습니다. 원본 보존/거부 기대값은 완화하지 않았습니다. 자세한 명령·실패 원인·상태/이벤트·실행 범위는 [인계 4.4절](../handoffs/v5_reuse_handoff.md#44-v5-w4-b-버전원자적-대체서명-철회-2026-10-16)에 있습니다.

Python **179 PASS/1 live SKIP**, Node hash·생성물·공유 12함수/7이벤트 ABI·format/diff/문서 경로 검사 통과. macOS arm64, Python 3.13.14, solc0.8.26, 내부 EVM·합성 fixture 기준이며 실제 RPC/네트워크 동시성·지갑 검사가 아닙니다. 성능/운영 가스 비용은 미측정입니다.

## 다음 작업·사실 확인

W5 Adapter/indexer·새 배포 식별·canonical event/receipt·현재 상태 연결, C/A/D 실제 소비와 독립 리뷰, G07이 남습니다. W4 전체 단계 완료를 주장하지 않습니다. 사용자 원본 변경 5개와 과거 브랜치는 보존했습니다.

- 본인 기여/계약 확인·작성자 외 리뷰: 미확인.
- 선행 Draft: #67, 과거 phase로 병합하거나 다른 담당 브랜치를 가져오지 않음.
- W4 push/PR/CI: 이 기록 뒤 공유하고 원격 PR 본문에 실제 SHA/상태를 남김. CI 통과를 미리 기록하지 않음.

## 이전 계획의 개발 기록 보존

아래는 C의 재사용 기준에 포함된 이전 개발 기록입니다. 당시 검사·연결·리뷰 상태를 보존하며, 위 V5 작업의 완료 근거로 합산하지 않습니다.

### W4 / B / 여하민 — 개인 개발 기록

- GitHub 계정: `@hamin1228`
- 실제 작업일: 2026-10-02 (W4는 달력 주차가 아님)
- 작업 ID: `W4-B1`, `W4-B2`, `W4-B3`
- 준비 브랜치: `codex/w4-b-proof-lifecycle`; `phase/W4` 생성 전 독립 작업
- 시작 기준: `origin/integration@3295a71` → 본인 W3-B 선행 SHA `92e0e94` 반영
- 상태: B 독립 구현·로컬 EVM 검증; C 연결·작성자 외 리뷰·단계 PR 대기

#### 수행한 작업

| 작업 | 개인 구현·검증 | 재사용·협업 |
| --- | --- | --- |
| W4-B1 | Proof commitment 등록·폐기·조회, 기관 계정 권한, 반복 폐기 무변경, event/ABI | W1/W2 Issuer/Key Registry, W3-B3 후보와 ADR 재사용 |
| W4-B2 | trusted gateway의 issuer/recipient binding, 현재 기관·키/기간/폐기/소비 검사, 원자적 1회 consume와 경쟁·직접 호출·경계 검사 | C의 서명·세션 검증은 후속 실제 연결 |
| W4-B3 | 새 로컬 배포/manifest, Proof Reader/Writer prepare·receipt·재조회, event decoder/projection, 실제 Anvil 연동 | W2 Writer Operation 복구 계약과 기존 projection 재사용 |

#### 주요 판단

- gateway는 서버가 검증한 서명·로그인 결과를 대행하는 권한이다. Contract 자체가
  서명된 JSON이나 웹 세션을 다시 검사한다고 주장하지 않는다.
- 등록 commitment와 Proof owner·binding은 온체인에서 고정하고, 현재 사용 가능 여부는
  Reader가 체인을 다시 읽는다. 이벤트 projection은 이력·재시작용이다.
- `SUBMITTED` hash는 확정이 아니다. canonical 성공 receipt와 최종 상태 재조회 뒤
  `CONFIRMED`를 반환하며 실패/reorg/RPC 단절은 성공으로 바꾸지 않는다.
- phase/W4와 W3-B3 소비 리뷰가 아직 없으므로 W4의 팀 연결·단계 완료를 선언하지 않는다.

#### 검증 근거

| 검사 | 실제 결과 |
| --- | --- |
| Foundry 전체 | 22 passed, 0 failed; 신규 Proof 권한·반복·경쟁·기간·binding·시각 0 경계 포함 |
| Reader/Writer/projection 단위 | 75 passed; 미등록·network·RPC·reorg와 replay 포함 |
| 임시 Anvil 통합 | 1 passed; 새 배포 → 등록 → 상태 재조회 → consume → 실패 receipt → 폐기 → 실제 event projection |
| Python 전체 관련 회귀 | 255 passed, opt-in 4 skipped |
| Ruff·구조·ABI | 변경 Python 형식/정적 검사, 저장소 구조, 생성 ABI와 forge artifact 일치 |

CI·외부 리뷰는 아직 실행/확인하지 않았다. 외부 유료 RPC와 보존 DB 초기화는 실행하지
않았다. 공개 합성 데이터와 매 실행 새 임시 로컬 체인만 사용했다.

#### AI 활용과 후속

Codex로 기존 ABI/Writer/Reader·ADR를 추적하고 Contract·Adapter·검사·문서 초안을
작성했다. 권한 분리, 동일 제출의 복구, 현재 체인 조회의 판정 권위와 C 영역 비수정
경계를 확인했다. C는 새 Adapter를 실제 발행·폐기·consume API와 Operation DB에
연결하고, D는 독립 재현을 수행해야 한다.

- 본인 확인: `@hamin1228` / 2026-10-02 / 기록 확인 대기
- 작성자 외 리뷰: 미확인
