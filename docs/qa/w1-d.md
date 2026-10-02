# W1-D1/D2 — 현재 독립 QA 상태

- 담당: D / 여인준님 (`@yijun0330`). 기준: 계획서 v3.0 §15.2·§16, ADR 0001.
- 공식 phase: `0308cb24f9e4aed157095131e2552243767d16eb`; 수정·검증 후보: `f1de961d8f94405d5a143cd853421eee8878b4f1`.
- 현재 작업: `docs/w1-completion-evidence` → `phase/W1`, 단계 승격 초안 [PR #39](https://github.com/OriginProof-3web/OriginProof/pull/39).
- 원래 로컬 `mvp/ai`의 미커밋·미추적 자료는 보존하고 기존 임시 worktree를 사용했습니다.
- 수정: D 합성 입력/검사·QA/기여 기록, 사용자 지정 검사 runner/웹 live E2E 및 검사에서 발견한 승인 화면 HTML 오류.
- 선행: A #27, B #26, C #23/#32, D #30이 공식 phase에 포함됐습니다.
- 독립 W1 실제 연결: role/CSRF/login/logout/만료, 신청·승인·반려·재조회, 자기 승인/타 기관 격리 및 접근성 검사 통과.
- D 자료는 fixture 1.1.0에서 현재 C v2 필드 계약과 대응했습니다. 28개 전체 본선 시나리오의 runtime 실행 상태는 NOT_RUN으로 유지합니다.
- 현재 실제 결과: [최종 QA](w1-final-verification.md), [환경](w1-final-environment.json), [사례표](w1-acceptance-matrix.md).
- 역사 기록: [이전 실행 결과](w1-results.md). 임시 통합 SHA 성공을 공식 phase 완료 증거로 재사용하지 않습니다.
- 리뷰/범위/기여: [기록](w1-scope-and-reviews.md), [W1-D](../portfolio/W1-D.md).
- 새 후보의 phase 반영·작성자 외 최종 승인과 A/B/C 본인 확인은 대기입니다. v2 실제 발행/키 관리·consume은 후속 단계 범위입니다.
