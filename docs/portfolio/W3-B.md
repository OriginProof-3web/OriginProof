# W3 / B / 여하민 — V5-W3-B 최초 버전 기관 서명 발행

- GitHub 계정 `@hamin1228`, 2026-10-16 (W3는 개발 단계).
- 상태: Contract 독립 구현·검사 완료 / 실제 배포·Adapter·API/DB·지갑·작성자 외 리뷰 대기.
- 브랜치 `codex/v5-w3-b-publication`, 시작 `5f91ac8e3405ac2f3bbe9ae19e15b81dd1f58c6e` (자기 W2).
- 검증 코드 SHA `f8cc461f725340e0a0d4f992aa849288a200780f`; 이후 기록 커밋은 문서만 변경.

## 실제 변경·기여·재사용

Codex가 B 소유의 신규 발행 컨트랙트·실제 ABI·검사와 B 인계/개인 기록을 작성했습니다. W2 기관/키 저장소와 block helper의 내부 상속 접근만 열고 기존 권한 검사·공유 ABI를 유지했습니다. C/A/D 생산 코드와 기존 사용자 변경을 수정하지 않았습니다. 사람의 코드 승인·기여 비율은 대신 기록하지 않습니다.

W2 공동승인/키/정지, C의 공통 원본/서명 계약·두 Golden, OpenZeppelin EIP712/ECDSA/SafeCast와 기존 회귀를 재사용했습니다. 원본/보호 내용 전체는 체인에 넣지 않고 서명된 commitment를 보존합니다. 기관의 현재 키·문서 ID 소유·업무 nonce·시각/schema를 검증하고 최초 버전만 원자적으로 저장합니다. 발행키와 중계자의 msg.sender 권한을 분리합니다.

[과거 W3-B 기록](https://github.com/OriginProof-3web/OriginProof/blob/3ef1fd40943914c1450e8bc05047119ab7eabbc0/docs/portfolio/W3-B.md)은 고정 SHA로 보존하며 그 성과·리뷰/실제 연결을 이번 v5 완료로 합산하지 않습니다.

## 검증·실패·범위

Foundry **68 PASS**(기존48+신규20, fuzz 총5개 각512), Python **179 PASS/1 live SKIP**, Node hash·ABI/생성물·변경 파일 format·문서/diff 검사 통과입니다. macOS arm64, Python 3.13.14, solc 0.8.26, 내부 EVM·합성 데이터 기준입니다. 최초 fmt check의 assembly 줄바꿈은 재포맷해 통과했으며 기능 실패로 기록하지 않습니다.

두 템플릿의 원본 Python Golden은 합성 fixture 주소에 runtime을 etch해 기존 서명을 소비했습니다. 실제 RPC 배포/지갑이나 원본 bytes 내용의 사실성을 검증한 것이 아닙니다. 시각/서명/소유권/nonce·정지·키 교체·16필드 변조 거부·실패 상태 불변을 검사했습니다. 명령·상세 결과·ABI 재생성·인계는 [기존 인계 4.3절](../handoffs/v5_reuse_handoff.md#43-v5-w3-b-최초-버전-기관-서명-발행-2026-10-16)을 기준으로 사용합니다.

## 다음 작업·사실 확인

다음 버전·대체·철회는 W4이며 이번에 구현하지 않았습니다. B 실제 Adapter/manifest·C/A 원본/지갑 연결·D 독립 검사·G07·v2/consume 전체 회귀·공개 체인/성능은 남아 있습니다. 실제 W3 단계 완료로 표시하지 않습니다.

- 본인 기여/계약 확인·작성자 외 리뷰: 미확인.
- 선행 Draft PR: 기준 #64 → W1 #65 → W2 #66, 병합하지 않음.
- W3 PR/CI: 이 기록 이후 생성·조회 결과를 원격 PR 본문에 남기며 원격 CI 통과를 미리 주장하지 않음.
