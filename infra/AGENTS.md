# Infrastructure Agent Instructions

## 1. 적용 범위와 담당

`infra/`에 적용하며 루트 `AGENTS.md`를 먼저 읽습니다.

C가 API·DB·Redis·웹 기동 공통 설정을 조율하고 B가 로컬 EVM·배포 설정을 담당합니다. 루트 runtime 설정도 같은 담당 구분을 따릅니다.

## 2. 구현·계약 규칙

기존 Compose·Makefile·.env.example·healthcheck·고정 의존성을 재사용합니다. 인터넷 웹 호스팅은 자동 필수가 아닙니다. 공개 EVM은 별도 달성 목표이며 네트워크·배포 범위·비용·확정 기준은 V5-Q04에서 결정합니다. secret·운영 credential·불필요한 공개 port를 추가하지 않습니다. 기존 서버 서명기 파일/볼륨은 레거시 복구용으로 보호합니다. 신규 기관키는 기관 지갑에 두고 서버 백업 대상으로 만들지 않으며 가스 중계키는 별도 보호합니다.

make mvp-up·make demo-reset 등 기존 인터페이스 이름을 유지합니다. reset은 볼륨 삭제를 포함하므로 폐기 가능한 합성 환경에서만 실행합니다. DB/서명기/manifest/chain 상태를 서로 다른 배포에서 섞지 않습니다.

## 3. 검증과 완료

변경에 해당하는 clean startup·health·seed·restart·volume 격리·배포 복구를 확인합니다. 전체 서비스 재현과 기존 카드 회귀를 구분하고 새 기능은 실제 추가된 시나리오만 완료로 보고합니다.

## 4. 인계

서비스·환경변수·기본값·영향 데이터·migration/rollback·배포 구분 정보를 전달합니다. 파괴적 복구 명령의 대상과 필요한 승인을 명시합니다.
