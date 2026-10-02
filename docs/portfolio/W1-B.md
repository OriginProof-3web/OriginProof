# W1 / B / 여하민 — 개인 개발 기록

- GitHub 계정: `@hamin1228`
- 실제 작업 기간: 2026-10-01 ~ 2026-10-01 (W1은 달력 주차가 아님)
- 상태: 독립 산출물 검증 완료 / C 연결·작성자 외 리뷰 대기
- 작업 ID·작업 묶음: `W1-B1`, `W1-B2` / 신뢰 기반
- 단계 브랜치 / 시작 기준 SHA / 검증한 코드 SHA: `phase/W1` 예정 / `3295a71c10a1a99c523d3cfefde91b5737b737ac` / 동일 SHA
- 단계 완료 PR: 미생성; B 작업 PR [#26](https://github.com/OriginProof-3web/OriginProof/pull/26)

## 목표와 실제 결과

현재 Issuer/Key Registry, ABI, 배포와 Reader의 실제 동작을 조사하고 B/C 사이의
입력·반환·오류·확정·조회 계약을 작성했다. ADR 0001의 키 분리, 정상 교체와 유출
폐기, gateway와 recipient binding, 원자적 consume, 재시작·재배포 정책을
ProofStatusRegistry ABI 초안과 구현 명세로 구체화했다.

애플리케이션 코드와 현재 ABI는 변경하지 않았다. ProofStatusRegistry 구현은 W4,
write Adapter와 강화된 manifest는 W2 입력이다.

## 개인 기여와 협업

| 작업 ID | 본인이 수행한 일 | 재사용·다른 담당자 기여 | 근거 | 상태 |
| --- | --- | --- | --- | --- |
| W1-B1 | 실제 Issuer/Key ABI·권한·Reader·배포 조사, Adapter 명령/반환/오류/확정/조회 계약 작성 | 기존 MVP Registry/Reader와 C PR #23의 신청 상태 초안 재사용 | 작업 PR [#26](https://github.com/OriginProof-3web/OriginProof/pull/26) | 독립 완료 |
| W1-B2 | 권한·키 분리, 상태 전이, ProofStatusRegistry ABI, gateway/binding, receipt·복구·재배포 명세 작성 | 승인된 ADR 0001 정책 재사용; W1-C3 검토 대기 | 작업 PR [#26](https://github.com/OriginProof-3web/OriginProof/pull/26) | 독립 완료, 연결 대기 |

## 주요 결정과 문제 해결

- 기존 Issuer/Key ABI는 W1에서 바꾸지 않고 실제 함수명을 Adapter 계약에 사용했다.
- `APPROVED_PENDING_CHAIN`을 체인 ACTIVE와 분리하고 receipt + 1 confirmation + 상태
  재조회가 끝난 경우에만 CONFIRMED로 정의했다.
- 정상 키 교체와 유출 폐기를 분리했다. 기존 키 기간 종료만으로 과거 Proof를
  무효화하지 않으며, REVOKED 키는 과거 Proof도 현재 사용 불가로 처리한다.
- 조회는 상태를 바꾸지 않고 consume만 원자적 상태 전이를 수행하도록 경계를 정했다.
- 첫 검증에서 Docker daemon이 없어 계약 검사가 중단됐고, Docker를 기동한 뒤 같은
  integration SHA에서 재실행해 통과시켰다.
- 리뷰 피드백: 아직 없음.

## 검증·시연 증거

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

## AI 활용과 본인의 판단

- Codex를 저장소 지침·계획·ADR·ABI 조사, 계약 문서 초안과 일관성 점검에 사용했다.
- 실제 기준 SHA, 기존 사용자 변경 보존, 권한 분리, 상태 전이, 오류/확정 경계와
  테스트 결과의 완료 범위는 사용자 지시와 저장소 정책에 맞춰 검토했다.

## 배운 점·한계·다음 작업

- 기존 Reader는 기관·키의 일관된 block 조회를 제공하지만 write Operation과 Proof
  상태는 아직 없다. 미등록과 RPC/ABI 실패를 분리하는 원칙을 후속 Adapter에도
  유지해야 한다.
- `origin/phase/W1@ae8c8e2`는 시작 기준 integration `3295a71`보다 뒤처져 있다.
  단계 조율자가 phase를 동기화한 뒤 이 작업 branch를 최신 phase에 맞춰야 한다.
- C의 W1-C3 구현 검토, 작성자 외 리뷰, A/C/D 결과와 단계 통합 검증은 남아 있다.
- 포트폴리오 설명 초안: 기존 Registry를 실제 ABI 기준으로 조사하고, 제출 성공을
  체인 완료로 오인하지 않는 Adapter 경계와 Proof 상태/consume 신뢰 모델을 W2/W4가
  구현 가능한 계약으로 정리했다. 기존 MVP 회귀와 로컬 EVM 계약 검사를 통과했다.

## 사실 확인

- 본인 확인: `@hamin1228` / 2026-10-01 / 작업 내용과 기여 기록 확인 대기
- 작성자 외 리뷰어: 미확인; W1-C3 담당자와 Contract/Adapter 소비자 리뷰 필요

## 2026-10-02 D의 근거 보완

위 본인 원 기록은 문서 작성 당시의 상태로 보존합니다. 이후 PR #26은 W1-B1/B2와 W2-B1/B2를 함께 포함해 C 승인 후 `phase/W1`에 병합됐습니다. Writer·manifest·projection 변경을 현재 없는 구현으로 해석하지 않습니다. [혼합 범위·리뷰 근거](../qa/w1-scope-and-reviews.md)를 참조합니다.

D/Codex는 `phase/W1@0308cb24`에서 B 명세와 C3 모델 경계를 대조했고, 수정 후보 `f1de961`에서 Foundry 컨테이너 Contract 10개와 기존 Reader/Writer/indexer 회귀를 확인했습니다. Foundry cast와 C v2 Golden의 signing digest 및 ID hash도 일치했습니다. [실제 결과](../qa/w1-final-verification.md)는 D 검증이며 B 본인의 C3 소비 승인으로 표시하지 않습니다.

단계 승격 초안은 [PR #39](https://github.com/OriginProof-3web/OriginProof/pull/39)입니다. B 본인의 이 기록/계약 확인은 아직 미확인입니다.
