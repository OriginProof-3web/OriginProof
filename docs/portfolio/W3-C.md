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


## 2026-10-02 W3-B1 연결 보완

W4 후속 branch `feat/w4-c-proof-lifecycle`의 C 코드 `596f313`에서 B W3 `92e0e94`의
get_issuer_key_snapshot을 발행·검증에 연결했습니다. 기관과 키의 동일 block/hash,
발행 직전 유효 구간·signer를 검사하고 Proof 상태 snapshot과도 일관성을 확인합니다.
이 branch에서는 W4 Registry가 연결되어 위 W3 최초 결과의 NOT_RUN/null 한계를 대체합니다.
C 자체 실제 DB/체인 검사는 통과했으며 A 화면·D 독립 확인·공유 phase 병합·팀 리뷰는 대기입니다.
[후속 연결·검사 상세](../api/w4_c_proof_lifecycle_contract.md)를 참조합니다.


## 5.1 후속 / V5-W3-C (2026-10-15~16)

- 상태: C 독립 구현·자체 검사 / 실제 Registry·웹·분석기 연결과 작성자 외 리뷰 대기. 단계 전체 완료는 아닙니다.
- 담당: @Jordi2801K의 C 범위에서 Codex가 구현·검사·문서를 수행했습니다. 사용자는 세 작업의 개발 방향을 승인했으며 사람의 코드 작성/리뷰·타인 승인이나 기여 비율은 추정하지 않습니다.
- 구현 근거: `7913435`. 최종 누적 검증 코드는 `650e85cd939ac4be493e14b4004daf081f92afa9`이며 후속 문서 커밋과 구분합니다.
- 결과: 원본/서명/Operation 선저장, 기관 지갑 서명 검증·직접 거래 대조·공개 조회·원본/필드 비교를 구현했습니다.
- 재사용: 기존 C 인증/CSRF/Operation/SQLAlchemy·B Writer/Reader 원본과 공유 서명 모델을 사용했습니다. 정확한 고정 SHA·타 담당 영역과의 경계는 [구현 기록](../handoffs/v5_c_implementation.md)을 확인합니다.
- 판단·문제 해결·실행 명령/환경·정상/거부 결과·실패 수정·잔여 위험·PR 근거는 같은 구현 기록과 [실행 API 인계](../api/v5_c_runtime.md)에 모읍니다. 중복해서 과거 PASS를 신규 실제 연결 성공으로 합산하지 않습니다.
- 최종 검사: 전체 Python 494 PASS/9 opt-in SKIP, 별도 실제 PostgreSQL 1 PASS(체인은 합성), Solidity/Golden 26 PASS, 두 템플릿 hash/타입·재생성·정적 검사 통과. 성능/공개 배포/실제 모델은 미측정입니다.
- 작성자 외 리뷰·본인의 기여 사실 확인: 아직 미확인입니다. 실제 리뷰 후 해당 링크를 추가합니다.

5.1 원격 공유: [#60](https://github.com/OriginProof-3web/OriginProof/pull/60) (Draft). 사용자 승인 후 자기 브랜치에 push하고 생성했습니다. 실제 원격 CI/작성자 외 리뷰·단계 완료는 별도입니다.
