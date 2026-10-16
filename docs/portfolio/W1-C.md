# W1 / C / Jordi — 개인 개발 기록

- 계정: @Jordi2801K
- 작업 기간: 2026-09-30 ~ 2026-10-01
- 상태: 독립 구현·검사 완료, 소비자 리뷰와 단계 완료 대기
- 작업: W1-C1~C4, 기준 phase/W1 322416e

## 실제 결과와 기여

C 인증·세션·권한·기관 신청은 PR #23으로 병합됐습니다. 후속 W1-C3는 ADR 0001의
두 유형 v2 모델·binding·서명/검증 경계와 생성 Schema/TypeScript/Golden을 구현했습니다.
기존 canonicalization/signature 알고리즘을 재사용하고 v1 모델과 fixture를 보존했습니다.
B Registry 명세는 입력으로 참고했으며 B 코드 수정이나 B/A/D 리뷰를 대신하지 않았습니다.

## 검증

Python core 검사 19개 통과: v1 Golden/기존 판정, 두 v2 서명 복구·binding·기간·타입,
실패 검사 순서·내용 누락/불일치·상태 우선순위·정상 키 기간 종료 이후 과거 서명.
실제 API/DB/EVM 새 v2 발행은 W3 범위로 미실행입니다. 코드 SHA는 작업 PR에 기록합니다.

## 판단·AI 활용·잔여

별도 v2 모델로 기존 v1 계약을 보존하고 현재 상태 미실행을 null/NOT_RUN으로 표시합니다.
Codex가 구현·검사·문서 작성을 보조했습니다. 정책은 사용자 승인 ADR을 따랐습니다.
B의 체인 경계 검토, A/D 생성물 소비, 단계 독립 확인은 아직 없습니다.

---

아래는 OriginProof 작업 폴더에서 수행한 공통 준비 기록입니다. 이 브랜치의 과거 구현·검사·기여 기록과 범위를 구분하며 대체하지 않습니다.

## W1 / C — 5.0 공유 계약 준비 기록

- 작업일: 2026-10-14 (W1은 개발 단계입니다.)
- 계정·범위: `@Jordi2801K`의 C 담당 범위에서 Codex가 명세·코드·검사를 수행했습니다. 사람이 직접 작성/검토한 기여나 B/A/D 승인을 대신 주장하지 않습니다.
- 상태: 준비 구현·독립 검사 완료, 소유자/소비 리뷰·실제 연결 대기
- 작업: V5-W1-C, V5-W1-B 서명/ABI 경계 준비
- 시작 기준: `3295a71c10a1a99c523d3cfefde91b5737b737ac` (origin/integration와 동일)
- 브랜치: `feat/v5-shared-contracts`

### 문제와 실제 변경

계획서 5.0의 공동승인·기관 지갑·문서 버전 방향을 팀원이 같은 규격으로 구현할 수 있도록 [공유 계약](../shared_contract_v5.md), Pydantic 원본·hash/서명 검사, 생성 Schema/TypeScript/예정 OpenAPI·인터페이스 ABI·정상/실패 예시를 준비했습니다. 기존 API·Registry·DB·v1/v2 읽기 동작은 바꾸지 않았습니다.

기존 canonical JSON·eth-keys·Crypto·Schema 생성기·Foundry/OpenZeppelin을 재사용했고 새 의존성을 추가하지 않았습니다. A/B/D의 기존 구현 및 사용자님의 기존 5.0 문서를 기반으로 했으며 실제 기여 비율은 측정하지 않았습니다.

### 판단·실패·검증

- 고정된 flat EIP-712 타입만 구현하고 범용 서명 SDK를 만들지 않았습니다. uint256은 decimal string, 다른 JSON 수치는 safe integer로 통일했습니다.
- Python 모델을 원본으로 타입/API 준비 정의를 생성하고 실제 FastAPI에 예정 route를 등록하지 않았습니다.
- 최초 union 모델 검사는 discriminator의 before validator 제약으로 실패해 해당 문자열 필드만 정규화하도록 수정했습니다.
- Foundry는 샌드박스 macOS 시스템 설정에서 충돌했고 동일 로컬 offline 검사를 허용된 환경에서 실행해 통과했습니다. 배포/유료 호출은 하지 않았습니다.
- Python 코어: 35 PASS (기존 11, 신규 24); Solidity: 14 PASS (기존 10, 신규 4), 기존 fuzz 512회 포함.
- TypeScript 타입 단독 컴파일·두 템플릿 Node Web Crypto hash 대조·Ruff·생성물 7개 재생성 일치·예정 OpenAPI 22 operation 참조 검사 통과.
- 기존 카드 Golden·기존 생성 Schema/TypeScript는 작업 전과 byte 동일합니다.
- SG01~16의 새 Registry 상태/동시성/권한·직접 tx·보관 검사, 브라우저 지갑·API E2E·DB migration·공개 배포·실제 모델 평가는 미실행입니다.

### 다음 담당자와 사실 확인

B는 ABI/키 이력/공동승인/nonce·버전 전이를 검토하고 Registry를 구현합니다. A는 동일 타입으로 원본 재계산·지갑 연결·거절/만료 UI를 검토합니다. D는 선정 입력과 SG01~16을 실제 연결 검사에 적용합니다. C는 검토된 원본으로 새 API·DB·복구를 연결합니다. 각 담당자는 별도 공유 계약 사본을 정의하지 않습니다.

소유자/소비 리뷰: 미확인. 사용자 입력·지갑 운영·공개 네트워크·모델·Decisions 미정 결정은 계획서 V5-Q01~09를 따릅니다. 기존 완료 phase를 수정하거나 W1 전체 완료로 표시하지 않았습니다.

### 실제 공유·CI 근거

- Draft PR: [#56](https://github.com/OriginProof-3web/OriginProof/pull/56), 대상 integration, 소유자/소비 리뷰 미확인.
- 검증한 코드 SHA: `8f1fcac6ed2b4d98d815f2b7e935facff06a0d77`. 이후 이 절을 추가하는 문서 커밋은 기능 코드를 바꾸지 않습니다.
- GitHub [Quality Gate](https://github.com/OriginProof-3web/OriginProof/actions/runs/38547258859): 위 코드 SHA의 python-quality/contracts 모두 SUCCESS 확인.
- 세 로컬 작업 폴더의 공통 문서·준비 모델/생성물은 동기화했고 각각 신규 검사 24개를 통과했습니다. 해당 폴더의 원래 구현/HEAD를 보존했으며 팀원 PC의 반영 완료를 대신 주장하지 않습니다.
