# Generated Schema Agent Instructions

## 1. 적용 범위와 담당

`packages/schemas/`에 적용하며 루트 `AGENTS.md`를 먼저 읽습니다.

C가 Python 원본에서 생성하는 JSON Schema·TypeScript 타입을 관리하고 B가 관련 ABI/event 소비 경계를 검토합니다.

## 2. 구현·계약 규칙

원본 Pydantic 모델 또는 Contract event를 먼저 수정하고 생성합니다. 생성 파일·enum을 손으로 수정하거나 중복 정의하지 않습니다. 생성 command·source version을 남기고 서명/호환성 변경은 ADR·migration 정책과 연결합니다. 모델·OpenAPI·실제 응답의 일관성을 검사합니다.

## 3. 검증과 완료

생성 전후 diff, 재생성 시 diff 없음, fixture 검증과 소비자의 컴파일을 확인합니다. 새 모델이 아직 구현되지 않았으면 계획 문서만으로 생성 완료를 주장하지 않습니다.

## 4. 인계

원본 경로·생성 diff·소비자·버전 전환 방법을 전달합니다. 기존 카드 v1 결과물을 조용히 덮어쓰지 않습니다.
