# W6 C — 프로세스·DB 복구와 보안 검증

담당 C / @Jordi2801K. W5 통합과 B Writer `65b041e`를 연결합니다.
보존 복구는 기존 Operation/Proof/계정/서명기와 해당 체인 배포를 함께 유지하는 경로입니다.
`make reset`/`make demo-reset`은 DB 볼륨 삭제이며 이 절차에 사용하지 않습니다.

## Operation 복구

1. UNKNOWN/SUBMITTED 응답은 성공·확정 실패가 아닙니다. 같은 operation_id를 조회합니다.
2. 원래 요청자 또는 운영자가 기존 세션과 CSRF로
   `POST /v1/operations/{operation_id}/recover`를 호출합니다. 저장된 sender/nonce/input/tx hash를 재사용합니다.
3. SUBMISSION_UNKNOWN은 노드 응답 유실로 거래가 이미 채굴됐을 수 있습니다.
   TRANSACTION_NOT_MATCHED는 저장된 hash가 원래 거래와 다르므로 UNKNOWN으로 유지합니다.
   두 경우 모두 새 request ID·nonce를 자동 할당하지 않습니다.
4. 실제 canonical 실패 receipt만 FAILED입니다. 과거 Writer가 제출 RPC 오류만으로 저장한
   FAILED/CHAIN_REVERTED 행은 자동 재시도하지 않고 운영자가 원래 거래 참조를 감사합니다.
5. 기존 DB의 deployment_id와 manifest가 다르면 DEPLOYMENT_CHANGED(409)입니다.
   같은 chain ID라도 재배포는 새 환경입니다. 이전 Proof를 현재 사용 가능으로 복사하지 않습니다.

실제 검사는 저장된 hash 없는 제출 응답 유실 → API 재시작 → 원래 거래 조회,
무관한 성공 hash의 거부, consume 제출 뒤 API SIGKILL → SUBMITTED 행의 동일 hash/참조 복구,
동시 발행/consume과 RPC 보류를 재현합니다. JSON-RPC relay는 실제 Anvil 요청을 전달한 후 응답을
교란합니다. 외부 네트워크 장애나 실제 노드의 모든 오류를 재현한 것으로 주장하지 않습니다.

## 보존 백업 (합성 P0, 쓰기 중단)

먼저 대상 Compose project를 확인하고 모든 외부 DB/체인 writer도 중단합니다.
기본 `originproof` 이외 프로젝트에는 모든 명령에 같은 `--project-name`을 넣습니다.
아래 명령은 고유한 새 백업 디렉터리에만 기록합니다. 백업에는 세션·비밀번호 hash·개인키가 있으므로
공유·Git·CI artifact에 올리지 않습니다. 실패하면 덤프를 유효한 백업으로 표시하지 않습니다.

```sh
umask 077
mkdir -p build/backups
OP_BACKUP_DIR="build/backups/$(date +%Y%m%d-%H%M%S)"
mkdir -m 700 "$OP_BACKUP_DIR"
docker compose stop api
docker compose exec -T postgres pg_dump -U originproof -Fc originproof > "$OP_BACKUP_DIR/database.dump"
docker compose run --rm --no-deps -T --entrypoint tar api -C /workspace/build/secrets -cf - issuer-signers > "$OP_BACKUP_DIR/issuer-signers.tar"
cp packages/contracts/deployments/31337.local.json "$OP_BACKUP_DIR/manifest.json"
git rev-parse HEAD > "$OP_BACKUP_DIR/source-sha.txt"
cp uv.lock "$OP_BACKUP_DIR/uv.lock"
docker compose up -d api
```

체인 상태는 별도로 B의 [체인 복구 기록](../blockchain/w6_fault_recovery_security.md)을 따릅니다.
Anvil의 빈 재시작을 기존 체인 복원으로 취급하지 않습니다. 현재 manifest의 genesis/deployment
block hash·주소·역할과 실제 체인이 맞아야 보존 DB를 사용합니다. API를 중단하지 않은 백업이나
덤프 중 외부 체인 변경은 일관된 복구 지점으로 인정하지 않습니다.

## 새 DB에서 복원 검증

기존 DB를 덮어쓰지 않고, 없는 이름으로 새 DB를 만듭니다. 아래 createdb가 실패하면 중단합니다.
`pg_restore --clean`, 볼륨 삭제 또는 기존 DB drop은 보존 복구가 아닙니다.

```sh
docker compose exec -T postgres createdb -U originproof originproof_restore_check
docker compose exec -T postgres pg_restore --exit-on-error --no-owner -U originproof -d originproof_restore_check < "$OP_BACKUP_DIR/database.dump"
```

서명기는 새 빈 디렉터리에만 복원하고 디렉터리 0700·일반 파일 0600·실행 UID 소유권을 유지합니다.
신뢰할 수 없는 tar·절대경로·상위경로·symlink/hardlink를 복원하지 않습니다. 실제 검사에서는
새 임시 디렉터리로 copytree하고 `verify_signer(secret_ref, signer)`로 DB의 공개 signer와 대조했습니다.
검증용 API_DATABASE_URL/ API_SIGNER_DIRECTORY를 새 DB·새 디렉터리로 지정해 migration head와
readiness를 확인합니다. 정상 Proof 서명/ACTIVE, 동일 요청 ID의 기존 Proof, 세션·기관 연결을 검사합니다.
재실행 seed는 기존 계정 password/role/issuer를 바꾸지 않습니다.

허용한 migration 복귀 범위는 **0006 → 0005 → head**입니다. 0006의 downgrade는 재구축할 수 있는
projection 테이블만 제거하며 API 계정/Proof/Operation/키 참조는 보존합니다. API를 중단한 상태에서
수행하고, 0005 이전으로의 downgrade는 이 검증 범위가 아닙니다. 구 버전 API와 새 DB의 완전한
양방향 호환을 주장하지 않습니다. lockfile·실행 SHA를 같이 보존해 동일 버전으로 복귀합니다.

## 재현·검사 명령

- `make test-w6-c-live`: Docker PostgreSQL 16.4 + host Foundry 1.4.4(고정 라이브러리 필요),
  무작위 loopback 포트·고유 이름·tmpfs DB·별도 API 프로세스. 테스트가 생성한 자원만 정리합니다.
- `make security`: uv 0.8.17에는 audit 명령이 없으므로 전체 workspace lock export를
  PyPA pip-audit 2.10.1로 조회합니다. 실시간 advisory 조회 실패는 통과로 처리하지 않습니다.
- CI `c-recovery`: 고정 의존성 설치·위 보안 감사·실제 프로세스/복원 검사입니다.
- 기존 메모리 요청 제한은 단일 worker·peer 단위이며 재시작 시 초기화됩니다. 확장 시 공유 카운터가
  필요하지만 P0에 Redis 기반 새 제한기를 추가하지 않았습니다.

## 의존성 변경 근거

FastAPI 0.142.2 / Starlette 1.7.0, pytest 9.1.1 / pytest-asyncio 1.4.0으로
기존 버전 제한을 갱신했습니다. API와 analyzer의 FastAPI 제한을 함께 맞추고 lockfile을 재생성했습니다.
새 기능 프레임워크를 도입하지 않았으며 추가 annotated-doc/opentelemetry-api는 FastAPI 전이 의존성입니다.
공유 lock/CI 담당은 C; analyzer 소유자 D의 호환 리뷰와 A/B 경계 리뷰는 별도입니다.

근거: [FastAPI release notes](https://fastapi.tiangolo.com/release-notes/#01330),
[Starlette advisory](https://github.com/Kludex/starlette/security/advisories/GHSA-jp82-jpqv-5vv3),
[pytest advisory](https://github.com/advisories/GHSA-6w46-j5rx-g56g),
[PyPA audit](https://github.com/pypa/pip-audit).
알려진 Python 취약점 0건은 검사 시점·잠금 패키지 범위의 결과이며 전체 시스템 무결점 증거가 아닙니다.
브라우저 전체 동선·다른 노트북·외부 배포·독립 리뷰는 A/D 후속 검증입니다.
