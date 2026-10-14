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

## 2026-10-14 5.0 공통 준비 자료

[공유 계약 v5-shared-0.1](../shared_contract_v5.md)의 모델·생성물·Golden을 공통 기준으로 사용합니다. 이번 준비의 검사는 OriginProof 작업 폴더에서 수행했고, 이 브랜치의 과거 검사/기여 기록을 대체하지 않습니다. B/A/D 리뷰·실제 연결은 후속입니다.

## 실제 공유·CI 근거

- Draft PR: [#56](https://github.com/OriginProof-3web/OriginProof/pull/56), 대상 integration, 소유자/소비 리뷰 미확인.
- 검증한 코드 SHA: `8f1fcac6ed2b4d98d815f2b7e935facff06a0d77`. 이후 이 절을 추가하는 문서 커밋은 기능 코드를 바꾸지 않습니다.
- GitHub [Quality Gate](https://github.com/OriginProof-3web/OriginProof/actions/runs/38547258859): 위 코드 SHA의 python-quality/contracts 모두 SUCCESS 확인.
- 세 로컬 작업 폴더의 공통 문서·준비 모델/생성물은 동기화했고 각각 신규 검사 24개를 통과했습니다. 해당 폴더의 원래 구현/HEAD를 보존했으며 팀원 PC의 반영 완료를 대신 주장하지 않습니다.
