# W2 / C / Jordi — 개인 개발 기록

- GitHub 계정: @Jordi2801K
- 실제 작업: 2026-09-30 ~ 2026-10-01
- 상태: C 독립 구현·실제 DB/EVM 연결 검증 완료, A/D 연결·리뷰·단계 판정 대기
- 작업 ID: W2-C1/C2/C3
- 시작 기준: phase/W2 e40191f; W1-C3 PR #32와 기존 Operation 준비 branch를 재사용
- 검증 코드 SHA: 작업 PR에 기록. 단계 완료 PR은 미생성.

## 목표와 실제 결과

Operation 예약뿐이던 API에 durable prepared/tx 저장·기존 제출 복구, 기관 승인/중지/
재활성화/폐기, 기관별 보호된 서명기와 공개키 API를 연결했습니다. 결정 저장과 실제
체인 활성화를 분리하고, CONFIRMED만 실제 성공으로 응답합니다.

## 개인 기여·재사용·AI

C가 orchestration·DB/migration·권한·파일 보관·API 생성 계약·단위/실제 연결 검사를
구현했습니다. B의 latest writer(741b8f8), reader, manifest, Contract와 회복 인터페이스를
수정하지 않고 재사용했습니다. A 웹 코드는 수정하지 않았습니다. Codex가 구현·검사·
문서 작성과 원인 분석을 보조했고, 승인 ADR을 기준으로 상태/복구 경계를 맞췄습니다.
B/A/D의 작성자 외 리뷰나 독립 실행을 대신 수행했다고 기록하지 않습니다.

## 판단과 해결

- 전송 전 prepared reference를 commit하고 tx hash 이후 별도 commit해 crash 복구 경계를 둡니다.
- 새 nonce 재전송 없이 기존 tx를 스캔·확인합니다. DB 미확정 nonce도 재시작 예약으로 사용합니다.
- 로컬 P0는 PG advisory lock으로 프로세스 간 변경을 직렬화합니다. 부하 확장은 필요 시 분리합니다.
- 서버 key 파일은 0700/0600·소유자·symlink·유효 scalar 검사와 fsync/challenge로 보호합니다.
- 실제 alembic check에서 W1 기존 timestamp nullable 불일치를 발견해 0004에 backfill/NOT NULL을
  반영하고 downgrade/upgrade/check로 재검증했습니다. backfill은 과거 발생 시각 복원과 다릅니다.
- 합성 SQLite 검사 첫 실행의 detached account 오류는 테스트 session expire 설정을 맞춰 수정했습니다.
- Pydantic enum copy의 출력 경고는 enum 값으로 변환해 해결했습니다.

## 검증 근거

| 검사 | 결과·범위 |
| --- | --- |
| 전체 Python | 171 passed, live opt-in 3 skipped; 기존 외부 라이브러리 deprecation warning 1 |
| Indexer | 60 passed, live opt-in 1 skipped |
| 실제 PostgreSQL+Anvil | 2 passed; 실제 로그인·신청·승인·기관 상태·키 교체/폐기·권한·응답 유실 후 재시작 |
| 합성 Adapter HTTP+SQLite | 7 passed; concurrent request·ID 충돌·DB 마지막 저장 실패·전송 전 저장 실패·nonce 예약·서명기 보호 |
| migration | 0001→0004, 0004 downgrade/upgrade, alembic check 모두 통과 |
| Ruff / 생성 TypeScript | 통과 |
| 재생성 / v1 Golden | byte-for-byte 일치 / v1 변경 없음 |

합성 로컬 환경만 사용했습니다. macOS·Python 3.13·PostgreSQL 16.4·Anvil/Foundry 1.4.4.
기존 demo DB/chain 대신 임시 테스트 DB·분리 Anvil에 실행했습니다. 기능 성능은 미측정입니다.
실행 중인 기존 Docker API에 새 코드를 배포했다고 주장하지 않습니다.

## 다음 작업·사실 확인

인계 원본: docs/api/w2_c_operation_contract.md. A 실제 화면 연결, B 소비자 경계 리뷰,
D 독립 브라우저/다른 환경/RPC 실패 검증, C 리뷰 수정·주차 PR 반영이 남았습니다.
W3 발행/현재 키 재검사와 W4 Proof lifecycle/consume은 다음 단계입니다.
작성자 외 확인은 아직 없습니다. 단계 전체 완료는 선언하지 않습니다.

최종 잠금 보완: PostgreSQL transaction advisory lock으로 취소/예외 시 자동 해제하며,
실제 PG의 교차 연결 배제·취소 후 해제 검사도 통과했습니다.


## 5.1 후속 / V5-W2-C (2026-10-15~16)

- 상태: C 독립 구현·자체 검사 / 실제 Registry·웹·분석기 연결과 작성자 외 리뷰 대기. 단계 전체 완료는 아닙니다.
- 담당: @Jordi2801K의 C 범위에서 Codex가 구현·검사·문서를 수행했습니다. 사용자는 세 작업의 개발 방향을 승인했으며 사람의 코드 작성/리뷰·타인 승인이나 기여 비율은 추정하지 않습니다.
- 구현 근거: `a303ec6`. 최종 누적 검증 코드는 `650e85cd939ac4be493e14b4004daf081f92afa9`이며 후속 문서 커밋과 구분합니다.
- 결과: 합성 명부/데모 코드/지정 내부 승인/키 증명/제안·거래 대조 DB/API를 구현했습니다. #50 nonce cleanup은 별도 4a0e6fb에서 C6 흐름에 반영했습니다.
- 재사용: 기존 C 인증/CSRF/Operation/SQLAlchemy·B Writer/Reader 원본과 공유 서명 모델을 사용했습니다. 정확한 고정 SHA·타 담당 영역과의 경계는 [구현 기록](../handoffs/v5_c_implementation.md)을 확인합니다.
- 판단·문제 해결·실행 명령/환경·정상/거부 결과·실패 수정·잔여 위험·PR 근거는 같은 구현 기록과 [실행 API 인계](../api/v5_c_runtime.md)에 모읍니다. 중복해서 과거 PASS를 신규 실제 연결 성공으로 합산하지 않습니다.
- 최종 검사: 전체 Python 494 PASS/9 opt-in SKIP, 별도 실제 PostgreSQL 1 PASS(체인은 합성), Solidity/Golden 26 PASS, 두 템플릿 hash/타입·재생성·정적 검사 통과. 성능/공개 배포/실제 모델은 미측정입니다.
- 작성자 외 리뷰·본인의 기여 사실 확인: 아직 미확인입니다. 실제 리뷰 후 해당 링크를 추가합니다.
