# W1 / D / 여인준 — 독립 QA 기록

- GitHub 계정: `@yijun0330`, 사용자가 지정한 D 역할.
- 작업일: 2026-10-01~2026-10-02. W1은 개발 단계입니다.
- 작업 ID: W1-D1/D2. 상태: 실제 연결·계약 소비 검사 완료, 새 변경 리뷰와 단계 최종 확인 대기.
- 기존 PR: [#30](https://github.com/OriginProof-3web/OriginProof/pull/30), C가 독립 QA 범위를 승인했습니다.
- 공식 phase 기준: `0308cb24f9e4aed157095131e2552243767d16eb`; 수정·검증 후보: `f1de961d8f94405d5a143cd853421eee8878b4f1`.
- 단계 승격 초안: [#39](https://github.com/OriginProof-3web/OriginProof/pull/39).

| 작업 | 실제 D 수행 | 재사용·협업 |
| --- | --- | --- |
| D1 | F01~F15 수용표, v1 카드 정상/금액 변조 회귀, 공식 W1 실제 role/CSRF/신청/승인·반려/세션·DB 독립 QA | A 웹, C API/모델, B 기존 Registry·Foundry 컨테이너 |
| D2 | 두 기관/두 유형 합성 입력 28개, C v2 필드 계약 대응, nonce 불일치 수정과 검사 보강 | C 원본 모델·생성 Schema/Golden을 재사용; D unsigned 입력을 signed Golden으로 간주하지 않음 |
| 계약 검토 | 생성물 byte 재현, Foundry signing digest/ID hash 교차 확인, 생성 TS 소비 컴파일, PR #23/#32 사후 기술 승인 리뷰 | user가 1~5번 검토·기록 보완을 지시; Codex 수행임을 리뷰에 명시 |

공식 W1의 승인 화면에서 axe serious 오류를 발견했습니다. `<dl>` 밖으로 안내 문구를 옮기는 최소 수정 후 실제 연결과 접근성 검사를 통과했습니다. 새 테스트의 Next route announcer 선택 충돌도 수정하고 다시 실행했습니다. 다른 담당자의 기능을 구현한 것이 아니라 사용자 요청 범위의 검사·발견 결함 수정입니다.

[최종 QA 결과·환경·재현](../qa/w1-final-verification.md), [전체 본선 사례표](../qa/w1-acceptance-matrix.md), [단계 범위·리뷰](../qa/w1-scope-and-reviews.md), [합성 입력](../../fixtures/finals/README.md)을 참조합니다. 새 후보에서 전체 Python 220 passed/1 opt-in skipped, 실제 Chromium 1 passed 및 DB 검사 PASS, 기존 mock browser 4 passed, component 6개, Foundry Contract 10개가 통과했습니다.

원래 미커밋·미추적 저장소를 보존하고 기존 임시 worktree에서 작업했습니다. 임시 DB·API·웹만 새 포트로 사용한 뒤 제거했습니다. Golden과 개인 `.env`, 기존 Compose DB는 변경하지 않았습니다.

AI 활용: 사용자가 D 역할과 W1 완료 준비 1~5번을 지정했고 Codex가 검사·수정·자료 작성·코드 리뷰를 수행했습니다. A/B/C 본인의 판단이나 사람의 최종 승인으로 표시하지 않습니다. 성능·기여 비율은 추정하지 않습니다.

기존 작성자 외 승인: PR #30의 C 리뷰. 이번 새 후보 PR의 외부 승인 및 소유자 기여 확인은 대기입니다. 제품 연결 검사 완료와 phase/integration 승격 완료를 구분합니다.
