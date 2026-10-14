# Blockchain Integration Agent Instructions

## 1. 적용 범위와 담당

`services/indexer/`에 적용하며 루트 `AGENTS.md`를 먼저 읽습니다.

B가 이벤트 projection·checkpoint·로컬 배포·manifest와 API blockchain Adapter를 담당합니다. API orchestration·공통 Python 모델은 C 소유입니다.

## 2. 구현·계약 규칙

공개된 ports/ABI에 맞춰 읽기·쓰기·receipt·재조회·오류를 연결합니다. 미등록만 absent로 반환하고 RPC/ABI/network 실패는 dependency 오류로 구분합니다. projection을 현재 체인 상태의 권위로 사용하지 않습니다. 신규 공동승인·버전/대체·철회·정지 이벤트는 ADR 0004의 별도 배포/ABI로 연결하고 과거 deployment와 checkpoint를 혼합하지 않습니다.

chain ID·주소·배포 SHA·배포 인자·배포 구분 정보를 manifest로 관리합니다. block/log identity와 checkpoint로 중복·재시작을 처리하고 체인 재배포 시 이전 projection과 Proof를 새 환경에 섞지 않습니다. 제출 결과가 불명확하면 Operation 복구 계약을 따라 재전송을 보류합니다.

## 3. 검증과 완료

배포/ABI·기관/키/Proof 상태 읽기·쓰기·실패 receipt·RPC 단절·중복 event·checkpoint 재시작·체인 재배포를 검사합니다. 실제 로컬 EVM 검사를 mock과 구분하고 새 배포 manifest와 최종 상태 재조회 근거를 남깁니다.

## 4. 인계

C에게 Adapter 입력/출력/오류·확정/복구 방법·사용 SHA를 전달합니다. Contract 변경은 같은 B 담당이어도 ABI·배포 소비자 영향을 별도 검토합니다.
