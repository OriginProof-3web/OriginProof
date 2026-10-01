# M4 — 배포·체인 조회·이벤트 저장

> **MVP 과거 기록 — 현재 작업 지시로 사용하지 마세요.** 당시 역할·브랜치·미완료 상태·설정값을 보존한 문서입니다. 현재 개발은 [시작 안내](../../START_HERE.md)와 [개발 계획서](../development_plan.md)를 따르며, 아래의 실행/병합 지시는 자동으로 적용하지 않습니다.

M3 계약의 상태를 M1 API가 이해하는 형식으로 전달합니다.
최종 증명 판정은 M1이 담당하며, M4는 신뢰 상태와 조회 실패를 정확하게 전달합니다.

## 구조와 동작 순서

1. `packages/contracts/script/DeployLocal.s.sol`이 로컬 체인에 계약과 합성 기관·키를 등록합니다.
2. `packages/contracts/script/deploy_local.py`가 Foundry 산출물에서 ABI를 추출하고 배포 manifest를 만듭니다.
3. `apps/api/src/infrastructure/blockchain/reader.py`가 문자열 ID를 keccak256으로 변환해 JSON-RPC로 조회합니다.
4. 조회한 상태와 UTC 유효 기간을 M1의 `IssuerRecord`·`KeyRecord`로 반환합니다.
5. `services/indexer/src/originproof_indexer/projection.py`는 이벤트 위치와 재시작 checkpoint를 SQLAlchemy로 저장합니다.

Reader의 공개 메서드는 `get_issuer`, `get_key`, `is_key_valid`입니다.
각 메서드 내부의 조회는 같은 블록 번호를 사용합니다. 여러 메서드 호출 전체를 하나의 블록으로
고정하는 것은 아닙니다. issuer 해시는 역변환할 수 없으므로 생성자의 `issuer_ids`에 알려진 ID를 제공합니다.

- 실제 미등록만 `None`으로 반환합니다.
- RPC·ABI·manifest 오류나 알 수 없는 issuer 해시는 `DependencyUnavailableError`입니다.
- M1은 이 장애를 `INCONCLUSIVE + DEPENDENCY_UNAVAILABLE`로 처리합니다.
- ABI 디코더는 현재 두 Registry의 고정 길이 반환 형식을 지원합니다. ABI 변경 시 Reader도 검토해야 합니다.

## 로컬 실행

MVP 재현에는 호스트의 `forge`·`anvil` 설치가 필요하지 않습니다. `make demo-reset`은
Docker Compose의 고정 Foundry `v1.4.4` 컨테이너에서 Anvil과 배포 스크립트를 실행합니다.

`make mvp-test`의 Contract 테스트도 같은 컨테이너를 사용합니다. 호스트 Foundry는 M3/M4가
계약을 직접 개발·디버깅할 때만 선택적으로 필요합니다.

```bash
make demo-reset
```

배포 컨테이너는 M1 seed가 생성한 `build/seed_manifest.json`의 **공개 signer 주소**만 사용합니다.
개발용 Anvil 계정·로그는 공유하지 마세요.

Golden fixture에는 고정 개인키·서명이 없습니다. 실제 증명을 서명한 공개 signer와 등록 주소가
같아야 합니다. 키 시작일은 Golden fixture의 issued_at이며 종료일은 그로부터 365일 뒤입니다.
배포자는 로컬 unlocked 계정을 사용하며 배포 스크립트는 개인키를 읽지 않습니다.

생성 파일:

- `packages/contracts/abi/IssuerRegistry.json`, `IssuerKeyRegistry.json`: Foundry 생성 ABI.
- `packages/contracts/deployments/31337.local.json`: chain ID, 배포 블록, 주소, HEAD SHA, 생성자 인자.
  로컬 manifest는 Git에서 제외됩니다. 미커밋 작업 중 SHA는 작업 내용 전체가 아닌 HEAD를 가리킵니다.

배포 명령은 매번 새 계약을 만듭니다. 체인을 재시작하거나 재배포하면 manifest를 다시 생성하고
Reader도 새 manifest로 생성해야 합니다. Compose 내부의 `anvil` RPC와 chain ID 31337만 지원합니다.

## 테스트와 해석

```bash
uv run pytest -q services/indexer/tests
M4_LIVE_TEST=1 uv run pytest -q services/indexer/tests
```

첫 명령은 단위 테스트이며 live 테스트를 건너뜁니다. 두 번째는 임시 Anvil을 시작해 실제 배포와
M1 ASGI 검증 경로까지 실행합니다. 임시 체인은 종료되므로 그 테스트가 만든 manifest를 운영에 쓰면 안 됩니다.
Proof 저장소는 테스트 대역이며 PostgreSQL·Docker 전체 E2E 테스트는 아닙니다.

이벤트는 `(chain_id, block_number, log_index)`로 중복을 방지합니다. 재시작 시 checkpoint를 읽고,
충돌 시 자동 덮어쓰지 않습니다. 호출자가 안전한 공통 조상을 확인한 뒤 명시적으로 rewind해야 합니다.
현재 구현은 저장 모듈이며 자동 로그 수집 worker는 포함하지 않습니다. MVP에서는 Reader가 체인의
권위 상태를 직접 조회하므로, projection은 이벤트 중복·재시작 안전성을 검증하는 보조 저장 경로입니다.
저장 후 checkpoint를 전진시키는 순서는 호출자가 지켜야 합니다. 별도 worker와 PostgreSQL 기반
projection 운영은 MVP 이후 확장 범위입니다.

## 날짜별 업데이트

### 2026-09-07

- M1 문자열 포트에 맞춘 Reader, 로컬 배포·ABI 추출, 이벤트 저장 모듈을 추가했습니다.
- live 포함 M4 테스트 33개 통과: 정상·변조·중지·폐기·장애와 재시작·reorg 복구를 확인했습니다.
- 이 시점에는 M1 기본 앱 연결과 `demo-reset`을 아직 변경하지 않았습니다.
- [날짜별 상세 기록](updates/2026-09-07.md) · [M1 연결 handoff](../handoffs/m4_chain_ready_2026-09-07.md).

### 2026-09-08 — MVP 통합 완료

- M1 runtime Reader 연결, seed → 배포 순서, `demo-reset` 및 HTTP E2E가 완료되었습니다.
- 고정 Foundry `v1.4.4` Anvil/deployer 컨테이너로 호스트 Foundry 없이 재현합니다.
- `mvp/integration@a1a671b`에서 두 독립 개발환경의 `make demo-reset`, `make mvp-test`가 통과했습니다.

후속 변경은 새 날짜 제목 아래 변경 이유·실행한 검사·남은 작업을 누적합니다.
