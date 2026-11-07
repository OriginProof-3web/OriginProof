# GitHub Workflow Agent Instructions

## 1. 적용 범위와 담당

`.github/`에 적용하며 루트 `AGENTS.md`를 먼저 읽습니다.

C가 workflow·이슈/PR template·CODEOWNERS 등 공통 협업 설정을 조율하며 각 소유자가 영역별 검사를 제공합니다.

## 2. 구현·계약 규칙

CI는 로컬의 기존 Make/package 명령을 사용합니다. action 버전을 고정하고 최소 권한을 사용하며 검사 약화·secret 노출·광범위 쓰기 권한을 금지합니다. branch/PR 대상은 루트의 본선 흐름을 따릅니다.

CODEOWNERS·branch protection·자동 단계 승격은 실제 설정된 경우에만 동작한다고 설명합니다. 설정이 없으면 담당자 수동 리뷰 규칙을 적용합니다. 작성자의 자체 테스트와 D의 독립 QA를 혼동하지 않습니다.

## 3. 검증과 완료

workflow 변경은 문법과 해당 로컬 명령을 검사하고, 문서만 변경하면 링크·참조·규칙 일관성을 검사합니다. 현재 CI가 무엇을 검사하는지 실제 job을 확인하며 미구현 검사를 통과로 기록하지 않습니다.

## 4. 인계

job·명령·trigger·필요 secret 이름·실패 정책·PR 대상과 검증 결과를 전달합니다. 실제 secret 값은 기록하지 않습니다.
