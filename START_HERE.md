# OriginProof Start Here

## 현재 작업 기준

공통 데이터/API/서명/상태는 [공유 계약 v5-shared-0.1](docs/shared_contract_v5.md)과 연결된 생성물을 읽습니다. 정상·실패 예시와 독립 서명 검사가 준비되어 있으며 실제 Registry/API/지갑 연결·B/A/D 리뷰는 후속입니다.

MVP Gate는 완료되었습니다. 현재 기준은 [최신 개발 계획서](docs/development_plan.md)이며 기존 성과를 포함한 총 W1~W7입니다. Wn은 개발 단계이고 새로 7주를 더 배정하거나 달력 마감을 확정한 것이 아닙니다. 공동승인·기관 지갑 서명·문서 버전 관리를 기존 코드에 연결합니다. 입력 종류·우선순위는 회의 후 결정하고 Decisions API는 현재 개발 범위 밖입니다. 범위는 2장, 재사용은 4장, 담당별 작업은 12장, 수용 검사는 14장, 미정 값은 16.2절을 확인합니다.

[AGENTS.md](AGENTS.md) → 계획서의 작업/검사 ID → [ADR 0004](docs/adr/0004-v5-governance-wallet-versioning.md) → 경로별 AGENTS.md → 실제 모델/API/ABI/테스트를 읽습니다. ADR 0001~0003은 과거 계약과 5.0에서 유지한 기준의 근거입니다. [4.0 보존본](docs/development_plan_v4.0_snapshot.md)은 당시 작업·검사 정의 확인용입니다. 기존 v1 서명과 신규 서명 초안의 차이는 [서명 명세](docs/signing_spec.md)를 확인합니다.

## 개발과 연결

개발 착수의 공통 분석 제한·보관·데모 이메일 기준은 계획서 8.2·9장과 ADR 0004를 따릅니다. 입력별 제한은 선정한 경로에만 적용합니다. [UI/UX 설계 1.1](docs/ui_ux_design.md)의 15개 템플릿·UX01~14와 [산출물 상세안 0.5](docs/final_deliverables_draft.md)를 인계 기준으로 사용합니다. 지갑 연결 방식·최종 schema/ABI·모델·공개 네트워크는 [후속 결정 목록](docs/final_deliverables_pending_decisions.md)에서 추적합니다. 문서 작성과 계약 리뷰·제품 구현·실제 검사를 구분합니다.

자기 영역은 확정 정책·기존 계약으로 구현하고 mock/합성 데이터로 검사합니다. 필요한 새 계약은 소유자가 초안·예시·검사를 공유해 관련 담당자가 검토합니다. 팀원 코드가 없으면 실제 연결·완료 판정만 대기하고, 가능한 독립 구현 전체를 멈추지 않습니다. `독립 구현·검사 완료 / 실제 연결 대기 / 연결 검증 완료 / 단계 완료`를 구분합니다.

작업 시작에 branch·SHA·사용자 변경·선행 작업·검증 명령을 확인합니다. 현재 phase/integration과 lockfile 기준으로 자기 환경을 검사하고, 통합/다른 환경 재현 때 같은 SHA와 fingerprint를 비교합니다. 과거 bootstrap SHA로 되돌리거나 네 명 모두 준비될 때까지 독립 구현을 막지 않습니다.

## 브랜치와 공유

작업 PR은 해당 `phase/Wn`을 대상으로 합니다. phase가 없으면 최신 integration에서 단계별 준비 branch를 만들고 독립 작업을 진행합니다. 검사한 선행 결과는 자기 branch에 push하여 URL·SHA·사용 범위·미완료를 공유합니다. phase 생성 후 최신 변경을 반영하고 단계로 PR을 올립니다. 계획·운영 문서 PR은 integration을 대상으로 할 수 있습니다.

단계 전체 수용 기준·리뷰·검사·기여 기록이 끝나면 phase를 integration에 PR로 승격하고 최종 phase SHA를 보존합니다. integration → main 검증·PR은 사용자님 명시 요청 뒤 지정된 한 명이 진행합니다. fetch 시점·의존 PR·원격 공유·동결 규칙은 계획서 15장과 루트 AGENTS 8절을 따릅니다. 자동 백그라운드 병합/승격이 구성되어 있다고 가정하지 않습니다.

## 검사와 기여 기록

현재 Makefile·웹 package scripts를 확인하고 계획서 14.3절의 변경 영역 검사를 실행합니다. 기존 `make mvp-up`, `make mvp-test` 등 이름을 유지하되 MVP 검사 통과를 본선 전체 성공으로 보고하지 않습니다. `make demo-reset`은 DB 볼륨을 삭제하므로 허용된 폐기 가능한 합성 환경에서만 실행합니다.

[PR 템플릿](.github/pull_request_template.md)과 [개인 기여 안내](docs/portfolio/README.md)를 사용합니다. 자기 검사·실제 연결·독립 리뷰·미실행을 구분하고 개인 기록은 실제 작업한 단계만 작성합니다. 작성자 외 리뷰·재현이 없으면 받은 것으로 표시하지 않습니다.

## 과거 MVP 자료

[Bootstrap 기록](docs/runbooks/bootstrap.md), [MVP 통합 기록](docs/runbooks/mvp_integration_sequence.md), [MVP 데모](docs/runbooks/mvp_demo.md)는 당시 재현과 회귀 참고 자료입니다. `mvp/integration`과 `mvp-final`은 과거 결과를 식별하며 새 본선 작업의 기본 branch가 아닙니다. 현재 기동·lockfile·배포 정보가 과거 예시보다 우선합니다.
