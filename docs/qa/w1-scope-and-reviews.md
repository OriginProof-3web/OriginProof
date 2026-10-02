# W1 범위·기여·리뷰 정리

기준: `phase/W1@0308cb24f9e4aed157095131e2552243767d16eb`, 2026-10-02. 사용자님은 W1 완료 준비 1~5번을 수행하도록 지시했습니다.

## W2 선행 구현의 처리

처리 방식은 **이미 병합된 이력을 보존하고 W1 수용 기준과 W2 선행 구현을 문서로 구분**하는 것입니다. 완료 단계 동결은 아직 하지 않았습니다. 공개된 PR/commit을 되돌리거나 W2 구현을 삭제하면 현재 phase/W2 및 후속 PR 의존성에 영향을 주므로 파일 삭제·history rewrite로 분리하지 않습니다.

| 원래 PR | W1에 필요한 것 | 포함된 선행 범위 | 단계 판정 |
| --- | --- | --- | --- |
| [#26 B](https://github.com/OriginProof-3web/OriginProof/pull/26) | Registry/Reader 조사·ABI·권한/상태/신뢰 계약, W1-B1/B2 설계 | Writer, 강화 manifest, projection/checkpoint, W2 chain 문서·W2-B 기록 | 선행 W2 구현으로 보존; W1 login/신청 완료 증거가 아니며 W2 별도 검증 필요 |
| [#27 A](https://github.com/OriginProof-3web/OriginProof/pull/27) | login/logout·역할별 신청/검토 화면, W1-A1~A3 | read-only Operation/AuditEvent monitor 및 W2 handoff | W1 API에 없는 조회는 W2 연결 대기; W1 범위는 신청/검토 상태로 판정 |

B가 PR #26에 W1-B1/B2 + W2-B1/B2 범위를 명시했고 C는 수정 head `741b8f8`의 phase/W1 통합을 승인했습니다. A PR #27도 W2 read-only 범위를 명시했고 C가 head `ffb96e8`을 승인했습니다. 이는 이미 수행된 범위 검토의 근거이며 새로운 B/C 동의나 W2 완료를 만들어내지 않습니다. 이번 사용자 요청과 계획서의 독립 선행 개발 규칙에 따라 보존 방식을 채택했습니다. 단계 승격 PR은 이 선행 범위를 포함 사실로 요약하고 W2 수용 증거는 별도로 연결합니다.

## 실제 리뷰 현황

| PR | 구현 담당 | 확인한 리뷰 | 남은 경계 |
| --- | --- | --- | --- |
| #23 W1 API | C | 2026-10-02 D `yijun0330` 승인; Codex 사후 검토임을 명시 | 새 후보 변경의 단계 최종 승인 별도 |
| #26 W1/W2 B | B | C 승인, head `741b8f8` (기존 요청 수정 후) | B의 C3 계약·기여 사실 확인 |
| #27 W1/W2 A | A | C 승인, head `ffb96e8` | A의 생성 계약/기여 사실 확인 |
| #30 W1 D | D | C 승인, head `5a55949` | 새 live QA/fixture 수정 리뷰 별도 |
| #32 W1 C3 | C | 2026-10-02 D `yijun0330` 승인, head `2cc8be2`; Codex 사후 검토 | B/A 소유자 확인 |

저장소에 `.github/CODEOWNERS` 파일은 없습니다. 따라서 자동 CODEOWNER 승인 상태가 있다고 주장하지 않습니다. 루트 지침의 경로 소유자와 별도 지정 리뷰어 기준을 적용합니다. D의 사용자 지시에 따라 에이전트가 실제 검토한 결과와 소유자 본인의 확인을 구분합니다.

## 네 명의 기록

- [W1-A](../portfolio/W1-A.md): PR #27/commit에서 확인되는 기여로 새 기록을 작성했습니다. A 본인이 확인했다고 표시하지 않습니다.
- [W1-B](../portfolio/W1-B.md): 기존 문서만 작성한 시점의 기록을 유지하고 혼합 PR의 현재 상태와 후속 검토를 덧붙였습니다.
- [W1-C](../portfolio/W1-C.md): C의 원 기록을 유지하고 D가 확인한 API/생성 계약 결과를 덧붙였습니다.
- [W1-D](../portfolio/W1-D.md): 실제 후보 live QA와 fixture 수정·발견/해결·검증 결과를 갱신했습니다.

기여 비율, A/B/C 본인의 확인, 다른 사람의 최종 단계 승인을 추정하지 않았습니다. 소유자·외부 리뷰가 확인되면 해당 review URL/날짜/범위를 기록합니다.
