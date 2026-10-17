# W1 / B / 여하민 — V5-W1-B 계약 검토·독립 검사

- GitHub 계정: `@hamin1228`; 작업일 2026-10-16 (W1은 개발 단계).
- 상태: 부분 완료 — 계약 차이 검토·독립 서명 검사 완료, C/A/D 소비 검토·실제 연결·단계 완료 대기.
- 브랜치: `codex/v5-w1-b-contract-review`; 시작 SHA `9feec138bf3d6d8a379b211583f92db1716e54f2`.
- 기준: 계획서 5.1 / 로컬 v5-shared-0.1, C Draft 0.2는 비교 원본으로만 사용.
- PR: 미생성, push 미실행. 새 단계 PR 대상은 C와 조율 예정이며 과거 phase는 보존.

## 과거 기록과 재사용

이 작업 폴더에 없던 [과거 W1-B 기록](https://github.com/OriginProof-3web/OriginProof/blob/ab86892f1aedc14664e3129231225e79220b7394/docs/portfolio/W1-B.md)은 고정 원본으로 보존합니다. 그 문서의 기존 성과·D 근거·검사·미확인을 이번 v5 완료로 바꾸지 않습니다. 기존 Registry·C 준비 인터페이스·생성 Golden·OpenZeppelin ECDSA와 Foundry 도구를 재사용했습니다. 과거 PR 전체 재병합이나 C 소스 복사는 하지 않았습니다.

## 실제 결과·기여·판단

Codex가 B 범위에서 기존 Registry/Reader/projection과 신규 계약 차이를 검토하고 Solidity 서명 변조/도메인/제안 ID/비정상 서명/fuzz 검사 7개를 추가했습니다. C 고정 head의 ABI/서명/Golden 동일성과 WalletRegistry 소비 경계를 대조했습니다. 사람의 코드 작성·승인·기여 비율이나 C/A/D 확인은 대신 주장하지 않습니다.

상세 전환표·실행 명령·결과·실제 연결 한계·B-C01~03은 [재사용 인계 4.1절](../handoffs/v5_reuse_handoff.md#41-v5-w1-b-계약-검토독립-검사-2026-10-16)을 기준으로 사용합니다. 같은 계약 사본을 만들지 않았습니다. 기존 승인자 조회 ABI 부재·승인 count/주소 목록·UNKNOWN 검색과 배포 식별은 후속 설계/소비 검토 항목입니다.

검증: Foundry 21 PASS(기존 Registry 10/Golden 11, fuzz 각 512회), Python wallet 24 PASS, Node hash·생성물 보존·변경 파일 format·diff/링크 확인. macOS arm64, Python 3.13.14, solc 0.8.26, 로컬 Foundry offline/합성 fixture 기준입니다. 성능은 미측정입니다. 검증한 코드 커밋과 문서 최종 커밋은 별도로 아래에 남깁니다.

## 남은 작업과 사실 확인

새 Registry 구현, 실제 Adapter/manifest·API/DB·브라우저/지갑, 독립 소비 리뷰는 후속입니다. G07은 미해결이고 SG01~16은 NOT_EXECUTED입니다. W1 전체·재사용 항목 전체 완료나 실제 연결 성공으로 기록하지 않습니다. 입력 선정/Decisions API 범위를 변경하지 않았습니다.

- 본인 기여/계약 확인: 미확인.
- 작성자 외 리뷰: 미확인.
- 원격 PR/CI: 이번 작업에서 미생성·미실행.

- 검증한 코드 SHA: `dee70526af24c0878f00bac322d6670c97e5e427` (로컬, 원격 미공유).
- 이후 문서 최종 SHA: 이 파일을 기록한 문서 커밋의 Git 이력으로 확인하며 검사 코드 SHA와 구분합니다.
