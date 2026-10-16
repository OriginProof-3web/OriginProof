# Contract Agent Instructions

## 1. 적용 범위와 담당

`packages/contracts/`에 적용하며 루트 `AGENTS.md`를 먼저 읽습니다.

B가 신규 공동승인·기관 서명·문서 버전 Registry와 기존 Issuer/Key/ProofStatus Registry의 호환 경계, event·Foundry 검사·배포 script·ABI를 담당합니다. Contract와 배포/Adapter의 변경 및 검증 증거를 구분합니다.

## 2. 구현·계약 규칙

기존 Registry/ID 인코딩은 구버전 읽기·회귀에 보존합니다. 신규 Registry·documentId 계산·EIP-712 인코딩은 ADR 0004와 C/B 공통 Golden으로 구분하며 기존 주소를 덮어쓰지 않습니다. 원문·개인정보·계정 ID·salt·전체 payload·개인키는 온체인에 넣지 않습니다. 발행키와 Registry 운영권한을 분리하고 폐기 키는 재활성화하지 않습니다.

신규 경로는 등록·키 교체·재활성화 2-of-3, 단독 긴급 정지, 기관 EIP-712 서명·소유권·nonce·deadline·정확한 다음 버전을 컨트랙트에서 검사합니다. 배포자/업그레이드 단독 우회 권한을 두지 않습니다. 버전 등록·최신 포인터·이전 최신 버전 대체는 원자적으로 처리하고 최신 철회로 과거 버전을 활성화하지 않습니다. 서버 gateway·binding·consume은 기존 계약의 회귀이며 신규 공개 안내에는 적용하지 않습니다. 조회는 상태를 바꾸지 않습니다. 계획의 함수명은 배포된 ABI가 아니므로 실제 생성 ABI·manifest를 함께 전달합니다.

## 3. 검증과 완료

Foundry 정상·권한·경계·fuzz 검사에서 중복/만료 제안·단독 활성화·서명 재전송·다른 기관 소유권·동시 다음 버전·정지 중 철회·키 사고를 확인합니다. 구버전 consume 경쟁/재사용·gateway 우회·위조 commitment 회귀는 별도로 유지합니다. 실패/동시성은 receipt와 최종 상태로 입증합니다. C와 Golden Fixture·domain 호환성을 확인합니다.

## 4. 인계

ABI/event diff·버전·배포/migration 영향·실행 SHA·실제 검사 결과를 C와 Adapter 소비자에게 전달합니다. Contract 단위 성공을 API·웹 전체 완료로 표현하지 않습니다.
