# W5 C — 상태·복구 응답과 로컬 P0 기동

C / @Jordi2801K. 기준 integration `3295a71`에 병합된 W4 `8011f7f`,
B W5 `b7a4107`을 연결하고 기존 C1 보안 변경 `1da16f0`을 재사용했습니다.
B의 Adapter/ProjectionStore 코드는 수정하지 않았습니다. A/B/D 작성자 외 리뷰는 별도입니다.

## 상태 계약 (기존 필드 유지, 추가 필드·조회)

- OperationView에 `recovery_required`와 `next_action`을 추가합니다.
  UNKNOWN/SUBMITTED는 `RECOVER_SAME_OPERATION`; PENDING_SUBMISSION은
  `RETRY_SAME_REQUEST`; CONFIRMED/FAILED는 `NONE`입니다. FAILED 작업을 자동 재전송하지 않습니다.
- `GET /v1/operations?target_id=...&status=UNKNOWN&limit=100&offset=0`:
  운영자는 전체, 발행자는 자기 작업 또는 자기 기관, 수신자는 자기 작업만 조회합니다.
  개별 조회의 기존 권한을 유지합니다. 서버 전용 input/recovery reference는 응답에 없습니다.
- `GET /v1/audit-events?target_id=...&limit=100&offset=0`: 운영자/자기 기관만 허용합니다.
  기본 100, 최대 200. 기존 배열 응답 유지. 예약과 SUBMITTED 저장에 감사 이벤트를 같은
  DB transaction으로 추가해 주체·대상·전후 상태·시각을 추적합니다.
- `GET /v1/chain-sync`: 운영자/발행자용 역사 projection 진행 상태입니다.
  STARTING / SYNCED / CATCHING_UP / WAITING_CONFIRMATIONS / RECOVERING / STALE / DISABLED.
  `authority=HISTORICAL_EVENTS_ONLY`를 명시합니다. 현 사용 가능성은 기존 v2 Reader 검증입니다.
  projection 성공을 Proof 성공으로 바꾸지 않습니다. 지연/오류는 원문 없이 보류 상태로 제공합니다.
- 백그라운드 scanner는 B의 `sync_confirmed(confirmations=2)` 및 atomic apply/reorg를 그대로
  사용합니다. PostgreSQL 별도 advisory lock, 전용 worker thread, poll당 200블록 상한입니다.
  중단 시 진행 중 DB/RPC 검사를 종료한 후 thread를 정리합니다. 대형 재색인은 반복 poll합니다.
  공통 조상이 없거나 tip 후퇴로 B가 오류를 내면 RECOVERING으로 유지하고 임의 DB reset을 하지 않습니다.

OpenAPI와 TypeScript는 원본 Pydantic serialization schema에서 재생성했습니다.
A는 UNKNOWN에서 같은 Operation recover 버튼을 사용하고 새 request ID로 작업을 만들지 않습니다.
새 선택 필드와 조회는 기존 v1/v2 서명과 API 필드를 바꾸지 않습니다.

## 로컬 기동

1. `.env.example`을 `.env`로 복사합니다. 본선 두 기관 ID는 legacy 카드 seed와 분리합니다.
   기존 .env에도 API_FINALS_PAYMENT_ISSUER_ID/ API_FINALS_DOCUMENT_ISSUER_ID를 반영합니다. Compose project는 기본 originproof입니다.
2. 기존 build/seed/deploy 명령을 재사용하는 `make finals-up`을 실행합니다.
   DB migration head, 기존 카드 회귀 seed/체인 배포, API 재기동, P0 계정 seed, readiness 순서입니다.
   `make demo-reset`/`make reset`은 데이터 삭제이므로 보존 재시작에 사용하지 않습니다.
3. `make finals-seed`는 두 합성 기관과 operator/bank/office/recipient/recipient_other를 준비합니다.
   기존 계정 비밀번호·승인·Proof는 유지하며 기존 username의 역할/기관 충돌은 실패시킵니다.
   새 로컬 공통 테스트 비밀번호는 signer 디렉터리의 `test-accounts.json`(0600)에만 보관합니다.
   로컬에서 파일을 확인하거나 `docker compose exec api`에서 읽어 로그인합니다. Git/로그/argv에 출력하지 않습니다.
4. 웹 http://127.0.0.1:3000 에서 두 기관의 신규 신청·운영자 승인·활성화·키 등록 후 발행합니다.
   온보딩을 seed가 대신 완료하지 않습니다. A의 W4 UI는 별도 연결 대상입니다.

`/health/live`는 프로세스 생존, `/health/ready`는 DB head·필수 계정/기관·보호된 writable
signer 디렉터리·실제 chain identity/code·projection 준비를 검사합니다. 미준비는 503 RUNTIME_NOT_READY.
Compose manifest/서명기 mount는 Dockerfile의 실제 WORKDIR `/workspace`와 일치시켰습니다.
API/Postgres/analyzer 공개 port는 loopback으로 제한합니다. 새 chain 자동 재배포와 보존 복구는 W6 계약입니다.
