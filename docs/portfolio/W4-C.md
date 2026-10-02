# W4 C — 키 교체와 발행 연결

C / @Jordi2801K, W4-C1. 선행 W3 PR #35의 17c24a3, 작업 feat/w4-c-key-rotation.
C 구현·자체 HTTP/DB·실제 PostgreSQL/Anvil 확인 완료. W4-C2/C3는 미구현이며 단계 전체 완료가 아닙니다.

C가 기존 키 등록 orchestration에 명시적인 rotate endpoint/action·감사를 연결하고
현재 유효 키의 확정 후 전환·미래 키/실패의 기존 선택 보존·과거 Proof 정책·늦은 복구를 검사했습니다.
B Writer/Reader/Contract와 W2 signer/Operation을 재사용했습니다. A/B/D 구현이나 리뷰를 대신 수행하지 않았습니다.
Codex가 구현·검사·원인 분석을 보조했습니다.

미래 키가 현재 키를 선택 해제하는 문제를 공유 confirm_target에서 수정했습니다.
과거 UNKNOWN 작업을 늦게 복구해 더 최신 선택이 되돌아가는 문제는 저장된 동일 sender의
nonce 순서로 방지했습니다. 새 계층·dependency·migration 없이 기존 복구 참조를 재사용했습니다.

전체 Python 239 passed / opt-in 5 skipped, W4 합성 검사 3 passed.
실제 PostgreSQL 16·Anvil 1.4.4 HTTP 검사 1 passed: 두 유형 교체/신규 발행/과거 서명,
미래 등록·비인가 실패·늦은 UNKNOWN 복구·키 폐기. Ruff/생성 타입 검사 통과.
macOS/Python 3.13, 합성 계정·임시 DB/chain. 브라우저·성능·작성자 외 리뷰는 미실행/미측정입니다.
구현·검사 SHA/CI는 작업 PR에 남깁니다. 상세 원본은 [키 교체 인계](../api/w4_c_key_rotation_contract.md)입니다.
A 화면 연결·B 리뷰·D 독립 확인과 Proof lifecycle/consume 실제 구현이 남아 있습니다.
