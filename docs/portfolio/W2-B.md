# W2 / B / 여하민 — V5-W2-B 공동승인·키 증명·정지

- GitHub 계정: `@hamin1228`; 작업일: 2026-10-16 (W2는 개발 단계).
- 상태: Contract 독립 구현·검사 완료 / 실제 배포·Adapter·C/A/D 연결·작성자 외 리뷰 대기.
- 작업: V5-W2-B; 브랜치 `codex/v5-w2-b-governance`.
- 시작 SHA: `c2111e379889d8550aa6ff893d44f576fb78189a` (자기 W1 결과 보존).
- 구현 SHA: `fa333c699d33a223b0d00d97ea353a29fe058f75`.
- 검증 코드 SHA: `0f240dbd2ee42c059e26e4bdbb3d0dc843858fd7`; 이후 기록 커밋은 문서만 변경.
- PR/원격 CI: 미생성·미실행. 원격 push 미실행. 과거 phase를 보존하고 새 단계 대상은 C와 조율 예정.

## 문제와 실제 결과

준비 ABI/Golden만 있던 W2 기관 권한 경로에 고정 승인자 3명 중 2명 승인, EIP-712 키 보유 증명, 기관별 governance nonce, 단독 긴급 정지, 키 교체/사고 이력, 공동 재활성화를 구현했습니다. 발행/철회 함수는 아직 제공하지 않으며 전체 Registry/API 연결 완료가 아닙니다.

## 개인 기여·재사용·판단

Codex가 B의 컨트랙트·컴파일 ABI·검사와 이 기록/기존 인계의 B 절을 작성했습니다. C API/모델·A 웹·D 분석기는 수정하지 않았습니다. 사람의 직접 작성·코드 승인·기여 비율은 대신 주장하지 않습니다.

공유 인터페이스의 구조·이벤트/준비 서명 계약, C의 Python Golden, 기존 Registry 회귀, OpenZeppelin EIP712/ECDSA/SafeCast와 Foundry를 재사용했습니다. 새 의존성·공유 ABI 변경 없이 W2 부분만 구현하고 신규 함수를 성공 stub으로 만들지 않았습니다. 같은 기관의 과거 signer를 새 keyId로 재활성화하는 우회를 막고 키 이력은 보존했습니다. 과거 서버 기관키/gateway/consume을 신규 권한으로 가져오지 않았습니다.

[과거 W2-B 기록](https://github.com/OriginProof-3web/OriginProof/blob/3ef1fd40943914c1450e8bc05047119ab7eabbc0/docs/portfolio/W2-B.md)은 고정 SHA로 보존합니다. 그 기록의 검사·승인·기여를 이번 v5 성과로 합산하거나 덮어쓰지 않았습니다.

## 검증과 실제 범위

Foundry offline **48 PASS**(기존 21 + 신규 W2 27), Python 공유 계약 **24 PASS**, Node hash·ABI/생성물 대조·변경 파일 format·링크/diff 검사 통과. 상세 명령·검사별 의미·ABI 재생성·소비자 경계는 [기존 인계 4.2절](../handoffs/v5_reuse_handoff.md#42-v5-w2-b-공동승인키-증명정지-독립-구현-2026-10-16)을 기준으로 사용합니다.

macOS arm64, solc 0.8.26, Python 3.13.14, Foundry 내부 EVM·합성 키/fixture 기준입니다. 실제 RPC/DB/지갑/공개 네트워크 검사가 아닙니다. 신규 Golden 교차 검사는 고정 fixture 주소에 runtime을 etch해 원본 Python 서명을 소비했으며 실제 주소에 배포한 것으로 표현하지 않습니다. 성능·가스 운영 비용은 미측정입니다.

## 남은 작업·사실 확인

B-C01 승인자 배포 근거, B-C02 canonical 이벤트/승인 목록, B-C03 UNKNOWN/배포 식별과 실제 Adapter가 남습니다. 신규 발행·업무 nonce·버전·철회는 W3/W4 후속입니다. 기존 v1/v2·consume의 원본/회귀는 보존하되 전체 재실행은 이번 범위 밖입니다. G07과 실제 연결·독립 검증은 미해결입니다. W2 단계 전체 완료를 주장하지 않습니다.

- 본인 기여/계약 확인: 미확인.
- C/A/D 소비 리뷰·작성자 외 리뷰: 미확인.
- 사람의 판단: 사용자가 선택한 기존 ABI 유지·B 범위 W2 구현 방식을 반영했으며 코드의 사람 검토는 대기.

## 이전 계획의 개발 기록 보존

아래는 C의 재사용 기준에 포함된 이전 개발 기록입니다. 당시 검사·연결·리뷰 상태를 보존하며, 위 V5 작업의 완료 근거로 합산하지 않습니다.

### W2 / B / 여하민 — 개인 개발 기록

- GitHub 계정: `@hamin1228`
- 실제 작업 기간: 2026-10-01 ~ 2026-10-01 (W2는 달력 주차가 아님)
- 상태: 독립 구현·로컬 EVM 검증 완료 / C 연결·작성자 외 리뷰 대기
- 작업 ID·작업 묶음: `W2-B1`, `W2-B2` / 신뢰 기반
- 작업 branch / 시작 기준 SHA: `codex/w2-b-chain-operations` / W1-B `ca48084`
- 통합 PR: [#26](https://github.com/OriginProof-3web/OriginProof/pull/26)으로 W1/W2 통합 예정

#### 목표와 실제 결과

기존 Registry를 API가 안전하게 변경할 수 있도록 write Adapter를 구현했다. 제출 hash,
receipt, confirmation과 상태 재조회를 분리하고 결과 미확인을 성공으로 처리하지 않는다.
배포 manifest에 deployment identity와 ABI hash를 추가하고 indexer event/checkpoint를
재배포별로 격리했다. 로컬 배포의 관리자·기관 운영자·키 관리자·기관 계정도 분리했다.

#### 개인 기여와 협업

| 작업 ID | 본인이 수행한 일 | 재사용·다른 담당자 기여 | 근거 | 상태 |
| --- | --- | --- | --- | --- |
| W2-B1 | Issuer/Key Writer, ABI 인코딩, 오류/receipt/재조회 결과, manifest 검증, 권한 분리 | 기존 Registry/Reader와 W1-B 계약 재사용 | 통합 PR #26, `apps/api/src/infrastructure/blockchain/` | 독립 완료 |
| W2-B2 | deployment identity, 실제 Anvil 배포·권한 검사, deployment별 projection/checkpoint 및 재시작 검증 | C 준비 branch의 Operation 예약 계약을 읽고 인계 경계 작성 | 통합 PR #26, `services/indexer/`, `packages/contracts/script/` | 독립 완료, C 연결 대기 |

#### 주요 결정과 문제 해결

- Writer가 재시도를 소유하지 않게 했다. 같은 요청의 내구성·중복 방지는 C Operation이
  담당하고 Writer는 한 번 제출한 결과를 CONFIRMED/FAILED/UNKNOWN으로 반환한다.
- receipt status 1만으로 성공 처리하지 않고 1 confirmation과 상태 재조회를 요구했다.
- chain ID만 같아도 새 Anvil 상태일 수 있어 genesis/deployment block hash와
  `deployment_id`를 Reader, Writer, indexer 전체 경계에 추가했다.
- 실제 EVM 첫 검사는 컨테이너에 `.git`이 없어 source SHA 자동 조회가 실패했다.
  테스트가 명시적 검증 SHA를 전달하도록 수정했으며 운영 배포의 실제 SHA 검증은 유지했다.
- 전체 회귀 첫 실행에서는 API health fixture가 구 manifest 형식이라 1개 실패했다.
  fixture를 새 공개 manifest 계약으로 갱신한 뒤 161개가 통과했다.
- 리뷰 피드백: 아직 없음.

#### 검증·시연 증거

| 사례·명령 | 기대 결과 | 실제 결과 | 환경 |
| --- | --- | --- | --- |
| Writer/Reader/projection pytest | 정상·revert·receipt 실패·UNKNOWN·재배포 격리 | 48개 통과 | macOS Python 3.13 |
| 전체 Python 회귀 | API/core/analyzer/indexer 유지 | 161개 통과, live 1개 skip | macOS Python 3.13 |
| `make test-contracts` | Registry 권한·상태 경계 | Foundry 10개 통과 | Docker Foundry 1.4.4 |
| opt-in live chain | 실제 배포·manifest·비인가 거부·Writer/Reader 상태 | 1개 통과 | Docker Anvil chain 31337 |
| Ruff, 웹 lint/typecheck | 정적 검사 | 통과 | 로컬 도구chain |

성능 수치는 측정하지 않았다. 실제 PostgreSQL Operation과 브라우저 E2E는 C/A/D 연결
뒤 검증한다.

#### AI 활용과 본인의 판단

- Codex로 기존 ABI/Reader/indexer와 C Operation 초안을 조사하고 구현·테스트·문서
  초안을 작성했다.
- 결과 미확인 재전송 금지, 배포 identity 경계, 역할 분리, 실제 EVM 검증 범위와
  완료/연결 대기 구분을 저장소 정책에 맞춰 확인했다.

#### 배운 점·한계·다음 작업

- 동일 chain ID와 주소만으로는 재기동된 로컬 체인을 식별할 수 없으므로 genesis와
  deployment block hash가 receipt/checkpoint 복구에 필요하다.
- C는 W2-C1 OperationRow에 Writer의 tx/deployment/receipt/재조회 증거를 연결하고,
  W2-C2/C3에서 인증 주체가 결정한 sender와 issuer만 전달해야 한다.
- A 브라우저 연결, D 독립 실패·재시작 재현, 작성자 외 리뷰와 phase 반영 전에는 W2
  단계 전체 완료가 아니다.
- 포트폴리오 설명 초안: 로컬 EVM 쓰기를 단순 transaction 제출이 아니라 배포 식별,
  권한 분리, receipt, confirmation, 상태 재조회와 재시작 가능한 checkpoint의 한 흐름으로
  구현하고 실제 Anvil에서 비인가 호출과 상태 변화를 검증했다.

#### 사실 확인

- 본인 확인: `@hamin1228` / 2026-10-01 / 작업 내용과 기여 기록 확인 대기
- 작성자 외 리뷰어: 미확인; C Operation 소비자와 B 경로 검토 필요
