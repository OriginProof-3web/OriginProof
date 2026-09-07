# MVP 통합 실행 순서

이 문서는 각 역할의 개발 브랜치를 안전하게 하나의 MVP로 통합하기 위한 실행 순서입니다.
최종 목표는 합성 `Origin Mock Bank` 카드 알림의 정상 입력이 `VERIFIED + ACTIVE`, 금액 변조 입력이
`TAMPERED + AMOUNT_MISMATCH`를 반환하는 것입니다.

김형준님만 `mvp/integration` 및 `main`으로 병합합니다. 다른 역할은 자기 브랜치에 push하고 PR을
생성하며, `main`에 직접 push하지 않습니다.

## 현재 상태와 우선순위

| 우선순위 | 상태 | 담당 | 해야 할 일 |
| --- | --- | --- | --- |
| 0 | 차단 | M3/M4 | 현재 `mvp/chain-core`를 그대로 통합하지 않고 최신 기준에서 체인 변경을 다시 준비합니다. |
| 1 | 준비됨 | 김형준 | `main` 기준으로 `mvp/integration`을 생성합니다. |
| 2 | 준비됨 | M1 | `mvp/backend`을 `mvp/integration`에 PR로 통합합니다. |
| 3 | M1 통합 뒤 시작 | M2 | 최신 `mvp/integration`을 기준으로 후보 필드 추출을 구현하고 `mvp/ai`에 push합니다. |
| 4 | 우선순위 0 해결 뒤 | M3/M4 | 정리된 체인 작업을 `mvp/integration`에 PR로 통합합니다. |
| 5 | 세 PR 통합 뒤 | M1 + 전원 | 실제 체인 어댑터 연결 및 MVP E2E를 검증합니다. |

## 0. M3/M4 브랜치 정리

2026-09-07 확인 기준 `mvp/chain-integration`의 내용은 `mvp/chain-core`에 이미 합쳐져 있습니다.
따라서 두 브랜치를 각각 통합하면 안 됩니다. `mvp/chain-core` 하나만 통합 후보입니다.

하지만 현재 `mvp/chain-core`는 Bootstrap 이후의 공통 scaffold, M1 API, 테스트, 문서 등을 삭제하는
차이를 포함하고 있습니다. 이 상태로 PR을 병합하면 체인 코드뿐 아니라 이미 완성한 MVP 기반도
지워질 수 있으므로 **현재 브랜치를 그대로 PR로 올리거나 병합하지 않습니다.**

M3/M4는 다음 방식으로 정리합니다.

1. 김형준님이 `mvp/integration`을 만든 뒤, M3/M4는 그 최신 SHA에서 새 정리 브랜치를 만듭니다.
2. Contract, ABI, deployment manifest, indexer, `apps/api/src/infrastructure/blockchain/`처럼 자기 소유인 변경만 옮깁니다.
3. 루트 설정, M1 API, Python shared model, fixture, scaffold를 삭제하거나 이전 버전으로 되돌리지 않습니다.
4. API 의존성 또는 공유 Python 계약 변경이 필요하면 M1에게 handoff를 요청합니다. 임의 수정하지 않습니다.
5. `make bootstrap-check`, `make lint`, 소유 영역 테스트를 통과시킨 후 새 PR을 생성합니다.

새 정리 브랜치는 예를 들어 `mvp/chain-ready`로 만들 수 있습니다. 기존 `mvp/chain-core`와
`mvp/chain-integration`은 기록 보존용으로 두고 force push하지 않습니다.

## 1. 김형준님: 통합 브랜치 생성

김형준님은 최신 `main`에서 한 번만 아래 작업을 합니다.

```bash
git switch main
git pull --ff-only origin main
git switch -c mvp/integration
git push -u origin mvp/integration
```

생성 뒤 팀 채널에 `mvp/integration`의 SHA를 공유합니다. 이후 모든 PR의 base branch는
`mvp/integration`입니다.

## 2. M1: Backend를 통합 기준점으로 만들기

M1 작업은 `mvp/backend`의 `bbaa4f9`에 있습니다. 이 브랜치에는 다음이 포함됩니다.

- `CardPaymentNoticeCandidate`, Signed Proof, Verification Result 계약
- `POST /v1/mvp/card-notices/verify`
- PostgreSQL Proof 저장소, Alembic migration, 합성 seed
- 정상/금액 변조 검증용 test-only chain adapter smoke test

김형준님은 GitHub에서 다음 PR을 생성하거나 M1에게 생성을 요청합니다.

| 항목 | 값 |
| --- | --- |
| Base | `mvp/integration` |
| Compare | `mvp/backend` |
| 제목 | `[M1/Backend] MVP verification API and proof storage` |
| 최소 검증 | `make test`, `make mvp-test`, `make db-smoke` |

승인 후 김형준님이 병합합니다. 이 병합이 끝나기 전에는 M2가 예전 계약을 기준으로 구현을 시작하지
않는 것이 안전합니다.

## 3. M2: M1 계약을 기준으로 AI 작업 시작

M1 PR이 병합된 후 M2는 최신 `mvp/integration`에서 작업합니다.

```bash
git fetch origin
git switch -c mvp/ai origin/mvp/integration
```

M2의 출력은 `CardPaymentNoticeCandidate`이며, 알 수 없는 값은 `null`, 추출 신뢰도는 `confidence`에
넣습니다. AI는 `VERIFIED`, `TAMPERED`, 진위 여부를 판단하거나 반환하지 않습니다.

M2 완료 전 확인 사항은 아래와 같습니다.

- `services/analyzer/`와 M2 fixture만 수정했는지 확인합니다.
- 실제 카드 정보, 실제 기관 명칭, API key, 원문 이미지를 commit하지 않습니다.
- Mock provider 기반 정상/누락/형식 오류 테스트를 통과시킵니다.
- PR은 `mvp/ai`에서 `mvp/integration`으로 생성합니다.

## 4. M3/M4: 정리된 체인 PR 통합

우선순위 0의 정리가 끝난 뒤에만 M3/M4 작업을 통합합니다.

| 항목 | 값 |
| --- | --- |
| Base | `mvp/integration` |
| Compare | 정리된 체인 브랜치 |
| 포함 범위 | Contract, ABI, local deployment manifest, chain reader, indexer |
| 제외 범위 | M1 API/공통 scaffold 삭제 또는 되돌림 |

PR 설명에는 deployment manifest 경로, ABI 경로, RPC URL/chain ID, `BlockchainReader` 구현이
준수하는 method와 실제 실행한 테스트를 적습니다.

## 5. M1과 전원: 실제 E2E 연결

M2와 M3/M4 PR이 `mvp/integration`에 병합되면 M1은 Backend와 실제 `BlockchainReader`·Analyzer를
연결합니다. 현재 API는 Proof 저장소까지는 동작하며, 실제 체인 reader가 연결되기 전에는 안전하게
`INCONCLUSIVE`를 반환합니다.

통합 후 아래 순서로 확인합니다.

1. `make bootstrap-check`
2. `make mvp-up`
3. `make seed`
4. `make test`
5. `make mvp-test`
6. `make db-smoke`
7. 정상 합성 입력이 `VERIFIED + ACTIVE`인지 확인합니다.
8. 금액만 바꾼 합성 입력이 `TAMPERED + AMOUNT_MISMATCH`인지 확인합니다.
9. 미등록 Proof, 체인 장애, key revoke에서 과장된 성공 결과가 반환되지 않는지 확인합니다.

실행에 실패하면 다음 PR을 병합하지 않고 현재 통합 단계에서 원인을 해결합니다.

## GitHub PR 생성 규칙

1. GitHub 저장소의 **Pull requests** 탭에서 **New pull request**를 누릅니다.
2. **base**는 항상 `mvp/integration`, **compare**는 자기 작업 브랜치를 선택합니다.
3. 변경 파일에 다른 역할의 파일 삭제나 대량 되돌림이 없는지 먼저 확인합니다.
4. 제목에 역할을 붙이고, 실제 실행한 명령과 결과를 PR 설명에 적습니다.
5. 김형준님과 해당 계약 소유자의 승인을 받은 뒤 김형준님이 병합합니다.
6. 모든 E2E가 통과한 마지막 단계에서만 `mvp/integration`에서 `main`으로 PR을 생성합니다.

## 팀 채널에 공유할 완료 보고 형식

```text
역할:
브랜치와 최신 commit SHA:
PR URL:
수정 경로:
실행한 검증 명령과 결과:
공유 계약 또는 ABI 영향:
M1/M2/M3/M4에 필요한 handoff:
남은 blocker:
```

각자 자신의 브랜치만 push하며, 공유 계약과 다른 담당 경로는 handoff 확인 없이 수정하지 않습니다.
