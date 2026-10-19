# W1 / B / 여하민 — V5-W1-B 계약 검토·독립 검사

- GitHub 계정: `@hamin1228`; 작업일 2026-10-16 (W1은 개발 단계).
- 상태: 부분 완료 — 계약 차이 검토·독립 서명 검사 완료, C/A/D 소비 검토·실제 연결·단계 완료 대기.
- 브랜치: `codex/v5-w1-b-contract-review`; 시작 SHA `9feec138bf3d6d8a379b211583f92db1716e54f2`.
- 기준: 계획서 5.1 / 로컬 v5-shared-0.1, C Draft 0.2는 비교 원본으로만 사용.
- PR: 미생성, push 미실행. 새 단계 PR 대상은 C와 조율 예정이며 과거 phase는 보존.

## 과거 기록과 재사용

이 작업 폴더에 없던 [과거 W1-B 기록](https://github.com/OriginProof-3web/OriginProof/blob/ab86892f1aedc14664e3129231225e79220b7394/docs/portfolio/W1-B.md)은 고정 원본으로 보존합니다. 그 문서의 기존 성과·D 근거·검사·미확인을 이번 v5 완료로 바꾸지 않습니다. 기존 Registry·C 준비 인터페이스·생성 Golden·OpenZeppelin ECDSA와 Foundry 도구를 재사용했습니다. 과거 PR 전체 재병합이나 C 소스 복사는 하지 않았습니다.

## 실제 결과·기여·판단

Codex가 B 범위에서 기존 Registry/Reader/projection과 신규 계약 차이를 검토하고 Solidity 서명 변조/도메인/제안 ID/비정상 서명/fuzz 검사 7개를 추가했습니다. C 고정 head의 ABI/서명/Golden 동일성과 WalletRegistry 소비 경계를 대조했습니다. 사람의 코드 작성·승인·기여 비율이나 C/A/D 확인은 대신 주장하지 않습니다.

상세 전환표·실행 명령·결과·실제 연결 한계·B-C01~03은 [재사용 인계 4.1절](../handoffs/v5_reuse_handoff.md#41-v5-w1-b-계약-검토독립-검사-2026-10-16)을 기준으로 사용합니다. 같은 계약 사본을 만들지 않았습니다. 기존 승인자 조회 ABI 부재·승인 count/주소 목록·UNKNOWN 검색과 배포 식별은 후속 설계/소비 검토 항목입니다.

검증: Foundry 21 PASS(기존 Registry 10/Golden 11, fuzz 각 512회), Python wallet 24 PASS, Node hash·생성물 보존·변경 파일 format·diff/링크 확인. macOS arm64, Python 3.13.14, solc 0.8.26, 로컬 Foundry offline/합성 fixture 기준입니다. 성능은 미측정입니다. 검증한 코드 커밋과 문서 최종 커밋은 별도로 아래에 남깁니다.

## 남은 작업과 사실 확인

새 Registry 구현, 실제 Adapter/manifest·API/DB·브라우저/지갑, 독립 소비 리뷰는 후속입니다. G07은 미해결이고 SG01~16은 NOT_EXECUTED입니다. W1 전체·재사용 항목 전체 완료나 실제 연결 성공으로 기록하지 않습니다. 입력 선정/Decisions API 범위를 변경하지 않았습니다.

- 본인 기여/계약 확인: 미확인.
- 작성자 외 리뷰: 미확인.
- 원격 PR/CI: 이번 작업에서 미생성·미실행.

- 검증한 코드 SHA: `dee70526af24c0878f00bac322d6670c97e5e427` (로컬, 원격 미공유).
- 이후 문서 최종 SHA: 이 파일을 기록한 문서 커밋의 Git 이력으로 확인하며 검사 코드 SHA와 구분합니다.

## 이전 계획의 개발 기록 보존

아래는 C의 재사용 기준에 포함된 이전 개발 기록입니다. 당시 검사·연결·리뷰 상태를 보존하며, 위 V5 작업의 완료 근거로 합산하지 않습니다.

### W1 / B / 여하민 — 개인 개발 기록

- GitHub 계정: `@hamin1228`
- 실제 작업 기간: 2026-10-01 ~ 2026-10-01 (W1은 달력 주차가 아님)
- 상태: 독립 산출물 검증 완료 / C 연결·작성자 외 리뷰 대기
- 작업 ID·작업 묶음: `W1-B1`, `W1-B2` / 신뢰 기반
- 단계 브랜치 / 시작 기준 SHA / 검증한 코드 SHA: `phase/W1` 예정 / `3295a71c10a1a99c523d3cfefde91b5737b737ac` / 동일 SHA
- 단계 완료 PR: 미생성; B 작업 PR [#26](https://github.com/OriginProof-3web/OriginProof/pull/26)

#### 목표와 실제 결과

현재 Issuer/Key Registry, ABI, 배포와 Reader의 실제 동작을 조사하고 B/C 사이의
입력·반환·오류·확정·조회 계약을 작성했다. ADR 0001의 키 분리, 정상 교체와 유출
폐기, gateway와 recipient binding, 원자적 consume, 재시작·재배포 정책을
ProofStatusRegistry ABI 초안과 구현 명세로 구체화했다.

애플리케이션 코드와 현재 ABI는 변경하지 않았다. ProofStatusRegistry 구현은 W4,
write Adapter와 강화된 manifest는 W2 입력이다.

#### 개인 기여와 협업

| 작업 ID | 본인이 수행한 일 | 재사용·다른 담당자 기여 | 근거 | 상태 |
| --- | --- | --- | --- | --- |
| W1-B1 | 실제 Issuer/Key ABI·권한·Reader·배포 조사, Adapter 명령/반환/오류/확정/조회 계약 작성 | 기존 MVP Registry/Reader와 C PR #23의 신청 상태 초안 재사용 | 작업 PR [#26](https://github.com/OriginProof-3web/OriginProof/pull/26) | 독립 완료 |
| W1-B2 | 권한·키 분리, 상태 전이, ProofStatusRegistry ABI, gateway/binding, receipt·복구·재배포 명세 작성 | 승인된 ADR 0001 정책 재사용; W1-C3 검토 대기 | 작업 PR [#26](https://github.com/OriginProof-3web/OriginProof/pull/26) | 독립 완료, 연결 대기 |

#### 주요 결정과 문제 해결

- 기존 Issuer/Key ABI는 W1에서 바꾸지 않고 실제 함수명을 Adapter 계약에 사용했다.
- `APPROVED_PENDING_CHAIN`을 체인 ACTIVE와 분리하고 receipt + 1 confirmation + 상태
  재조회가 끝난 경우에만 CONFIRMED로 정의했다.
- 정상 키 교체와 유출 폐기를 분리했다. 기존 키 기간 종료만으로 과거 Proof를
  무효화하지 않으며, REVOKED 키는 과거 Proof도 현재 사용 불가로 처리한다.
- 조회는 상태를 바꾸지 않고 consume만 원자적 상태 전이를 수행하도록 경계를 정했다.
- 첫 검증에서 Docker daemon이 없어 계약 검사가 중단됐고, Docker를 기동한 뒤 같은
  integration SHA에서 재실행해 통과시켰다.
- 리뷰 피드백: 아직 없음.

#### 검증·시연 증거

| 사례·명령 | 기대 결과 | 실제 결과 | SHA·환경 | 증거 |
| --- | --- | --- | --- | --- |
| `make bootstrap-check` | 구조·환경 확인 | 통과 | `3295a71`, macOS local | 로컬 실행 기록 |
| `make env-fingerprint` | 환경 fingerprint 생성 | 통과 | `3295a71`, Python 3.13.14, uv 0.11.28, Docker 29.4.3 | `build/environment_fingerprint.json` 로컬 생성물 |
| `make mvp-test` | API/analyzer/기존 계약 회귀 | API 5, analyzer 97, 통합 102, Foundry 10개 통과 | `3295a71`, Docker local EVM build | 로컬 실행 기록 |
| `make smoke` | API/analyzer health | 통과 | `3295a71`, Docker Compose | 로컬 실행 기록 |
| ABI·ADR·Reader 대조 | 문서 함수·상태·오류가 현재 구현과 승인 정책을 구분 | 통과; 새 Proof ABI는 초안으로 명시 | `3295a71` | 작업 PR diff |

`make mvp-up`은 API/analyzer를 정상 기동했으나 기존 다른 컨테이너가 사용 중인
호스트 3000 포트 때문에 web 컨테이너만 bind에 실패했다. W1-B 문서/계약 검증과
API/analyzer smoke에는 영향이 없으며 브라우저 단계 검증 근거로 사용하지 않는다.

측정 성능 수치는 없다.

#### AI 활용과 본인의 판단

- Codex를 저장소 지침·계획·ADR·ABI 조사, 계약 문서 초안과 일관성 점검에 사용했다.
- 실제 기준 SHA, 기존 사용자 변경 보존, 권한 분리, 상태 전이, 오류/확정 경계와
  테스트 결과의 완료 범위는 사용자 지시와 저장소 정책에 맞춰 검토했다.

#### 배운 점·한계·다음 작업

- 기존 Reader는 기관·키의 일관된 block 조회를 제공하지만 write Operation과 Proof
  상태는 아직 없다. 미등록과 RPC/ABI 실패를 분리하는 원칙을 후속 Adapter에도
  유지해야 한다.
- `origin/phase/W1@ae8c8e2`는 시작 기준 integration `3295a71`보다 뒤처져 있다.
  단계 조율자가 phase를 동기화한 뒤 이 작업 branch를 최신 phase에 맞춰야 한다.
- C의 W1-C3 구현 검토, 작성자 외 리뷰, A/C/D 결과와 단계 통합 검증은 남아 있다.
- 포트폴리오 설명 초안: 기존 Registry를 실제 ABI 기준으로 조사하고, 제출 성공을
  체인 완료로 오인하지 않는 Adapter 경계와 Proof 상태/consume 신뢰 모델을 W2/W4가
  구현 가능한 계약으로 정리했다. 기존 MVP 회귀와 로컬 EVM 계약 검사를 통과했다.

#### 사실 확인

- 본인 확인: `@hamin1228` / 2026-10-01 / 작업 내용과 기여 기록 확인 대기
- 작성자 외 리뷰어: 미확인; W1-C3 담당자와 Contract/Adapter 소비자 리뷰 필요
