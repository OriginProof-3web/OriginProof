# M1 handoff — 2026-09-07 M4 chain-ready

최초 기준은 `3bbaba0`이며, 최신 `mvp/integration`의 `f029e76`을 병합해 재검증했습니다.
작업 브랜치는 `mvp/chain-ready`이고 계약 코어 변경은 없습니다.
검증 결과는 [날짜별 기록](../blockchain/updates/2026-09-07.md)을 참고합니다.

## 연결 순서

1. M1 seed를 실행해 증명과 `build/seed_manifest.json`의 공개 signer를 준비합니다.
2. chain ID 31337 로컬 RPC를 실행하고 해당 signer로 `deploy_local.py`를 실행합니다.
3. `packages/contracts/deployments/31337.local.json`을 API 프로세스가 읽을 수 있도록 배치합니다.
4. `JsonRpcBlockchainReader(rpc_url, manifest_path, issuer_ids=["iss_origin_mock_bank"])`를 생성합니다.
5. 기존 `SqlAlchemyProofRepository`와 Reader를 `VerificationService`에 주입하고
   `create_app(verification_service=...)`로 연결합니다. M1 기본 앱의 `UnavailableBlockchainReader`는 아직 유지돼 있습니다.
6. seed 증명의 정확한 Candidate로 API를 호출한 뒤 전체 E2E를 실행합니다.

RPC 형식은 `http://127.0.0.1:8545`(호스트 실행 예시), chain ID는 31337입니다.
컨테이너 내부에서는 실제 서비스 DNS 주소를 Reader에 제공해야 합니다. 배포 CLI는 loopback만 허용합니다.
ABI는 `packages/contracts/abi/{IssuerRegistry,IssuerKeyRegistry}.json`에 생성됩니다.
Reader 생성 시 잘못된 manifest도 `DependencyUnavailableError`가 발생하므로 시작 시 구성 실패 정책을 정해야 합니다.

## M1 소유 변경 요청

- **PR #8 CI blocker — `Makefile`의 `generate` 대상:** 깨끗한 GitHub Actions 환경에서
  `make generate`가 `ModuleNotFoundError: No module named 'Crypto'`로 실패합니다. 현재
  `$(UV) run python scripts/generate_schemas.py`는 workspace member 의존성을 설치하지 않기
  때문입니다. 두 생성 명령을 `$(UV) run --package originproof-core python ...`로 실행하거나,
  동등하게 core 의존성을 포함하도록 수정해주세요. 로컬에서 해당 `--package` 명령으로 schema와
  Golden fixture를 생성한 뒤 생성 파일 diff가 없음을 확인했습니다. 깨끗한 clone에서
  `make generate && git diff --exit-code -- packages/schemas/generated fixtures/golden`을
  재검증해야 합니다.
- `demo-reset`의 seed 이후 signer 기반 배포를 연결하고 RPC 접근·manifest 전달 경로를 정해주세요.
  현재 Compose의 anvil 이름 서비스와 실제 EVM 이미지·포트 구성을 확인해야 합니다.
- `httpx`는 현재 루트 dev 의존성입니다. dev 그룹 없는 API 배포를 위해 API 런타임 의존성에 선언해야 합니다.
- 루트 테스트 대상은 indexer 테스트를 포함하지 않습니다. `uv run pytest -q services/indexer/tests`와
  Foundry 가능한 환경의 `M4_LIVE_TEST=1` 검사를 CI에 추가해주세요.
- indexer는 동기 SQLAlchemy Engine을 받는 저장 모듈입니다. PostgreSQL 드라이버·마이그레이션·worker
  구성은 별도 연결이 필요합니다. 조회 권위는 체인이며 이 저장소를 최종 판정 근거로 사용하지 않습니다.
- 재시작 시 checkpoint부터 안전하게 replay하고, 블록 로그 저장 완료 후 checkpoint를 갱신해주세요.
  reorg 공통 조상 탐지는 worker 책임이며 rewind API는 제공된 조상의 실제 체인 소속을 검증하지 않습니다.

## 검증 범위와 제한

M4 33개 테스트에는 실제 임시 Anvil 배포·ABI 생성·M1 ASGI 경로의 정상/변조/중지/폐기/RPC 종료가
포함됩니다. 최신 통합 기준 `make mvp-test`, `make lint`, `make typecheck`, `make bootstrap-check`도
통과했습니다. Proof 저장소는 대역이며 SQLAlchemy 저장 검사는 SQLite 파일을 사용했습니다.
PostgreSQL 및 Docker 전체 E2E, 다중 개발 환경 재현은 아직 수행하지 않았습니다.
Golden fixture는 고정 signer가 없는 digest fixture이므로 실제 seed의 공개 signer를 반드시 사용해야 합니다.
개인키·RPC token·증명 원문은 manifest에 넣지 않습니다.
