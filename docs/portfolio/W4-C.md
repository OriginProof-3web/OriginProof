# W4 C — 키 교체·Proof 생명주기·1회 사용

C / @Jordi2801K, W4-C1/C2/C3. 선행 W3 PR #35의 17c24a3, 작업 feat/w4-c-key-rotation.
C 구현·자체 HTTP/DB·실제 PostgreSQL/Anvil 확인 완료. W4-C2/C3도 아래 후속 구현·실제 연결 검사를 마쳤으며 단계 전체 완료는 아닙니다.

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
A 화면 연결·B 리뷰·D 독립 확인·공유 단계 병합이 남아 있습니다.


## 2026-10-02 W4-C2/C3 후속 연결

- branch `feat/w4-c-proof-lifecycle`, C 구현·검사 SHA `596f3130e9291f620932161c818389c63e1b53b3`.
- C W4-C1 `85e152c`에서 시작하고 B W3 `92e0e94` / W4 `58e819e`를 준비 branch에 반영하여 연결 검사했습니다. B 원본을 C 기여로 집계하지 않습니다.
- C가 신규 발행 등록 Operation, 기존 W3 원본 등록, 폐기·consume API, 동일 블록 기관/키 snapshot과 현재 chain commitment 대조, UNKNOWN 복구·중복/권한/실패 검사를 구현했습니다.
- 새 저장 계층·dependency·migration을 추가하지 않고 기존 Proof/Operation/감사·B Adapter를 재사용했습니다. DB만으로 소비를 확정하는 방식은 채택하지 않았습니다.
- 미확정 등록을 ACTIVE로 표시하지 않는 경계와 등록 alias의 예약/복구 참조 원자 저장을 확인했습니다. 실제 로컬 DB migration 실행 때 환경변수 접두사 누락으로 실패했고 `API_DATABASE_URL` 적용 후 새 DB migration·check·연결 검사가 통과했습니다.
- 전체 Python **268 passed / opt-in 5 skipped**, Contract **22 passed**, 합성 lifecycle **4 passed**, 실제 PostgreSQL/Anvil HTTP **1 passed**. 실제 로그로 경쟁 consume 1개·반복 폐기 tx 없음·소비 이력 보존을 확인했습니다.
- Codex가 기존 흐름 추적, 구현, 자체 검사, 소비 경계 검토와 문서 작성을 보조했습니다. 작성자 외 팀 리뷰·브라우저·D 독립 재현·성능 측정은 수행하지 않았습니다.
- 상세 API·실패·재현 근거: [W4 lifecycle 인계](../api/w4_c_proof_lifecycle_contract.md). C 담당 구현·자체 실제 연결 범위는 확인 완료이며 공유 phase 병합 뒤 단계 재검증이 필요합니다.
