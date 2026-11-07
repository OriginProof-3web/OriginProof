# D 독립 #85 PostgreSQL seed·설정 재현

2026-10-21, AI(Codex)가 PR #85 `ea49318989f3a17895cf973065672936d701ce48`을 `git archive`로 임시 경로에 읽기 전용 원본으로 내보내 실행했습니다. C 브랜치 checkout/commit/merge, 데모 DB 변경/reset은 하지 않았습니다. 저장소의 패키지 제약·lockfile을 변경하지 않고 Dockerfile의 잠금 환경을 사용했습니다.

## 실제 환경과 격리

Docker 29.7.2 / Compose 5.5.1, PostgreSQL16.4-alpine / Redis7.4.1-alpine / 고정 Foundry1.4.4 이미지입니다. 임시 프로젝트 `originproof-d85-20261021`, 사설 network·새 postgres-data/issuer-signers volume만 사용했고 호스트 publish ports를 제거했습니다. 원본 compose를 유지하고 임시 override만 사용했습니다. provider mock, 입력/relay false, 유료 호출0입니다. 승인자 주소는 설정 파싱 확인용 합성 주소이며 Registry 배포·지갑 연결로 취급하지 않습니다. 비밀번호/secret은 로그·Git에 남기지 않았습니다.

## 실행 결과

| 실제 검사 | 결과 |
| --- | --- |
| `make mvp-up` → `make db-upgrade` | 6개 서비스 기동, Alembic0001~0009 적용 |
| 기존 DB 시나리오 | 새 격리 DB에 기존 P0 합성 계정5개를 만든 뒤 v5 seed 두 번: 총12개(기존5+신규7) |
| 기존 계정 보존·반복 멱등성 | account ID/username/role/issuer/password_hash가 그대로 유지됨; 두 seed의 설정 mapping 동일 |
| `.env` 반영·`make api-reload` | API container ID 교체, 내부 승인자 mapping·합성 승인 주소가 컨테이너 Settings에 일치; 기존 행 유지 |
| 새 DB 시나리오 | 같은 격리 PostgreSQL에 빈 `d85_fresh` 생성, `.env` DB만 전환 후 mvp-up→db-upgrade→v5-wallet-seed 두 번: 7개/동일 행 |
| 새 DB 설정 재기동 | 새 계정 mapping으로 .env 갱신→api-reload→컨테이너 Settings 일치 |
| 실제 역할 충돌 거부 | 격리 DB의 한 합성 계정 role을 다르게 한 뒤 seed 실패 확인; 부분 변경 없음, 원래 role 복원 |
| credential 권한 | test-accounts.json 0600 |
| 실제 HTTP health | live200, **ready503** |
| 정리 | 소유 Compose 컨테이너/network/volume만 제거, 잔존 container0 |

`make`에는 `COMPOSE='docker compose --project-name originproof-d85-20261021 -f docker-compose.yml -f d85-isolation.yml'`을 전달했습니다. override는 postgres/api/analyzer/web의 `ports: !reset []`만 설정합니다. 기존 DB는 현재 데모 DB를 재사용한 것이 아니라 P0 자료가 있는 폐기 가능한 격리 DB입니다. 따라서 실제 운영/팀 DB migration 호환성 전체를 검증한 것은 아닙니다.

원본 실행 로그는 `/private/tmp/originproof-d85-{mvp-up,db-upgrade,live-check,finish}.log`, 요약 JSON은 `/private/tmp/originproof-d85-live-result.json`입니다. 임시 파일은 영구 보관을 보장하지 않으므로 위 결과를 이 문서에 기록했습니다.

## 한계·C에게 확인할 내용

시드/설정 재생성 검사는 통과했지만 **앱 전체 readiness·Registry 연결 성공은 아닙니다.** 새 v5 계정7개에는 readiness.py가 요구하는 기존 recipient·v1/v2 issuer 계정이 없고, Registry/배포 manifest도 연결하지 않았습니다. 실제 ready503을 정상 연결 성공으로 기록하지 않습니다. C가 runbook에 v5 seed-only 기동의 예상 health 상태, P0 계정·배포/Registry 연결의 선행 명령과 정상 완료 기준을 명시해야 합니다. B Registry가 없는 /v3 체인 기능503은 원래 인계된 한계입니다.

기관/실제 승인 지갑·OpenAI·OCR·G07·브라우저 E2E는 실행하지 않았습니다. 담당자 본인 확인·작성자 외 승인도 별도입니다.
