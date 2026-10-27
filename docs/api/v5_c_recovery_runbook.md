# 5.1 C 신규 지갑 DB/API 복구·독립 검증

작업: V5-W6-C, 선행 [#62](https://github.com/OriginProof-3web/OriginProof/pull/62)와 [현재 C API](v5_c_runtime.md). 기존 v1/v2 복구는 [구버전 runbook](w6_c_recovery_runbook.md)을 유지합니다. 이 문서는 신규 지갑 자료와 실제 API 프로세스 검사 범위를 추가합니다.

사용자 확인: 5.1 이후 B의 신규 Registry/Adapter와 D의 실제 분석기는 아직 준비되지 않았습니다. 이번 작업은 C 독립 복구·검증 도구와 연결 인계이며 실제 B/A/D 통합 완료·단계 완료가 아닙니다.

## 자동 재현

```sh
make test-v5-c-live
```

고정 의존성의 Python·Docker가 필요합니다. `postgres:16.4-alpine` 이미지를 사용하며 매 검사마다 무작위 이름·loopback port·tmpfs DB와 별도 uvicorn 프로세스를 만듭니다. 각 검사는 실제 로그인·CSRF·기관 메일/내부 승인과 SQLAlchemy/asyncpg를 통과합니다. 종료 시 해당 프로세스와 전용 컨테이너만 정리합니다. 기존 Compose·DB·볼륨은 수정하지 않습니다.

`scripts/ci/test_v5_c_recovery.py:process_app`는 명시적 test flag가 있어야 실행되는 합성 fixture입니다. 새 Registry와 분석기 응답만 파일로 제어하며 운영 composition으로 사용하지 않습니다. `WalletRegistry`와 `analysis_processor`의 C 주입 경계는 실제 코드 그대로 사용합니다.

| 검사 | 확인한 경계 |
| --- | --- |
| 백업·복원 | 기존 0006 자료를 둔 채 head migration, 두 문서 버전·원본/서명·선택 보고서/원본·계정/세션을 pg_dump → 별도 빈 DB pg_restore 후 재조회; schema check·구버전 저장 행 보존 |
| 외부 전송 후 강제 종료 | 실제 API SIGKILL, DB의 UNKNOWN/서명/원본 보존, 동일 요청·재조정에서 제출 횟수 1회 유지 |
| 확정 결과 저장 실패 | 전용 PG trigger로 문서 저장 실패를 주입하고 500 뒤 재시작, 같은 거래 재조회로 확정; 원본/서명을 다시 제출하지 않음 |
| 분석 프로세스 중단·삭제 | RUNNING 재시작 실패 처리·미보관 원본 삭제, durable QUEUED 재개, 삭제 후 늦은 작업이 실제 종료된 뒤에도 CANCELLED/보고서 없음 |
| 동시 다음 버전·권한 | 같은 기관의 서로 다른 두 계정이 version 2/같은 업무 nonce를 제출하면 202/409·미확정 Operation 1개; 타 역할 조회·CSRF·본문 상한 거부 |
| RPC 장애·기간 | readiness 503/live 200, AI 위험 결과와 발행 INCONCLUSIVE 독립 집계; 만료 즉시 410, 재시작 정리, 기관 발행 원본은 유지 |

동시 버전은 C의 실제 PostgreSQL 직렬화를 확인합니다. B 컨트랙트의 원자적 전이·실제 receipt/reorg를 확인한 것은 아닙니다. 과거 `make test-w6-c-live`의 실제 Anvil 2개 회귀도 별도로 유지합니다.

같은 검사에서 `POST /v3/verifications`를 서로 다른 request ID로 100회 순차 실행하고, 버전 1의 보호 필드 비교가 모두 VERIFIED인지 확인합니다. `build/v5-c-performance.json`에 p50/p95와 범위를 기록하며 CI 로그에도 출력합니다. 실제 HTTP/PostgreSQL·서명/hash 비교를 포함하지만 Registry 응답은 합성입니다. 실제 체인 지연·모델 지연·다중 사용자 부하 또는 성능 개선율을 뜻하지 않습니다.

## 실제 백업·복원 순서

대상 DB·코드 SHA·lockfile·migration head·신규 Registry chain/address·승인 지갑 공개정보·Adapter 버전을 먼저 기록합니다. 운영 자료에 이 문서의 폐기 가능한 테스트 설정을 복사하지 않습니다.

1. 원본/서명·서명 요청·Operation·요청 claim·분석/보관 동의·검증 세션·계정/세션을 같은 DB snapshot으로 백업합니다. `pg_dump -Fc`를 사용하고 백업 파일/디렉터리를 0600/0700으로 제한합니다. 백업에는 계정 hash·원본이 있으므로 공개 저장소에 넣지 않습니다.
2. 기존 DB와 별개의 **빈 복원 DB**를 만든 뒤 `pg_restore --exit-on-error --no-owner`로 복원합니다. 기존 DB에 `--clean`을 적용하거나 볼륨을 초기화하지 않습니다.
3. 복원에 맞는 코드/lockfile로 Alembic current/check를 확인합니다. 빈 DB 복원에는 dump에 이미 migration 이력이 포함돼 있습니다. 새 적용이 필요하면 백업된 head와 변경을 검토한 뒤 upgrade합니다. downgrade는 신규 열/자료를 제거할 수 있어 복원 대용으로 사용하지 않습니다.
4. 새 DB에만 연결한 단일 API 프로세스를 시작하고 실제 계정 로그인·세션 권한·버전별 원본 bytes/서명·보고서/원본 동의와 만료를 확인합니다. 재시작 중에 만료된 자료는 정책에 따라 접근 거부/정리되므로 물리 데이터만 보고 보존 실패로 판단하지 않습니다.
5. 동일 chain/address와 실제 canonical 상태를 대조합니다. 새 배포를 이전 배포의 복구로 취급하지 않습니다. UNKNOWN은 find_transaction/기존 txHash부터 조회하며 새 nonce로 자동 제출하지 않습니다.

신규 기관 지갑 개인키는 서버에 수집/저장하지 않아 이 DB 백업에 포함되지 않습니다. 신규 키를 서버 서명기 디렉터리에 복사하지 않습니다. 기존 v1/v2 서버 서명기를 함께 운영하는 경우 그 파일 보존은 구버전 runbook의 별도 절차를 따릅니다.

## 서비스 API 밖 검증 도구

```sh
PYTHONPATH=packages/python uv run --package originproof-api python scripts/verify_wallet_document.py \
  --material /path/to/verification-material.json \
  --original /path/to/received-original.json \
  --metadata /path/to/public-issuer-metadata.json \
  --rpc-url "$OP_WALLET_RPC_URL" \
  --chain-id "$OP_WALLET_CHAIN_ID" \
  --registry "$OP_WALLET_REGISTRY_ADDRESS"
```

material은 `/v3/documents/{id}/verification-material?version=...`의 공개 JSON을 미리 확보하거나 기관이 동일 형식으로 전달한 자료입니다. 이후 검증에는 서비스 API를 호출하지 않습니다. 원본/서명은 로컬 파일에서 읽고, 신뢰할 배포 공지에서 별도로 확인한 chain ID·Registry 주소와 직접 RPC를 사용합니다. 검증 대상 파일 안의 domain을 신뢰 주소로 자동 채택하지 않습니다.

`--original` 대신 `--candidate`에 실제 받은 보호 필드 JSON을 주거나 `--id-only`를 선택합니다. 셋 중 하나를 명시합니다. 공개 issuer metadata는 기관 공개자료의 `issuer_id/name/domain` JSON이며 원본 그대로 hash를 대조합니다. metadata가 없으면 해당 검사를 완료하지 못해 INCONCLUSIVE입니다. 새 배포 주소·실제 RPC·공개 metadata 배포는 B/C 인계 후 지정하며 Golden 주소를 운영 주소로 쓰지 않습니다.

도구는 체인 ID·계약 code 존재·고정 block의 문서/latest·기관·과거 키/사고 이력·nonce를 직접 조회하고, 조회 뒤 같은 block hash를 다시 확인합니다. 기존 코어로 원본/보호 hash·기관 서명·상태·경고를 대조합니다. RPC 장애·다른 체인·불완전한 ABI·reorg·증거 누락은 확인 불가이며 합성 성공으로 대체하지 않습니다. 명령은 원문·RPC 인증정보를 오류에 출력하지 않습니다. 로컬 입력 파일은 각 128KiB 상한입니다.

출력은 공통 VerificationResult JSON입니다. 종료 코드 0은 VERIFIED, 1은 TAMPERED, 2는 NOT_REGISTERED/INCONCLUSIVE 또는 잘못된 로컬 입력입니다. **VERIFIED는 비교/발행 근거의 결과입니다. 현재 사용 가능 여부는 document.state와 warnings를 별도로 읽습니다.** ID 단독은 내용 일치를 주장하지 않습니다. 현재 준비 ABI의 직접 RPC 해독은 B의 최종 ABI 리뷰 후 다시 교차 확인합니다.

두 템플릿·변조·metadata 부재/조작·부분 범위·RPC 장애·잘못된 체인/주소·reorg·키 교체/사고·입력 제한은 합성 ABI 응답으로 검사했습니다. 실제 신규 Registry 배포에 대한 V5-F20 완료 근거는 아직 없습니다.

## B/A/D 연결 시 바꿀 지점

C 앱 조립점은 `originproof_api.main.create_app(wallet_chain=..., analysis_processor=...)`입니다. Uvicorn의 `--factory`로 실제 조립 함수를 실행하고 단일 worker로 운영합니다. B/D 구현이 준비되기 전에 fixture factory를 운영 기본값으로 넣지 않습니다.

| 인계 | 실제 구현이 준비되면 확인할 것 |
| --- | --- |
| B → C | WalletRegistry 구현·ABI/manifest/주소, 같은 canonical block과 과거 키 이력, 실제 calldata/receipt/event 대조·재조회; 현재 Protocol의 실제 반환 모델로 연결 |
| D → C | async processor가 공통 AnalysisReport를 반환, 실제 quote/Unicode 위치·refusal/timeout 등 안전한 code, 모델이 발행 verification을 정하지 않음; 입력/모델·전송 예산 결정 뒤 연결 |
| C → A | 현재 앱 OpenAPI·wallet-contract.ts·v3 detail 오류·서명/Operation 재조회·보관 만료, 실제 지갑 서명/거절과 두 보관 선택 UI; [API 인계](v5_c_runtime.md) 사용 |
| 공동 → RC | 같은 코드/lockfile·migration·배포·계정·합성 자료로 전체 수용표, G07 원인/최종 재검사, 다른 PC와 서비스 API 밖 검증·리허설을 기록 |

현재 실제 새 B/D 구현·A 소비/소유자 리뷰가 없으므로 통합 RC·계약 최종 검토·실제 모델 성능·공개 네트워크·W6/W7 전체 완료로 판정하지 않습니다. 기존 새/옛 경로의 검증 근거를 섞지 않습니다.
