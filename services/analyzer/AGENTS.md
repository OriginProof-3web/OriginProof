# Analyzer Agent Instructions

## 1. 적용 범위와 담당

`services/analyzer/`에 적용하며 루트 `AGENTS.md`를 먼저 읽습니다.

D가 후보 추출·LLMProvider·prompt·합성 입력 평가를 담당합니다. 본선 P0는 AI 없이 동작하며 OCR/이미지/PDF 확장은 P1입니다.

## 2. 구현·계약 규칙

기존 카드 추출은 CardPaymentNoticeCandidate 회귀로 보존합니다. 새 유형 추출은 P1로 채택되고 C의 해당 후보 모델이 준비된 경우에만 확장합니다. 공통 모델을 임의로 복제하지 않습니다.

provider 기본값은 mock, OPENAI_MODEL 기본값은 gpt-6-luna입니다. provider 전용 객체는 Adapter 내부에 유지하고 모르는 필드는 null로 둡니다. 진위 판단·AI 단계의 Registry 판정·원시 응답/민감값 로그를 금지합니다. 기존 어댑터·오류 처리를 재사용합니다.

## 3. 검증과 완료

Mock 단위·정상/변조·누락·refusal·timeout·incomplete·Schema 오류를 검사합니다. 실제 유료 API 검사는 명시적 opt-in이며 Mock replay를 실제 추출 정확도로 보고하지 않습니다.

## 4. 인계

C에게 후보 필드 변경과 합성 예시·기대 객체·평가 근거를 전달합니다. D의 전체 QA 역할이 다른 소유자의 테스트 경로를 무조건 수정할 권한을 뜻하지는 않습니다.
