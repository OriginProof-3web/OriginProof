# W5 — D 개인 작업 기록

## 범위와 현재 상태

- 담당: D / M2 여인준님, GitHub `@yijun0330`.
- 작업 ID: `W5-D1`, `W5-D2` 실행 준비. `W5-D3`는 P0 완료 후로 보류.
- 기준: [계획서 15.6절](../development_plan.md), [ADR 0001](../adr/0001-finals-contracts.md).
- 시작 기준: `integration@3295a71c10a1a99c523d3cfefde91b5737b737ac`. 2026-10-03 확인 시 `phase/W5`가 없습니다.
- 브랜치: `test/w5-d-p0-qa`. 문서/운영 계획만의 Draft PR을 `integration`으로 제출합니다. 단계 기능을 W4에 넣거나 phase 완료를 선언하지 않습니다.
- 현재 상태: D1 매핑·후보 독립 실행·실패 재현 보고 완료, D2 통합 UI와 B/C 혼합 장애 원인 확인·작성자 외 리뷰 대기.

## 문제와 변경 결과

앞 단계의 코어·실제 DB/chain·브라우저 결과를 F01~F15별로 연결할 필요가 있었습니다. 특히 W3의 `VERIFIED + null`과 W4의 `ACTIVE`, API 준비와 UI 동작을 합쳐 최종 성공으로 오해할 수 있습니다.

[추적표](../qa/w5-d-acceptance.md)와 [구조화된 원본](../qa/w5-d-acceptance.json)에 15개 항목의 담당 작업·검사 파일/명령·실행/제품/보고 SHA·부분 결과·잔여 검사를 연결했습니다. [D2 계획](../qa/w5-d-e2e-plan.md)에 세 역할 실행 순서 15개와 새 세션·실패·접근성·증거 조건을 준비했습니다. 제품 소스나 공유 정책은 변경하지 않았습니다.

## 개인 기여와 협업

| 작업 ID | 이번 에이전트가 수행한 일 | 재사용·다른 담당자의 기여 | 근거 | 상태 |
| --- | --- | --- | --- | --- |
| W5-D1 | 기존 D W1~W4 원 보고서와 검사 코드 대조, SHA 고정 근거 10그룹·F01~F15 매핑, 누락/실패 구분 | A/B/C가 제공한 제품과 앞 단계 D 검사 결과. 이번에 그 구현을 작성한 것으로 기록하지 않음 | [추적 원본](../qa/w5-d-acceptance.json) | 작성·검토 준비 |
| W5-D2 | 세 역할 P0·오류·접근성 순서, 준비 조건·판정·안전한 증거 형식 작성 | C PR37 후보 계약과 이전 W2/W3/W4 helper·실패 결과 참조 | [실행 계획](../qa/w5-d-e2e-plan.md) | 준비; 통합 실행 NOT_RUN |
| W5-D3 | 선행 P0 완료 전 선택 확장 보류를 기록 | 승인된 계획·ADR | 계획서 15.6절 | 보류 |

## 주요 판단과 누락 확인

- 기존 기록을 고정 SHA로 참조했습니다. 검사 helper를 현재 integration에 복사하거나 소유자 기능을 대리 구현하지 않았습니다.
- W2 6 통과/6 실패, W3 QR D 미실행, W4 D3 브라우저 12개 미실행을 유지했습니다. C PR37은 W5 준비 후보이며 임시 W4 base의 병합 금지와 W6 runtime 결과의 차이를 명시했습니다.
- F06 실제 unknown Proof 조회, F11 중지 중 새 발행 거부, F14 실제 다른 chain 서명 재사용, F15 요청 제한·전체 비밀정보 검사에서 선택한 D 자료에 없는 근거를 찾아 후속 검사로 연결했습니다. 근거 부재를 제품 미구현으로 단정하지 않았습니다.
- 문서 준비를 P0 또는 단계 완료로 처리하지 않았습니다. D의 자기 검증과 A/B/C 구현·C 통합 조율을 구분했습니다.
- 독립 에이전트 검토의 W2 한계 참조·0 skipped 표현·W3 opt-in 사전 조건 권고를 반영했습니다. 작성자 외 사람의 리뷰 피드백은 아직 없습니다. 읽기 검토는 소유자의 승인으로 기록하지 않습니다.

## 검증·시연 증거

현재 변경은 문서와 추적 JSON입니다. 구조/환경·문서 참조·SHA/파일·명령·정책·비밀정보 검사를 수행했습니다. staged diff의 공백 오류와 변경 범위도 확인했습니다. 과거 기능 검사 결과는 원 보고서 링크이며 이번 신규 기능 실행으로 세지 않습니다.

| 검사 | 결과 | 범위·한계 |
| --- | --- | --- |
| frozen uv 환경 준비 | 완료, 51개 package 설치 | 새 checkout 전용 `.uv-venv`, 기존 환경/lockfile 변경 없음 |
| `make bootstrap-check` | PASS | 구조·필수 파일/명령·Compose CLI 검사. 서비스 실행 성공 증거 아님 |
| `make env-fingerprint` | PASS | 기준 SHA의 환경 자료를 추적 JSON에 기록. Node 22.18.0·pnpm 11.19.0·Python 3.13.7(지정 3.13.0과 차이)·uv 0.8.17. host forge 미설치는 참고 정보 |
| JSON F01~F15/근거/담당 ID·고정 SHA 파일·문서 링크 | PASS | 15 F항목·10 근거·6 차단/누락 항목, immutable 파일/Makefile 35개·Markdown 참조 122개. 임시 표준 라이브러리 checker, 기능 테스트 아님 |
| `git diff --cached --check`·수정 경로 확인 | PASS | docs 내 4파일만 변경; 소스·lockfile·개인 설정 보존 |
| 독립 에이전트 문서 검토 | 검토·권고 반영 | W2 한계 참조·0 skipped 표현·W3 opt-in 사전 조건 정리, F03 v1 코드 참조 추가. C/A/B나 사람의 리뷰 승인 아님 |
| W5 D2 실제 UI/API/DB/chain·접근성 | NOT_RUN | 같은 W5 통합본·웹/API/Contract·기동 인계 대기 |

이번 준비에서 DB 초기화·서비스 배포·유료 모델 호출은 수행하지 않았습니다. 원 사용자 checkout의 미커밋·미추적 파일과 개인 `.env`는 보존했습니다. 임시 별도 clone을 사용했고 managed worktree 도구는 Git unavailable로 생성되지 않았습니다.

## AI 활용과 본인의 판단

Codex가 D1 추적 자료와 D2 문서를 작성했습니다. 읽기 전용 보조 에이전트가 W1/W2·W3/W4의 실제 코드/보고서 근거를 대조하고 문서를 검토했습니다. 기존 Graphify 그래프의 읽기 질의를 재사용했고 Ponytail 기준으로 별도 검사 프레임워크나 SDK를 추가하지 않았습니다. Graphify 재생성·Serena 메모리 갱신을 하지 않았습니다.

사람이 직접 설계·수정·확인한 범위나 기여 비율은 이 대화만으로 알 수 없어 추정하지 않습니다. 사용자가 D의 W5 착수를 지시했으며 사람의 결과/기여 사실 확인은 별도로 남깁니다.

## 남은 작업과 사실 확인

- D: W5 통합본 handoff 후 [D2-01~15](../qa/w5-d-e2e-plan.md)를 실행하고 결함을 재검사합니다. 현재 자기 영역의 추적·실행 준비를 마쳤다는 것과 W5 P0 완료는 구분합니다.
- A/B/C: 각각 화면·체인/Indexer·API/기동을 인계합니다. C가 단계 통합·승격을 조율합니다. D는 이 작업을 사용자님의 필수 대리 구현으로 추가하지 않습니다.
- W5-D3: P0 D1/D2 완료 뒤 팀 결정에 따라 선택 기능 검토. 현재 보류가 기본입니다.
- 본인 사실 확인: 아직 미확인. 에이전트가 사람의 확인을 대신 채우지 않습니다.
- 작성자 외 리뷰어: 아직 미확인. 실제 리뷰 링크·확인 범위를 받은 뒤 갱신합니다.

## 2026-10-04 — 후보 독립 실행 추가

[실제 보고](../qa/w5-d-api-verification.md), [결과 JSON](../qa/w5-d-api-results.json)에 고정 제품/QA SHA와 범위를 기록했습니다. D가 새 fixture 두 파일로 현재 후보의 실제 socket HTTP·PostgreSQL·Anvil·projection worker/API process 재시작/reorg를 재현했습니다. C/B 소스는 변경하지 않았고 기존 D W4 helper를 재사용했습니다.

- 기본 fresh clean clone: **18 보고 그룹 PASS / 0 FAIL**, 소스 hash·qa_git_dirty=false·소유 자원 부재 확인.
- 같은 코드 mixed 진단: **17 PASS / 1 FAIL**. 재기동 후 lifecycle verify의 INCONCLUSIVE/DEPENDENCY_UNAVAILABLE를 재현했습니다. B/C 원인 확인 대기이며 성공에 합치거나 제품 수정으로 닫지 않았습니다.
- 후보 Makefile 구조·환경 PASS, `make test`284PASS/4opt-in skipped, 표준 Foundry 컨테이너22PASS/0FAIL/0skipped. 이 수를 D 그룹이나 fuzz 반복과 중복 합산하지 않았습니다.
- 처음 signer 검사에서 확장자 선택이 틀린 QA 결함은 `key_*` raw32byte·권한 검사로 보완했습니다. 권한표의 consume404·Proof revoke 필수reason도 실제 계약과 맞췄습니다. 제품 코드를 바꾼 해결로 기록하지 않습니다.
- 앞선 혼합 스택 lifecycle 실패를 조사하며 원래 fixture의 fresh DB/chain 범위를 유지했습니다. 재현 가능한 mixed flag를 삭제하지 않고 현재 QA 커밋에 함께 보존했습니다.
- 독립 코드 branch `test/w5-d-api-qa`는 push로 공유합니다. phase/W5가 없어 기능 PR의 단계 대상 생성은 대기하며 이 문서 PR52는 docs만 유지합니다.
- 기본 provider/model은 mock/gpt-6-luna, 유료 호출0. 개인 .env·사용자 작업·기존 서비스·Serena/Graphify 보존. 새 소유 합성 자원의 migration/로컬 배포·종료를 수행했으며 운영 DB/배포는 하지 않았습니다.

W5-D2의 실제 UI·QR·키 관리·consume·접근성은 A/C의 같은 통합 화면 인계 뒤 실행합니다. W5-D3는 P0 완료 후로 보류입니다. Codex가 D 코드·실행·보고를 수행했고 사람의 결과/기여 사실 확인과 작성자 외 리뷰는 PENDING입니다. 초기 문서 준비 당시 기능 미실행 기록은 당시 범위로 보존합니다.
