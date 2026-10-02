# W1 / A / 김형준 — 근거 기반 기여 기록

- GitHub 계정: `@kimhyounjun`, PR #27 작성자 기준.
- 실제 원 작업 기간: 2026-10-01 (PR의 A 구현 커밋 기준). 기록 보완: 2026-10-02.
- 작업 ID: W1-A1/A2/A3. 상태: 구현·실연결 검증 자료 확보, 본인 사실 확인 및 새 수정 리뷰 대기.
- 근거: [PR #27](https://github.com/OriginProof-3web/OriginProof/pull/27), 구현 `d64c97a`, `ffb96e8`.
- 공식 phase 기준: `0308cb24f9e4aed157095131e2552243767d16eb`; 새 D 수정·검증 후보: `f1de961d8f94405d5a143cd853421eee8878b4f1`.
- 단계 승격 초안: [PR #39](https://github.com/OriginProof-3web/OriginProof/pull/39).

## 실제 기여와 협업

| 담당 | 확인 가능한 수행 | 근거와 한계 |
| --- | --- | --- |
| A | 세 역할 흐름·권한/입력/오류 정의, login/logout와 역할별 신청·검토, 체인 대기 표시, component/route-mock E2E 작성 | PR #27 및 `apps/web/W1_A1_SCREEN_FLOW.md`, `apps/web/app/finals/page.tsx` |
| C | 실제 인증·세션·신청/결정 API, PR #27 독립 화면 범위 리뷰 | PR #23, #27의 C 승인 |
| D/Codex | 공식 W1 API·DB와 실제 브라우저 확인, 승인 화면 접근성 최소 수정, 새 live QA와 기록 보완 | [최종 QA](../qa/w1-final-verification.md). 이 후속 작업을 A의 단독 기여로 기록하지 않음 |

A는 서버가 반환한 role/issuer를 사용하고 역할 선택 입력을 만들지 않았습니다. DB 승인과 체인 성공을 다른 상태로 표시했으며, 아직 계약이 없는 후속 기능의 endpoint를 임의 구현하지 않았습니다. PR #27은 W2 read-only 작업/감사 monitor도 포함합니다. [단계별 범위](../qa/w1-scope-and-reviews.md)에서 구분합니다.

PR #27 원 기록에는 Node 기준 차이와 route mock 검사, Next dev/build 동시 실행 시 `.next` 충돌 및 순차 재검증을 남겼습니다. 이번 D 검사는 Node 22.18.0에서 실제 서비스를 연결했고, 승인 화면의 definition-list 오류를 후보에서 수정했습니다. 원 작업의 선택/실패와 후속 발견을 구분합니다.

## 검증 증거

[최종 QA 보고](../qa/w1-final-verification.md)의 실제 SHA·환경·명령을 참조합니다. 후보에서 component 6개, 기존 route-mock E2E 4개, 새 실제 Chromium 흐름 1개와 DB/세션 검사가 통과했습니다. lint/typecheck/build도 통과했습니다. [승인 후 체인 대기 화면](assets/W1/live-approved.png)은 D가 만든 합성 계정의 실제 결과입니다.

v2 Proof 발행/공개 조회·비교 UI 및 W2 키 쓰기 화면 완료는 이 W1 기록에 포함하지 않습니다. 성능이나 기여 비율은 측정하지 않았습니다.

## AI 활용·사실 확인

PR #27은 Codex의 UI·검사 초안 보조를 명시합니다. 이 누락 기록은 사용자 요청에 따라 D/Codex가 PR·commit·재현 근거로 작성했습니다. A의 본인 판단/새로운 승인 발언을 추정하지 않았습니다.

- A 본인 확인: 미확인.
- 기존 작성자 외 코드 리뷰: PR #27의 C 승인 (`ffb96e8`).
- 이번 접근성 수정·기록의 A/C 최종 확인: 미확인; 새 수정 PR에서 필요.
