# W5 C — 기존 API 권한·요청 보호

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
