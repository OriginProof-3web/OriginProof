# W2 / B / 여하민 — 개인 개발 기록

- GitHub 계정: `@hamin1228`
- 실제 작업 기간: 2026-10-01 ~ 2026-10-01 (W2는 달력 주차가 아님)
- 상태: 독립 구현·로컬 EVM 검증 완료 / C 연결·작성자 외 리뷰 대기
- 작업 ID·작업 묶음: `W2-B1`, `W2-B2` / 신뢰 기반
- 작업 branch / 시작 기준 SHA: `codex/w2-b-chain-operations` / W1-B `ca48084`
- 통합 PR: [#26](https://github.com/OriginProof-3web/OriginProof/pull/26)으로 W1/W2 통합 예정

## 목표와 실제 결과

기존 Registry를 API가 안전하게 변경할 수 있도록 write Adapter를 구현했다. 제출 hash,
receipt, confirmation과 상태 재조회를 분리하고 결과 미확인을 성공으로 처리하지 않는다.
배포 manifest에 deployment identity와 ABI hash를 추가하고 indexer event/checkpoint를
재배포별로 격리했다. 로컬 배포의 관리자·기관 운영자·키 관리자·기관 계정도 분리했다.

## 개인 기여와 협업

| 작업 ID | 본인이 수행한 일 | 재사용·다른 담당자 기여 | 근거 | 상태 |
| --- | --- | --- | --- | --- |
| W2-B1 | Issuer/Key Writer, ABI 인코딩, 오류/receipt/재조회 결과, manifest 검증, 권한 분리 | 기존 Registry/Reader와 W1-B 계약 재사용 | 통합 PR #26, `apps/api/src/infrastructure/blockchain/` | 독립 완료 |
| W2-B2 | deployment identity, 실제 Anvil 배포·권한 검사, deployment별 projection/checkpoint 및 재시작 검증 | C 준비 branch의 Operation 예약 계약을 읽고 인계 경계 작성 | 통합 PR #26, `services/indexer/`, `packages/contracts/script/` | 독립 완료, C 연결 대기 |

## 주요 결정과 문제 해결

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

## 검증·시연 증거

| 사례·명령 | 기대 결과 | 실제 결과 | 환경 |
| --- | --- | --- | --- |
| Writer/Reader/projection pytest | 정상·revert·receipt 실패·UNKNOWN·재배포 격리 | 48개 통과 | macOS Python 3.13 |
| 전체 Python 회귀 | API/core/analyzer/indexer 유지 | 161개 통과, live 1개 skip | macOS Python 3.13 |
| `make test-contracts` | Registry 권한·상태 경계 | Foundry 10개 통과 | Docker Foundry 1.4.4 |
| opt-in live chain | 실제 배포·manifest·비인가 거부·Writer/Reader 상태 | 1개 통과 | Docker Anvil chain 31337 |
| Ruff, 웹 lint/typecheck | 정적 검사 | 통과 | 로컬 도구chain |

성능 수치는 측정하지 않았다. 실제 PostgreSQL Operation과 브라우저 E2E는 C/A/D 연결
뒤 검증한다.

## AI 활용과 본인의 판단

- Codex로 기존 ABI/Reader/indexer와 C Operation 초안을 조사하고 구현·테스트·문서
  초안을 작성했다.
- 결과 미확인 재전송 금지, 배포 identity 경계, 역할 분리, 실제 EVM 검증 범위와
  완료/연결 대기 구분을 저장소 정책에 맞춰 확인했다.

## 배운 점·한계·다음 작업

- 동일 chain ID와 주소만으로는 재기동된 로컬 체인을 식별할 수 없으므로 genesis와
  deployment block hash가 receipt/checkpoint 복구에 필요하다.
- C는 W2-C1 OperationRow에 Writer의 tx/deployment/receipt/재조회 증거를 연결하고,
  W2-C2/C3에서 인증 주체가 결정한 sender와 issuer만 전달해야 한다.
- A 브라우저 연결, D 독립 실패·재시작 재현, 작성자 외 리뷰와 phase 반영 전에는 W2
  단계 전체 완료가 아니다.
- 포트폴리오 설명 초안: 로컬 EVM 쓰기를 단순 transaction 제출이 아니라 배포 식별,
  권한 분리, receipt, confirmation, 상태 재조회와 재시작 가능한 checkpoint의 한 흐름으로
  구현하고 실제 Anvil에서 비인가 호출과 상태 변화를 검증했다.

## 사실 확인

- 본인 확인: `@hamin1228` / 2026-10-01 / 작업 내용과 기여 기록 확인 대기
- 작성자 외 리뷰어: 미확인; C Operation 소비자와 B 경로 검토 필요
