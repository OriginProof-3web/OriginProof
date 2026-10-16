# Conventions and Invariants

- 소유권은 루트 AGENTS.md 4절을 따릅니다: A 웹, B Contract·Indexer·API blockchain Adapter, C 나머지 API·Python 코어·통합 조율, D Analyzer·합성 fixture·독립 QA. M1~M4는 과거 역할명입니다.
- 공유 모델은 packages/python/originproof_core가 원본입니다. Schema/OpenAPI/TypeScript는 생성 경로를 사용하며 소비자 계약 변경에 호환성·migration·관련 리뷰를 포함합니다.
- v1 회귀 서명은 docs/signing_spec.md, 본선 두 유형은 ADR을 따릅니다. 승인된 정책을 구현 완료로 간주하지 않습니다.
- AI는 후보 필드만 반환하고 모르는 값은 null입니다. refusal·incomplete·timeout·rate limit·schema mismatch를 처리합니다.
- 검증 상태와 lifecycle을 분리합니다. NOT_REGISTERED를 가짜라고 표시하지 않습니다.
- 비밀·개인정보·원문·전체 payload를 체인·로그에 기록하지 않습니다. 업로드 제공 시 signature·MIME·크기·페이지 제한을 검사합니다.
- 작업 branch → phase/Wn → integration. phase가 없으면 integration에서 독립 준비가 가능합니다. main 통합과 완료 phase 변경은 루트 지침을 따릅니다.
