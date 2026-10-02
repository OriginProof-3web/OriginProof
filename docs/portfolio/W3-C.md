# W3 C — 두 유형 발행·조회·검증

C / @Jordi2801K, W3-C1/C2/C3. 기준 phase/W2@1f8ed63, 작업 feat/w3-c-issuance.
구현·자체 및 실제 DB/체인 HTTP 검사 완료; A 화면 연결·B 교차 리뷰·D 독립 검증 대기.

C가 발행 API·원자적 저장/migration·수신자 binding 권한·typed 공개/제한 조회·코어/RPC 연결·검사를 구현했습니다.
B의 기존 Reader/Writer/manifest와 C의 W1 v2 코어·W2 signer/Operation을 재사용했습니다.
A/B/D 경로 구현·타인의 리뷰를 수행했다고 기록하지 않습니다. Codex가 구현·검사·원인 분석을 보조했습니다.

하나의 DB transaction과 W2 advisory lock을 재사용해 중복 발행과 교체 중 키 선택 충돌을 막았습니다.
수신자 token은 계정마다, salt는 Proof마다 생성하고 공개 응답에서 제외합니다.
별도 v2 테이블로 v1 회귀를 보존하며, 아직 없는 Proof 상태는 NOT_RUN/null로 명시합니다.
테스트 초기 실패는 합성 Reader의 Pydantic 위치 인자 사용과 optional 인증 테스트 경계에서 발생했으며,
키워드 모델 구성·FastAPI dependency로 수정 후 재검증했습니다.

전체 Python 236 passed / live opt-in 5 skipped, Ruff 통과.
실제 분리 PostgreSQL 16·Anvil 1.4.4 HTTP 검사 1 passed: 두 유형 새 서명/저장,
동시 동일 ID, 공개/수신자 조회·정상/변조 비교. migration/모델 check 통과.
macOS/Python 3.13 환경, 합성 계정·임시 DB/chain만 사용했습니다. 성능·실제 브라우저·타인 리뷰는 미측정/미실행입니다.
상세 계약·재현 원본: [W3 API 인계](../api/w3_c_proof_contract.md).
최종 코드와 실제 CI SHA는 작업 PR에서 확인하며 단계 전체 완료는 선언하지 않습니다.
