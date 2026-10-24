# Wallet journal position migration

AI(Codex)가 여하민님 요청으로 준비했습니다. B 소유 journal 전용 SQL이며 C API Alembic 체계와 별개입니다. `WalletProjection.initialize()`의 `create_all`은 기존 열 타입을 변경하지 않습니다.

- 신규 DB: 현재 metadata가 BIGINT로 생성합니다.
- 기존 PostgreSQL: indexer writer를 멈추고 백업·대상 DB·schema를 확인한 뒤 운영자가 `001_wallet_positions_bigint.sql`을 적용합니다. 기존 행·PK·checkpoint·deployment를 삭제하거나 다시 만들지 않습니다.
- 예시: `psql --set=ON_ERROR_STOP=1 --file=services/indexer/migrations/001_wallet_positions_bigint.sql` (연결 설정은 운영자의 기존 안전한 환경을 사용하고 Git/로그에 기록하지 않습니다). 오류 또는 lock timeout이면 해당 세션을 종료해 rollback하고 원인을 해결합니다. 배포 중 자동 실행하지 않습니다.
- 전후 확인: 두 테이블의 행 수·PK·checkpoint 값과 `information_schema.columns`의 세 열 타입을 비교합니다. 성공 후 `block_number` 두 곳과 `log_index`가 bigint인지 확인하고 writer를 재개합니다. INTEGER로 자동 downgrade하지 않습니다(범위 초과 데이터 손실 방지).
- SQLite는 INTEGER 자체가 signed 64-bit이므로 ALTER가 필요 없습니다. 실제 PostgreSQL 적용은 Docker daemon 부재·psql 미설치로 **미실행**입니다. 새 패키지 설치·운영 DB 변경은 하지 않았습니다. 테스트는 PostgreSQL DDL 컴파일과 SQLite 2^31 초과 위치 보존이며 실제 migration 성공 증거를 대신하지 않습니다.
