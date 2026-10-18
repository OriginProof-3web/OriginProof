# 5.0 기능 기준의 기존 코드 재사용 인계

- 문서 버전: **1.0** · 작성/PR 상태 확인: **2026-10-15, 한국시간**
- 계획 기준: [개발 계획서 5.1](../development_plan.md) 3·4·11.3·15장, V5-Q08.
- 목적: 종료된 과거 PR의 코드를 재사용할 때 에이전트와 담당자가 같은 원본·범위·미완료를 확인하도록 합니다.
- 현재 상태(2026-10-16): **C 누적본·#50 일부 재사용과 C 신규 DB/API 독립 검사 반영 / A/B/D 실제 연결·소유자 리뷰 미확인**. 적용한 정확한 범위·검사·후속 PR은 [C 구현 기록](v5_c_implementation.md)을 확인합니다. 아래 원본별 전체 인계 완료를 대신하지 않습니다.
- GitHub [최초 통합 인계 댓글](https://github.com/OriginProof-3web/OriginProof/pull/56#issuecomment-6172682875)의 내용을 저장소 문서로 옮겼습니다. 이후 진행 상태는 이 문서에서 갱신하며 댓글의 과거 기록은 보존합니다.

## 1. 사용하는 방법과 완료 처리

1. 맡은 V5 작업과 관련된 아래 항목의 고정 SHA·경로·중복·전환 조건을 읽습니다.
2. 최신 개발 기준과 원본을 비교해 재사용할 코드·검사·데이터 경계를 정합니다. 과거 PR 전체를 순서대로 병합하거나 서버 서명/consume을 신규 공개 안내에 그대로 적용하지 않습니다.
3. 기존 역할 소유권에 따라 필요한 변경을 현재 개발 작업에 반영하고 후속 PR·적용 범위·실제 검증 SHA를 기록합니다.
4. 새 계약의 정상·거부·실패 사례와 필요한 구버전 회귀·실제 연결을 확인한 뒤에만 해당 범위의 인계를 완료 처리합니다. mock·단위 검사·과거 PASS를 새 실제 연결 성공으로 합산하지 않습니다.
5. 완료 항목은 아래 활성 목록에서 완료 기록으로 옮기고 반영 PR·검증 SHA/명령/결과·남은 한계를 남깁니다. 근거가 없으면 미확인으로 유지하며 원본 브랜치/커밋·자료를 삭제하지 않습니다. AGENTS·START_HERE에 항목별 진행 상태를 복제하지 않습니다.

## 2. 처리된 PR와 보존 원본

아래 9개 PR은 모두 **병합 없이 CLOSED**입니다. 종료는 코드 폐기·결함 해결·현재 개발본 반영을 뜻하지 않습니다. 원격 브랜치와 head가 그대로 존재함을 확인했습니다.

| 원본 PR | 보존 브랜치 | 고정 head | 5.0 재사용 상태 |
| --- | --- | --- | --- |
| [#39](https://github.com/OriginProof-3web/OriginProof/pull/39) | `phase/W1` | [`ab86892f1aedc14664e3129231225e79220b7394`](https://github.com/OriginProof-3web/OriginProof/tree/ab86892f1aedc14664e3129231225e79220b7394) | 후속 반영·검증 미확인 |
| [#54](https://github.com/OriginProof-3web/OriginProof/pull/54) | `codex/w2-a-acceptance-fixes` | [`de334ac2d1fc7d2bb2b8aa0e776b3b8d4d473999`](https://github.com/OriginProof-3web/OriginProof/tree/de334ac2d1fc7d2bb2b8aa0e776b3b8d4d473999) | 후속 반영·검증 미확인 |
| [#48](https://github.com/OriginProof-3web/OriginProof/pull/48) | `codex/w3-a-qr-followup` | [`76533198a4130a81d33917f6af08c7b6fa6188ff`](https://github.com/OriginProof-3web/OriginProof/tree/76533198a4130a81d33917f6af08c7b6fa6188ff) | 후속 반영·검증 미확인 |
| [#53](https://github.com/OriginProof-3web/OriginProof/pull/53) | `codex/admin-latest-functions` | [`2b350de60cac35ee10e242c95eae281e06ad18d7`](https://github.com/OriginProof-3web/OriginProof/tree/2b350de60cac35ee10e242c95eae281e06ad18d7) | 후속 반영·검증 미확인 |
| [#55](https://github.com/OriginProof-3web/OriginProof/pull/55) | `codex/w5-a-ui-completion` | [`56dbd82407e7d04cca97162aebbf276ec6a9f607`](https://github.com/OriginProof-3web/OriginProof/tree/56dbd82407e7d04cca97162aebbf276ec6a9f607) | 후속 반영·검증 미확인 |
| [#51](https://github.com/OriginProof-3web/OriginProof/pull/51) | `test/w2-d-browser-qa` | [`17f78e300b04aa9395fb20f6f76f5313d705db3d`](https://github.com/OriginProof-3web/OriginProof/tree/17f78e300b04aa9395fb20f6f76f5313d705db3d) | 후속 반영·검증 미확인 |
| [#43](https://github.com/OriginProof-3web/OriginProof/pull/43) | `feat/d-ai-extraction-safety` | [`c16de660914389ba8821612aa3d6c64708085185`](https://github.com/OriginProof-3web/OriginProof/tree/c16de660914389ba8821612aa3d6c64708085185) | 후속 반영·검증 미확인 |
| [#37](https://github.com/OriginProof-3web/OriginProof/pull/37) | `feat/w5-c-api-security` | [`9651062c9f36e124b76796278c996764678e1c77`](https://github.com/OriginProof-3web/OriginProof/tree/9651062c9f36e124b76796278c996764678e1c77) | 후속 반영·검증 미확인 |
| [#38](https://github.com/OriginProof-3web/OriginProof/pull/38) | `feat/w6-c-security-checks` | [`3ef1fd40943914c1450e8bc05047119ab7eabbc0`](https://github.com/OriginProof-3web/OriginProof/tree/3ef1fd40943914c1450e8bc05047119ab7eabbc0) | 후속 반영·검증 미확인 |

이미 병합한 기존 변경도 새 5.0 서비스 전체가 연결됐다는 뜻은 아닙니다.

| PR | 실제 반영 대상 | 병합 커밋 | 범위 |
| --- | --- | --- | --- |
| [#52](https://github.com/OriginProof-3web/OriginProof/pull/52) | `integration` | [`a178af08005b1b6d66907d8dec2e9887b41077cf`](https://github.com/OriginProof-3web/OriginProof/commit/a178af08005b1b6d66907d8dec2e9887b41077cf) | 문서·QA/실패 기록 |
| [#50](https://github.com/OriginProof-3web/OriginProof/pull/50) | `phase/W2` | [`a059a3283d5aaa9b2e673907723507086c86bc57`](https://github.com/OriginProof-3web/OriginProof/commit/a059a3283d5aaa9b2e673907723507086c86bc57) | 전송 전 저장 실패/취소의 nonce 예약 해제 |
| [#47](https://github.com/OriginProof-3web/OriginProof/pull/47) | `phase/W3` | [`69db3680ee8a2779a48e58ec775bd29009f7aa4c`](https://github.com/OriginProof-3web/OriginProof/commit/69db3680ee8a2779a48e58ec775bd29009f7aa4c) | 기존 W3 독립 QA |
| [#49](https://github.com/OriginProof-3web/OriginProof/pull/49) | `phase/W4` | [`374074744613b37ae91051c3f57a7c9222037506`](https://github.com/OriginProof-3web/OriginProof/commit/374074744613b37ae91051c3f57a7c9222037506) | 기존 W4 정책·상태 QA/D3 준비 |

[#56](https://github.com/OriginProof-3web/OriginProof/pull/56)은 **2026-10-15 01:48 한국시간**에 `integration`의 `33bc4f4e7456c5ef7c2df8c8bf09f8014e0169f8`로 **MERGED**됐으며 계획·지침·v5-shared-0.1 준비 계약을 담습니다. Registry/API/DB/브라우저 지갑 실제 구현·연결을 완료한 PR은 아닙니다. 새 통합 PR과 재사용 적용 완료의 근거는 아직 없습니다.
