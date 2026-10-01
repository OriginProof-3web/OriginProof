# W6 C — 기존 API·세션·서명기 보안

C / @Jordi2801K, W6-C2. 2026-10-01, 선행 W5-C1 `b6d7d67`,
branch `feat/w6-c-security-checks`, 검증 코드 `9100ca9`.
기존 API 독립 구현·검사 완료이며 신규 W4-C2/C3 연결 검사·단계 전체 완료는 대기입니다.
phase/W6가 아직 없어 자기 W5 준비 branch 위에 작업을 쌓았으며 단계 생성 후 재정렬합니다.

기존 세션·PBKDF2·파일 서명기를 재사용해 cookie 형식·실제 HTTPS Secure,
비ASCII CSRF 거부·미등록 계정 dummy 계산·SQL 오류 bind 숨김·directory descriptor 파일 접근을 보완했습니다.
0700/0600·UID·symlink/hard link/FIFO·challenge·directory 교체 경합을 검사했습니다.
새 dependency·migration·Contract/Adapter 변경은 없습니다. Codex가 구현·검사·문서화를 보조했습니다.

Python 3.13/macOS, 실제 HTTP ASGI·SQLite·임시 파일·합성 Adapter 범위:
전체 `python -m pytest -q` 228 passed / opt-in 4 skipped.
W5 31개·W6 18개 보안 사례를 포함하며 Ruff 전체·compileall·diff·OpenAPI 원본 일치 검사 통과.
최종 코드 변경 후 전체 검사를 수행했고 SQL 오류 문자열의 비밀값 숨김을 확인했습니다.
신규 성능 수치나 완전한 로그인 timing 동일성은 측정/주장하지 않습니다.

검사 범위·명령·잔여 W4~W7 C 작업은 [보안·잔여 개발 보고](../api/w6_c_security_report.md)에 기록했습니다.
실제 PostgreSQL/Anvil·브라우저·다른 환경·외부 보안 scan·작성자 외 리뷰는 미실행입니다.
폐기/consume 신규 API 검사는 W4-C2/C3 이후, Contract 직접 호출 우회 검사는 하민님 W6-B3와
인준님 독립 확인이 필요합니다. W6-C1/C3은 이번 범위가 아닙니다.
메모리 요청 제한은 로컬 단일 worker 전용이며 재시작 초기화·프록시 예산 공유 한계가 남습니다.
