# D GitHub 리뷰 공유 현황

2026-10-16 한국시간, 사용자 요청으로 아래 D 전용 브랜치와 Draft PR을 공유했습니다. 이전 인계/QA JSON의 push·PR 미수행 표시는 해당 검사 시점의 역사 기록이며 현재 공유 상태는 이 문서를 따릅니다.

계획서 5.1 / 병합 기준 v5-shared-0.1입니다. 과거 보존 phase/W1~W4와 integration은 직접 수정하지 않았고, B/C와 같은 단계별 Draft stack으로 변경 범위를 분리했습니다. **PR/브랜치 공유는 작성자 외 리뷰·실제 연결·단계 완료를 뜻하지 않습니다.**

| 리뷰 순서 | PR·범위 | head 브랜치 | base 브랜치 |
| --- | --- | --- | --- |
| 1 | [#70 · 기준 반영·기존 D W1 보존](https://github.com/OriginProof-3web/OriginProof/pull/70) | `codex/v5-1-d-baseline` | `integration` |
| 2 | [#71 · W1 안전성 재사용·근거 소비](https://github.com/OriginProof-3web/OriginProof/pull/71) | `codex/v5-w1-d-safety-qa` | `codex/v5-1-d-baseline` |
| 3 | [#72 · W2 기관 승인·governance 실패 QA](https://github.com/OriginProof-3web/OriginProof/pull/72) | `codex/v5-w2-d-governance-qa` | `codex/v5-w1-d-safety-qa` |
| 4 | [#73 · W3 내용·DB 변조 QA](https://github.com/OriginProof-3web/OriginProof/pull/73) | `codex/v5-w3-d-content-qa` | `codex/v5-w2-d-governance-qa` |
| 5 | [#74 · W4 버전·키 상태 QA](https://github.com/OriginProof-3web/OriginProof/pull/74) | `codex/v5-w4-d-lifecycle-qa` | `codex/v5-w3-d-content-qa` |
| 6 | [#75 · W5 규칙·OpenAI 분석기·평가 초안](https://github.com/OriginProof-3web/OriginProof/pull/75) | `codex/v5-w5-d-analysis` | `codex/v5-w4-d-lifecycle-qa` |
| 7 | [#76 · 후속 연결 QA·자료 자체 점검·clean/G07 기록](https://github.com/OriginProof-3web/OriginProof/pull/76) | `codex/v5-d-independent-qa` | `codex/v5-w5-d-analysis` |

선행 PR 아래에서 다음 PR을 보면 각 단계의 차이만 검토할 수 있습니다. W2/W3/W4는 각각 검사 파일과 개인 기록 두 파일입니다. W5 분석기와 후속 QA도 분리했습니다. 선행 병합/새 phase 생성 뒤 대상 변경은 C의 통합 조율과 리뷰에 따르며 자동 병합은 설정하지 않았습니다.

## 검증 근거와 리뷰할 항목

- 검증된 전체 원본: `52c80b8d974d0a0542680d687447bce7cba413f8`, 실행 소스 `40ab4da11c71d75d26b6b94145e53ee03e3d54a6`. 공유 직전 연결 head `17050ef56a46c90ba5b791275964fad4bf022ea5`는 실행 파일·fixture·공통 계약·lock이 원본과 같고 W2~W4 개인 기록의 링크만 고정 SHA로 바꿨습니다. 이후 이 공유 목록/현재 상태 링크 추가는 문서 변경입니다.
- [D 분석 인계](v5_d_analysis.md): 공통 AnalysisReport·규칙/LLM 구분·발행 판정 금지·근거 대조. 공급자는 OpenAI만 사용하며 세부 모델/유료 범위는 미정입니다.
- [연결 QA](../qa/v5-d-independent-qa.md): 실제 D callback의 C ASGI/SQLite/합성 Registry12 PASS. 과거 제품 PostgreSQL/Anvil mixed18 보고 그룹 PASS는 신규 A/B/C 통합 또는 G07 해결이 아닙니다.
- [clean·자료·단계별 QA](../qa/v5-d-readiness.md): 같은 Mac 새 clone/venv292 PASS, W2 승인12/W3 내용·DB13/W4 버전·키5 PASS. 이전 검사와 중복 합산하지 않습니다.
- A 또는 C: 합성60개 자체 점검 중 라벨 경계5개·설명용 표식3개·분할 관계3묶음을 리뷰해야 합니다. 사람 리뷰·평가셋 동결·보류36개 모델 평가는 아직 없습니다.
- C: **DG12 겹친 반복 인용**의 자체 근거 함수 수정과 재검사가 필요합니다. D callback의 방어가 C 함수를 고친 것은 아닙니다.
- B/C: **G07**의 과거 혼합 환경 실패 원인·수정 인계가 필요합니다. 이번 비재현 PASS만으로 닫지 않습니다.
- GitHub CI는 각 PR의 Checks에서 확인합니다. 로컬 결과와 별도이며 PR 생성만으로 통과를 선언하지 않습니다. 사람/소유자 리뷰도 대기입니다.

이 요청에서 유료 모델·운영 배포·원격 병합·팀원 별도 메시지는 수행하지 않았습니다. 사용자 원본 파일과 기존 커밋 이력을 보존했습니다.
