> **2026-10-31 D 후속:** [재검토·승인·충돌 정리·K10 확인](../qa/v5-d-rereview-20261031.md)에서 #106~#109 기술 승인과 최신 phase 반영, 기여 기록 보존·추가 유료0을 확인할 수 있습니다. K10은 최소 문장에서 미재현이며 실제 실패 입력이 필요합니다. 과거 날짜의 대기 항목과 구분합니다.

> **2026-10-30 최신 상태:** 아래 날짜별 기록은 보존 이력입니다. 현재 기준은 [D 마무리 인계](../qa/v5-d-final-audit-20261030.md)와 [불일치 검토·RC 준비](../qa/v5-d-review-and-rc-prep-20261030.md)입니다. 텍스트84+연결3+이미지46=누적133회 실행 후 유료 정책은 모두false입니다. 이미지23개 실측·리뷰/문서 수정은 #113, 이미지 전용 보관 수정은 #112이며 두 PR의 소유자 리뷰/병합과 최종 RC·다른 실제 장비·리허설은 별도입니다. 과거의 “유료0/미정·G07 미해결”을 현재 상태로 읽지 않습니다(G07은 RESOLVED_LOCAL_LEGACY).

# D GitHub 리뷰 공유 현황

> #84 D 기술 검토도 [이슈에 기록](https://github.com/OriginProof-3web/OriginProof/issues/84#issuecomment-6335937751)했습니다. 실행 HEAD fe5aed4: consumer31·분석기/SDK/API/연결114 PASS, failure/error/skip0. 합성·mock 결과이며 실제 모델·Registry·웹 연결은 후속입니다. [남은 작업 순서](../qa/v5-d-postmerge-20261022.md#다음-d-작업-순서와-필요한-인계).

> 2026-10-22 최신: D #72~#76은 팀에서 병합했고, B/C 검토를 근거로 G07을 로컬 legacy 범위 해결로 갱신했습니다. 병합 후953 PASS/opt-in11 SKIP. [정확한 SHA·검토·범위](../qa/v5-d-postmerge-20261022.md). 아래 이전 OPEN/미병합/리뷰 대기 문구는 당시 기록입니다. 사람 본인 확인·실제 신규 연결·단계 완료와 구분합니다.

> 최신 개발 완료 기록: 제한 모델 평가 실행기·수용 증거 도구·실제 로컬 독립 CLI 검증을 구현했습니다. G07은 fresh1/mixed5 각18 PASS, C 검토 전 OPEN입니다. [실행 SHA·검사·남은 인계](../qa/v5-d-development-completion-20261021.md). 아래 이전 미실행/미병합 표시는 당시 기록입니다.

> 2026-10-21 최신: 최신 공유 기준: 계획5.1/공유0.2, #75/#76 일반 PR, #82/#86/#87 병합 반영. G07 실제 반복 후에도 B/C 검토 전 OPEN. [현재 실행·수치·남은 작업](../qa/v5-d-performance-independent-20261021.md). 아래의 이전 SHA/미병합 표시는 당시 기록입니다.

> 2026-10-21 현재 점검: [W1~W7 작업·동일 HEAD 재검사](../qa/v5-d-weekly-status-20261021.md). 현재 C 0.2에서 DG12는 통과했고, 새 CI 증거 보호와 [의존성 보안 PR #87](https://github.com/OriginProof-3web/OriginProof/pull/87)을 검증했습니다. [후보 근거 평가·G07 사전 검사/반복 도구](../qa/v5-d-development-tools-20261021.md)를 구현했습니다. 실제 모델 평가·G07·사람 리뷰·실제 통합은 별도 대기입니다. 아래 날짜별 과거 결과와 구분합니다.

2026-10-18 한국시간 갱신. 10월16일 사용자 요청으로 아래 D 전용 브랜치와 PR을 공유했고, #70/#71은 병합됐습니다. #72~#76의 변경 요청을 수정해 기존 PR에 반영합니다. 이전 인계/QA JSON의 push·PR 미수행 표시는 해당 검사 시점의 역사 기록이며 현재 공유 상태는 이 문서를 따릅니다.

계획서 5.1 / 병합 기준 v5-shared-0.1입니다. 과거 보존 phase/W1~W4와 integration은 직접 수정하지 않았고, D 단계별 준비 stack으로 변경 범위를 분리했습니다. 현재 #72~#74는 일반 PR, #75/#76은 Draft이며 재리뷰/최종 승인은 대기입니다. **PR/브랜치 공유는 작성자 외 리뷰·실제 연결·단계 완료를 뜻하지 않습니다.**

| 리뷰 순서 | PR·범위 | head 브랜치 | base 브랜치 |
| --- | --- | --- | --- |
| 1 | [#70 · 기준 반영·기존 D W1 보존](https://github.com/OriginProof-3web/OriginProof/pull/70) | `codex/v5-1-d-baseline` | `integration` |
| 2 | [#71 · W1 안전성 재사용·근거 소비](https://github.com/OriginProof-3web/OriginProof/pull/71) | `codex/v5-w1-d-safety-qa` | `codex/v5-1-d-baseline` |
| 3 | [#72 · W2 기관 승인·governance 실패 QA](https://github.com/OriginProof-3web/OriginProof/pull/72) | `codex/v5-w2-d-governance-qa` | `phase/W5` |
| 4 | [#73 · W3 내용·DB 변조 QA](https://github.com/OriginProof-3web/OriginProof/pull/73) | `codex/v5-w3-d-content-qa` | `codex/v5-w2-d-governance-qa` |
| 5 | [#74 · W4 버전·키 상태 QA](https://github.com/OriginProof-3web/OriginProof/pull/74) | `codex/v5-w4-d-lifecycle-qa` | `codex/v5-w3-d-content-qa` |
| 6 | [#75 · W5 규칙·OpenAI 분석기·평가 초안](https://github.com/OriginProof-3web/OriginProof/pull/75) | `codex/v5-w5-d-analysis` | `codex/v5-w4-d-lifecycle-qa` |
| 7 | [#76 · 후속 연결 QA·자료 자체 점검·clean/G07 기록](https://github.com/OriginProof-3web/OriginProof/pull/76) | `codex/v5-d-independent-qa` | `codex/v5-w5-d-analysis` |

선행 PR 아래에서 다음 PR을 보면 각 단계의 차이만 검토할 수 있습니다. 최초 W2/W3/W4는 각각 검사 파일과 개인 기록 두 파일이었고, 리뷰 수정으로 W2에 고정 C 전용 CI/재현 문서를 추가하여 뒤 단계로 merge했습니다. 최신 integration #80의 검사 기준도 함께 반영됐습니다. W5 분석기와 후속 QA도 분리했습니다. 현재 base는 단계별 비교를 위해 유지했습니다. #72의 이미 병합된 base를 새 유효 phase로 바꾸는 작업과 후속 대상 변경은 C의 통합 조율과 리뷰에 따르며 자동 병합은 설정하지 않았습니다.

## 검증 근거와 리뷰할 항목

- 검증된 전체 원본: `52c80b8d974d0a0542680d687447bce7cba413f8`, 실행 소스 `40ab4da11c71d75d26b6b94145e53ee03e3d54a6`. 공유 직전 연결 head `17050ef56a46c90ba5b791275964fad4bf022ea5`는 실행 파일·fixture·공통 계약·lock이 원본과 같고 W2~W4 개인 기록의 링크만 고정 SHA로 바꿨습니다. 이후 이 공유 목록/현재 상태 링크 추가는 문서 변경입니다.
- [D 분석 인계](v5_d_analysis.md): 공통 AnalysisReport·규칙/LLM 구분·발행 판정 금지·근거 대조. 최종 모델은 사용자 선택으로 OpenAI GPT-6 Luna (`gpt-6-luna`)로 확정했습니다. 유료 범위/예산은 미정입니다.
- [연결 QA](../qa/v5-d-independent-qa.md): 실제 D callback의 C ASGI/SQLite/합성 Registry12 PASS. 과거 제품 PostgreSQL/Anvil mixed18 보고 그룹 PASS는 신규 A/B/C 통합 또는 G07 해결이 아닙니다.
- [clean·자료·단계별 QA](../qa/v5-d-readiness.md): 같은 Mac 새 clone/venv292 PASS, W2 승인12/W3 내용·DB13/W4 버전·키5 PASS. 이전 검사와 중복 합산하지 않습니다.
- A 또는 C: 합성60개 자체 점검 중 라벨 경계5개·설명용 표식3개·분할 관계3묶음을 리뷰해야 합니다. 사람 리뷰·평가셋 동결·보류36개 모델 평가는 아직 없습니다.
- C: **DG12 겹친 반복 인용**의 자체 근거 함수 수정과 재검사가 필요합니다. D callback의 방어가 C 함수를 고친 것은 아닙니다.
- B/C: **G07**의 과거 혼합 환경 실패 원인·수정 인계가 필요합니다. 이번 비재현 PASS만으로 닫지 않습니다.
- 최초 원격 공유 시점의 GitHub CI와 이번 수정 head의 CI를 구분합니다. 새 전용 stage QA가 #72~#75에서 실제 실행됐고, consumer는 DG12로 실패했습니다. 최종 상태는 각 PR Checks에서 확인합니다. 로컬 결과와 별도이며 PR 생성만으로 통과를 선언하지 않습니다. 사람/소유자 리뷰도 대기입니다.

이 요청에서 유료 모델·운영 배포·원격 병합·팀원 별도 메시지는 수행하지 않았습니다. 사용자 원본 파일과 기존 커밋 이력을 보존했습니다.


## 2026-10-18 변경 요청 반영

- #80 포함 최신 integration `54705588d660aceea71ff1cb03eefb5aefe37aa4`를 W2에 merge하고 D W3→W4→W5→QA로 순서대로 이력을 보존했습니다. 보존 phase/병합된 #70/#71/타 담당 제품은 수정하지 않았습니다.
- #72: 중복 승인 오염 snapshot은 `503 WALLET_REGISTRY_UNAVAILABLE`까지 검사합니다. #73: DB 5개 변조의 reason/check를 검사합니다. #74: 구키 신규 발행의 `422 INVALID_SIGNATURE`와 전송 목록 불변을 검사합니다. W2~W4의 브랜치/실행 소스/개별 최초 실패 수·현재 PR 공유 상태를 정정했습니다.
- #75: 검증 통과 출력의 항상 1.0 지표를 모델 후보 품질에서 분리하고, 미측정 후보 분모/일치 수/비율은 NOT_EVALUATED/null로 남겼습니다. 환각 격리·실패 분모·SDK timeout·총 기한/취소·안전한 예외 타입 메타데이터를 검증했습니다. test 모듈 직접 import도 공용 conftest fixture로 바꿨습니다.
- #76: 새 전용 CI가 C 고정 checkout을 쓰므로 D의 분석 연결 12개도 실제 CI 대상입니다. 최종 로컬 실행 소스 `b482875de7aa1014b7ef080b02950d7183b922b2`에서 stage 42 PASS, 같은 C 환경의 분석기 256 PASS입니다. C consumer는 별도 30 PASS / 1 FAIL(DG12)이며 실패를 숨기지 않습니다.
- 전체 최신 Python은 329 PASS / 1 SKIP(indexer live-chain opt-in), 생성물 diff 없음·Ruff·Python compileall/웹 tsc 통과입니다. 로컬 mock/합성 결과를 실제 체인·모델 검사로 합산하지 않습니다.

[수정·재현 명령과 CI 경계](../qa/v5-d-review-fixes.md), [구조화 재검사 결과](../qa/v5-d-review-results.json). 개발24개 재평가의 예측과 원본/라벨/분할은 그대로이며, 후보 근거 품질의 실제 평가·입력/유료 범위·A/C 라벨 리뷰·DG12/G07·동일 신규 A/B/C 실제 연결과 새 phase 대상 조율이 남습니다. 사람의 리뷰 승인을 만들어내거나 단계 완료로 처리하지 않았습니다.


## 2026-10-18 후속 사용자 결정

최종 모델은 **OpenAI GPT-6 Luna (`gpt-6-luna`)**로 확정됐습니다. [분석 인계](v5_d_analysis.md)와 [L05 결정 기록](../final_deliverables_pending_decisions.md)에 반영했습니다. 기존 코드·환경 예시 기본값과 같아서 실행 코드는 바꾸지 않았고 문서/설정 대조만 수행했습니다. 과거 모델 미정 문구는 당시 기록이며 현재 모델 선택 대기 항목은 해소됐습니다. 입력·유료 평가 범위/예산·라벨/분할 리뷰와 실제 모델 평가는 계속 후속입니다.
