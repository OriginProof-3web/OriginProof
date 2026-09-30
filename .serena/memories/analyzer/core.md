# Analyzer

- D: services/analyzer, 합의된 합성 fixture·평가·실패 사례·E2E 재현. 타 담당 테스트 변경은 소유자 handoff 또는 사용자 지시가 필요합니다.
- 현재 카드 회귀 추출의 CardPaymentNoticeCandidate를 보존합니다. 새 유형 지원은 현재 모델과 본선 계획의 구현 상태를 확인합니다.
- AI는 후보 추출만 수행하고 진위·Registry 상태를 결정하지 않습니다. 추출 실패 필드는 null입니다.
- LLMProvider/OpenAI/Mock 경로를 재사용합니다. 모델·reasoning·timeout·retry는 settings와 환경설정에서 읽습니다.
- mock 기본, 유료 live 검사는 명시적 범위에서만 실행합니다. P0 ID 조회·비교·발행은 AI 없이 동작해야 합니다. OCR는 선택 확장입니다.
