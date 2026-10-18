# W5 C — API 권한·상태 연결·P0 기동

**현재(2026-10-03): C1~C3 구현·자체 검증 완료, 리뷰·팀 단계 완료 대기.**

아래 첫 기록은 2026-10-01 당시 상태이며 최신 검증은 마지막 절입니다.

C / @Jordi2801K, W5-C1. 2026-10-01, 선행 W4-C1 `85e152c`,
branch `feat/w5-c-api-security`, 검증 코드 `1da16f0`.
기존 API 독립 구현·검사 완료이며 W4-C2/C3 연결 검사와 W5 단계 전체 완료는 대기입니다.
phase/W5가 아직 없어 자기 선행 W4 PR 위의 준비 branch로 개발했으며 단계 생성 후 재정렬합니다.

기존 서버 세션·역할·기관/객체 권한·Operation·발행 중복 방지를 재사용하고
공통 peer 요청/로그인 제한·Origin·본문 크기/수신 시간 제한·응답 cache 보호를 구현했습니다.
새 dependency·DB migration·B/A/D 구현은 추가하지 않았습니다. Codex가 구현·검사·문서화를 보조했습니다.
API 응답과 운영 한계, 전수 권한표는 [W5 계약](../api/w5_c_security_contract.md)에 기록했습니다.

Python 3.13/macOS, HTTP ASGI·실제 SQLite 저장·합성 Adapter 범위:
전체 Python `python -m pytest -q` 210 passed / opt-in 4 skipped;
W5 `python -m pytest apps/api/tests/test_w5_c_security.py -q` 31 passed.
Ruff 전체·API compileall·git diff --check·OpenAPI 원본 일치 검사 통과.
전체 검사 후 streaming buffer를 bytearray로 바꾼 동일 동작에 대해 W5 31개를 재검사했습니다.
환경은 기존 고정 Python runtime을 재사용했으며 새 lockfile이나 설치를 만들지 않았습니다.

한계: 로컬 단일 worker의 메모리 제한으로 재시작 시 횟수가 초기화되고 프록시 사용자는 예산을 공유합니다.
실제 PostgreSQL/Anvil·브라우저·외부 보안 scan·작성자 외 리뷰는 미실행입니다.
하민님 W4-B2/B3 → W4-C2/C3 후 폐기·consume 권한/입력/재시도 검사를 추가해야 합니다.
W5-C2 Operation/복구 상태 통일과 W5-C3 기동 정리는 이번 범위가 아닙니다.
형준님 오류 화면·인준님 독립 검증 및 PR 리뷰·CI는 별도 확인이 필요합니다.

## 2026-10-03 후속 C1~C3

W4 `8011f7f`와 B W5 `b7a4107` 위에서 C1 보안을 재적용했습니다.
C2는 Operation 다음 행동·기관별 목록·예약/제출 감사 저장·B projection 백그라운드
scanner와 복구 중 응답을 연결했습니다. C3는 migration 0006, 실제 기동 준비 검사,
Docker 경로 정합성·loopback port·재실행 가능한 P0 계정 seed와 `make finals-up`을 추가했습니다.
기존 B projection 및 C W4 orchestration/권한/서명을 재사용했고 새 라이브러리는 없습니다.
공유 runtime/CI/생성기 수정 담당은 C, 리뷰 대상은 B의 projection 경계·A 응답 소비·D 재현입니다.

작성자 검사: Python 3.13.0/macOS, 전체 `283 passed, 4 skipped`; 신규 W5 `4 passed`;
Ruff 통과. 실제 PostgreSQL/Anvil 기동 검증은 W6 통합 실행 결과로 추가 기록합니다.
OpenAPI/TypeScript는 원본에서 생성했습니다. 작성자 외 리뷰·A 실제 UI·D 독립 재현은 미확인입니다.
구현·자체 검사와 단계 전체 완료를 구분합니다. Codex가 구현·검사·인계 작성을 보조했습니다.
상세 계약: [W5 C 통합](../api/w5_c_integration_contract.md).

### 최종 W5 독립 검증

2026-10-03, C W5 코드 `19584cc` (생성물 `147e007`): 기존 FastAPI 0.115.14/pytest 8.4.2
잠금 버전으로 `284 passed, 4 skipped`; W5 후속 상태/권한/파일/불일치 검사 5개 통과.
W4 lifecycle 신규 권한/재시도 검사는 기존 W4 테스트와 함께 재실행했습니다.
DB 확인 상태와 실제 canonical Reader 비교를 `/v2/issuer/proofs/{proof_id}/reconciliation`으로 제공합니다.
배포 불일치·RPC 오류에서는 일치를 단정하지 않습니다. 기존 PR #37을 C1~C3 전체로 갱신합니다.
공유 lock 보안 패치와 실제 복구/Compose 결과는 W6 C 기록의 검증 SHA에서 확인합니다.
W5 작성자 외 리뷰·A 실제 전체 UI 연결·D 독립 재현은 미확인입니다.


## 5.1 후속 / V5-W5-C (2026-10-15~16)

- 상태: C 독립 구현·자체 검사 / 실제 Registry·웹·분석기 연결과 작성자 외 리뷰 대기. 단계 전체 완료는 아닙니다.
- 담당: @Jordi2801K의 C 범위에서 Codex가 구현·검사·문서를 수행했습니다. 사용자는 세 작업의 개발 방향을 승인했으며 사람의 코드 작성/리뷰·타인 승인이나 기여 비율은 추정하지 않습니다.
- 구현 근거: `30002bc`. 최종 누적 검증 코드는 `650e85cd939ac4be493e14b4004daf081f92afa9`이며 후속 문서 커밋과 구분합니다.
- 결과: 소유자 분석 작업·멱등/timeout·네 보관 조합·삭제/재시작·grounding·C 검증 사본 집계를 구현했습니다.
- 재사용: 기존 C 인증/CSRF/Operation/SQLAlchemy·B Writer/Reader 원본과 공유 서명 모델을 사용했습니다. 정확한 고정 SHA·타 담당 영역과의 경계는 [구현 기록](../handoffs/v5_c_implementation.md)을 확인합니다.
- 판단·문제 해결·실행 명령/환경·정상/거부 결과·실패 수정·잔여 위험·PR 근거는 같은 구현 기록과 [실행 API 인계](../api/v5_c_runtime.md)에 모읍니다. 중복해서 과거 PASS를 신규 실제 연결 성공으로 합산하지 않습니다.
- 최종 검사: 전체 Python 494 PASS/9 opt-in SKIP, 별도 실제 PostgreSQL 1 PASS(체인은 합성), Solidity/Golden 26 PASS, 두 템플릿 hash/타입·재생성·정적 검사 통과. 성능/공개 배포/실제 모델은 미측정입니다.
- 작성자 외 리뷰·본인의 기여 사실 확인: 아직 미확인입니다. 실제 리뷰 후 해당 링크를 추가합니다.

5.1 원격 공유: [#62](https://github.com/OriginProof-3web/OriginProof/pull/62) (Draft). 사용자 승인 후 자기 브랜치에 push하고 생성했습니다. 실제 원격 CI/작성자 외 리뷰·단계 완료는 별도입니다.

## 2026-10-18 V5-W5-C 셀프 리뷰 후속

W3/W4의 만료·request ID·합성 상태 보완을 반영했습니다. 실제 cleanup 함수를 31일 뒤
시각으로 실행한 뒤 철회 서명은 남고 Operation·그에 연결된 재시도 ID 기록은 정리되는지,
기존/새 ID의 서명 재제출과 직접 거래 접수가 모두 410인지 검사했습니다. API wallet 및
분석·보관 검사 77 PASS, Ruff·diff 통과입니다. SQLite/ASGI·합성 Registry 검사이며
운영 배포·유료 모델·D 독립 검증을 실행한 것은 아닙니다.
