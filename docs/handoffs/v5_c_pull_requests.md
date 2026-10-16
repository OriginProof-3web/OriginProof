# 5.1 C 원격 공유 기록

대상 저장소: **OriginProof-3web/OriginProof** (`https://github.com/OriginProof-3web/OriginProof`). 사용자님의 명시적 push/PR 생성 지시에 따라 아래 여섯 브랜치를 공유하고 Draft PR #57~#62를 생성했습니다. PR은 순서대로 선행 브랜치에 의존합니다. 단계 통합/병합·main 승격은 포함하지 않습니다.

2026-10-16 후속: 잔여 C 개발 요청에 따른 신규 지갑 복구·독립 검증을 [Draft PR #63](https://github.com/OriginProof-3web/OriginProof/pull/63)으로 공유했습니다. `feat/v5-w6-c-recovery-integration` → `feat/v5-w5-c-analysis-retention`, 코드 근거 `c17a8f573bc8f64b522637cd3178f893baec8316`입니다. 기존 여섯 PR의 코드 근거/이력을 덮어쓰지 않습니다. 실제 5개 복구·527개 전체 회귀와 합성 범위·남은 연결은 [W6 구현 기록](v5_c_implementation.md#v5-w6-c-신규-지갑-복구독립-검증-2026-10-16)을 확인합니다. 새 PR의 원격 CI와 작성자 외 리뷰는 별도입니다.

공통 실행 코드 근거는 `650e85cd939ac4be493e14b4004daf081f92afa9`, 문서 근거는 이 파일을 포함한 후속 커밋입니다. [구현/검사 기록](v5_c_implementation.md), [실행 API 인계](../api/v5_c_runtime.md), [공유 계약 0.2](../shared_contract_v5.md)를 함께 검토합니다.

| 순서 | head: push할 브랜치 | Draft PR base | 제목 | PR |
| --- | --- | --- | --- | --- |
| 1 | feat/v5-w1-c-reuse-baseline | integration | V5 W1 C: 재사용 누적 기준과 5.1 전환 경계 | [#57](https://github.com/OriginProof-3web/OriginProof/pull/57) |
| 2 | fix/v5-w2-c-nonce-cleanup | feat/v5-w1-c-reuse-baseline | V5 W2 C: 제출 전 저장 실패·취소의 nonce 예약 해제 | [#58](https://github.com/OriginProof-3web/OriginProof/pull/58) |
| 3 | feat/v5-w2-c-governance | fix/v5-w2-c-nonce-cleanup | V5 W2 C: 기관 확인·키 증명·공동승인 DB/API | [#59](https://github.com/OriginProof-3web/OriginProof/pull/59) |
| 4 | feat/v5-w3-c-publication | feat/v5-w2-c-governance | V5 W3 C: 기관 서명 발행·직접 거래 대조·검증 API | [#60](https://github.com/OriginProof-3web/OriginProof/pull/60) |
| 5 | feat/v5-w4-c-document-lifecycle | feat/v5-w3-c-publication | V5 W4 C: 문서 버전·철회·키 이력과 사고 경고 | [#61](https://github.com/OriginProof-3web/OriginProof/pull/61) |
| 6 | feat/v5-w5-c-analysis-retention | feat/v5-w4-c-document-lifecycle | V5 W5 C: 분석 작업·보관/삭제·검증 결과 집계 | [#62](https://github.com/OriginProof-3web/OriginProof/pull/62) |

첫 PR은 integration에 아직 없는 C6 누적 소스(당시 A/B/D 자산 포함)도 담으므로 재사용과 신규 작성을 구분합니다. 후속 PR의 diff는 직전 자기 브랜치를 기준으로 합니다. 과거 phase는 보존하며 새 단계 통합 브랜치가 조율되면 base/선행 반영을 조정합니다. 여섯 PR은 검토용 Draft이고 단계 완료·타 담당자 승인으로 표현하지 않습니다.

## PR 1 본문

### 작업과 책임

C / @Jordi2801K, V5-W1-C. 기준 integration `33bc4f4`; 사용자 요청의 재사용 기준 확정 작업입니다. 5.1 계획과 ADR 0004를 적용합니다.

### 문제와 변경 결과

기능 코드가 옛 단계/개인 브랜치에 흩어져 있어 C6+integration 누적본 `ba8946c`를 기준으로 채택하고 원본 SHA·중복·후속 책임을 고정했습니다. 실제 새 Registry/API 연결을 완료한 PR은 아닙니다. C6 재사용에는 기존 A/B/D 기여가 포함되며 신규 C 작성으로 주장하지 않습니다. 알려진 #50 nonce 수정은 PR 2에 분리했습니다.

### 검증·기여·한계

원본 조사·모델/생성물과 구버전 회귀를 재사용했습니다. 당시 초기 Python 점검은 447 PASS/6 SKIP였고 #50 회귀 두 실패는 다음 수정의 재현 근거입니다. 최종 누적 코드 검사는 PR 6과 구현 기록을 따릅니다. Codex가 조사·문서/코드 작업을 수행했고 사용자는 개발 범위를 승인했습니다. 사람의 직접 작성·리뷰, B/A/D 승인·성능 성과는 추정하지 않습니다. 개인 기록: [W1-C](../portfolio/W1-C.md).

## PR 2 본문

### 작업과 책임

C / @Jordi2801K, V5-W2-C의 #50 적용. 기준 `7056a57`, 구현 `4a0e6fb`. B #50 `7e75986`의 제출 전 실패 정리를 사용자 지시에 따라 C 누적 Writer에 반영했습니다.

### 문제와 변경 결과

save_prepared가 실패/취소되면 예약된 가스 nonce가 남아 다음 정상 요청의 nonce가 건너뛰었습니다. 제출 전 저장 실패에서만 예약을 해제하고 불명확한 전송 UNKNOWN은 예약을 유지합니다. Writer 전체를 덮어쓰지 않아 기존 tx binding·복구를 보존합니다.

### 검증·기여·한계

Writer/기존 API 62 PASS, 실패·CancelledError 두 재현과 UNKNOWN 보호, Ruff/diff 통과. B 원본의 수정과 기존 Writer 기여를 재사용했고 Codex가 C 누적 흐름에 적용·검사했습니다. 실제 RPC/새 기관 지갑 연결과 작성자 외 리뷰는 후속입니다. 개인 기록: [W2-C](../portfolio/W2-C.md).

## PR 3 본문

### 작업과 책임

C / @Jordi2801K, V5-W2-C. 기준 `4a0e6fb`, 구현 `a303ec6`. 공유 계약·ADR 0004·앞선 nonce 수정에 의존합니다.

### 문제와 변경 결과

신규 기관 확인·지갑 증명·공동승인 준비 계약을 실행 DB/API에 연결했습니다. 합성 명부/데모 코드/별도 내부 승인, KeyProof의 단일 소비, 고정 제안·실제 거래 대조와 Operation을 추가했습니다. DB 승인이나 txHash만으로 기관을 활성화하지 않습니다. 0007 migration은 기존 테이블/자료를 유지하고 신규 저장만 추가합니다.

### 검증·기여·한계

당시 전체 Python 454 PASS/6 SKIP, 신규 HTTP 6개, 실제 임시 PG의 upgrade/0007 왕복/schema check 통과. Alembic의 누락된 기존 projection metadata도 등록해 삭제 자동생성을 방지했습니다. Codex가 기존 C 인증/CSRF/SQLAlchemy와 공유 모델을 재사용해 구현·검사했고 B Registry/Adapter는 별도 연결입니다. 새 의존성·기관 업무 개인키 저장을 추가하지 않았습니다. 작성자 외 리뷰·실체인·브라우저 검사는 대기입니다. 개인 기록: [W2-C](../portfolio/W2-C.md).

## PR 4 본문

### 작업과 책임

C / @Jordi2801K, V5-W3-C. 기준 `a303ec6`, 구현 `7913435`. 신규 기관 확인·공유 지갑 서명 계약을 사용합니다.

### 문제와 변경 결과

원본·서명·Operation을 제출 전에 저장하고 기관 지갑 서명/직접 tx의 불변 domain·action·문서/버전/hash를 대조합니다. 공개 문서·독립 검증 자료·원본/필드/ID 비교와 UNKNOWN 재조정을 추가했습니다. 기본은 직접 제출이며 접수 202는 체인 확정이 아닙니다. v1/v2 binding/consume은 유지합니다.

### 검증·기여·한계

당시 API/core 선택 검사 65 PASS(신규 HTTP 누적 15), 0008 PG upgrade/schema check 통과. request ID 충돌·잘못된 txHash·DB 내용/메타데이터 조작·범위별 판정을 검사했습니다. Codex가 C 저장/검증을 구현·검사했고 B/A/D의 구현·승인을 대신하지 않았습니다. 실제 Registry/브라우저/외부 리뷰는 후속이며 최종 경계 보완은 PR 6에 있습니다. 개인 기록: [W3-C](../portfolio/W3-C.md).

## PR 5 본문

### 작업과 책임

C / @Jordi2801K, V5-W4-C. 기준 `7913435`, 구현 `12ddb35`. 앞선 발행 저장과 공유 버전/철회 계약에 의존합니다.

### 문제와 변경 결과

정확한 latest+1·기관 문서 소유권·버전별 불변 원본·별도 Revoke 서명을 적용했습니다. 정지 중 현재 정상 키의 철회를 허용하고 정상 키 교체의 과거 서명과 사고 경고를 구분합니다. 최신 철회로 과거 버전을 복구하지 않습니다. DB 최신 포인터가 체인 권위를 대신하지 않습니다.

### 검증·기여·한계

당시 HTTP 누적 20 PASS: 다음 버전 경쟁·소유권·정지/철회·구키 신규 발행 거부·과거 서명/사고 경고·서로 다른 승인자 결과. 기존 C 서명/저장·B 상태 경계를 재사용해 Codex가 구현·검사했습니다. 합성 Registry 결과이며 실제 원자적 체인 전이·브라우저·작성자 외 리뷰는 후속입니다. 최종 철회 확정 보완도 PR 6과 함께 확인합니다. 개인 기록: [W4-C](../portfolio/W4-C.md).

## PR 6 본문

### 작업과 책임

C / @Jordi2801K, V5-W5-C 및 선행 C 경계 보완. 기준 `12ddb35`, 기능 코드 `30002bc`+`650e85c`, 후속 문서 커밋. 5.1 계획·공유 계약 0.2/ADR 0004를 적용합니다.

### 문제와 변경 결과

분석 접수·소유자 작업/이력·멱등/시간·네 보관 조합·다운로드/삭제·재시작 복구·grounding과 C 검증 사본 집계를 구현했습니다. 선택 입력은 기본 비활성 TEXT 합성 검사만 준비하고 D 실제 분석기를 주입합니다. 실제 모델 미연결을 성공으로 대체하지 않으며 모델의 발행 진위 결정은 거부합니다. 안전한 provider code만 노출합니다.

0009 migration은 검증 세션의 소유권·공개/LEGACY 범위와 분석 사본을 추가합니다. 서명/EIP-712·ABI·기존 v1/v2 Golden은 유지합니다. 선행 경계의 REACTIVATE zero proof·철회 REVOKED 확인·만료 RESIGN·Adapter 기관/키 식별·원본 부재 경고·보관 후 요청 410도 보완했습니다.

### 개인 기여·판단과 문제 해결

Codex가 기존 C 인증/Operation/SQLAlchemy·공유 모델과 생성기를 재사용해 구현·검사·문서를 수행했습니다. 실제 사람이 직접 수행한 코드 작성/리뷰를 추정하지 않습니다. B/A/D 원본·연결 책임은 구현 기록과 개인 [W5-C](../portfolio/W5-C.md)를 따릅니다. 새 의존성을 추가하지 않았습니다.

PG readiness의 첫 실패는 개인 .env의 구 기관/projection 값이 합성 fixture에 섞인 원인이어서 fixture 환경을 분리해 재검증했습니다. 정책 조건을 완화하지 않았습니다. worker는 현재 단일 API 프로세스 task로 제한하고 분산 실행 전 기존 queue로 이전해야 합니다.

### 검증과 한계

| 검사 | 결과 |
| --- | --- |
| 최종 코드 clean 사본·frozen 의존성, 명시 전체 Python 경로 | 494 PASS / live·외부 opt-in 9 SKIP, 기존 deprecation warning 1 |
| 신규 wallet HTTP/분석 | 위 전체에 포함된 45개 |
| 실제 임시 PostgreSQL의 동시 발행/분석/readiness | 별도 1 PASS; 체인 증거·processor는 합성 |
| PG migration 전체 적용·0009 왕복/schema check | PASS; 이전 0007 왕복·0008 적용 기록 별도 |
| Solidity/기존 Contract+wallet signing Golden | 26 PASS; 새 Registry 실구현 검사가 아님 |
| Node 두 템플릿 hash·생성 TS·5개 생성기 일치·Ruff/compileall·구조/diff | PASS, 기존 v1/v2 Golden byte 동일 |

실제 B Registry/Adapter·A 지갑/브라우저·D 모델/유료 평가·G07 혼합 환경·성능·작성자 외 리뷰는 미검증입니다. 입력 선정 전 기본 활성화, 공개 배포, 기존 phase/main 변경과 단계 전체 완료는 포함하지 않습니다.

## 공통 제출 확인

- 개인·재사용·AI 기여와 실제 코드/검사 근거를 구분했습니다.
- 원시 provider 응답·기관 개인키·실제 개인정보를 기록하지 않았으며 합성 검사를 사용했습니다.
- 여섯 브랜치의 원격 push와 Draft PR 생성·대화 첨부를 확인했습니다. 초기 #57/#58의 생성 타입 불일치는 b82a2d1에서 생성기로 고쳤고 후속 자기 브랜치에 병합했습니다. 재실행 CI는 확인 전입니다. 원격 CI와 작성자 외 리뷰는 생성 자체와 구분하며 전체 통과/승인을 가정하지 않습니다.
