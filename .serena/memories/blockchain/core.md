# Blockchain and Indexer

- B: packages/contracts, services/indexer, apps/api/src/infrastructure/blockchain. Contract와 Adapter는 각각 검증합니다.
- ADR 0004의 신규 Registry는 2-of-3·기관 EIP-712·고정 소유·원자적 다음 버전·정지/복구를 검사합니다. 현재 구현 완료는 별도 확인합니다. 과거 Registry/주소·consume은 회귀로 보존하고 신규 공개 안내에 consume을 붙이지 않습니다. projection은 현재 체인 상태를 대체하지 않습니다.
- 원문·개인정보·전체 payload를 온체인에 넣지 않습니다. Registry 운영키와 기관 발행키는 분리합니다.
- 이벤트 projection은 재처리·중복·재시작을 검증합니다. 배포 manifest에 chain ID·주소·source SHA·인자를 남깁니다.
- 권한·상태·경계값과 ABI 호환성을 검사합니다. 표준 Foundry 실행은 deployer 컨테이너를 사용합니다.
