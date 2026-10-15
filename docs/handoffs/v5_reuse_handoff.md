# 5.0 기능 기준의 기존 코드 재사용 인계

- 문서 버전: **1.0** · 작성/PR 상태 확인: **2026-10-15, 한국시간**
- 계획 기준: [개발 계획서 5.1](../development_plan.md) 3·4·11.3·15장, V5-Q08.
- 목적: 종료된 과거 PR의 코드를 재사용할 때 에이전트와 담당자가 같은 원본·범위·미완료를 확인하도록 합니다.
- 현재 상태: **PR 정리·원본 보존·인계 문서 작성 완료 / 새 5.0 반영·실제 연결·기능 검증 미확인**.
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

## 3. 활성 재사용 인계

### R39 — PR #39

- 상태: **후속 반영·검증 미확인**
- 작업: V5-W1-C 및 해당 영역의 후속 작업
- 담당/검토 경계(기존 소유권 기준): C 사용자님(@Jordi2801K) 통합 조율, A/B/D 해당 영역·검사 검토
- 재사용: 인증·기관 신청·두 유형 모델·Writer/Registry 경계·합성 QA·기여 기록의 기반
- 재사용: 기존 v1/v2 원본/서명/권한·상태 회귀와 W1 접근성/fixture 보완의 근거
- 중복/선행: 기반 구현 일부는 이후 phase와 #55의 누적본에도 있습니다. 최신 제품 소스와 비교하고 동일 변경을 중복 반영하지 않습니다.
- 전환/미완료: 옛 W1 완료·integration 승격을 새 5.0 통합 작업으로 대체했습니다. 종료로 과거 CHANGES_REQUESTED를 해결하거나 네 명의 확인·기능 완료를 소급 기록하지 않습니다.
- 주요 고정 원본: [apps/api/src/originproof_api/accounts.py](https://github.com/OriginProof-3web/OriginProof/blob/ab86892f1aedc14664e3129231225e79220b7394/apps/api/src/originproof_api/accounts.py), [apps/api/src/originproof_api/applications.py](https://github.com/OriginProof-3web/OriginProof/blob/ab86892f1aedc14664e3129231225e79220b7394/apps/api/src/originproof_api/applications.py), [packages/python/originproof_core/finals.py](https://github.com/OriginProof-3web/OriginProof/blob/ab86892f1aedc14664e3129231225e79220b7394/packages/python/originproof_core/finals.py), [docs/qa/w1-final-verification.md](https://github.com/OriginProof-3web/OriginProof/blob/ab86892f1aedc14664e3129231225e79220b7394/docs/qa/w1-final-verification.md)
- 종료·상세 인계 근거: [PR 댓글](https://github.com/OriginProof-3web/OriginProof/pull/39#issuecomment-6172386359)
- 후속 반영 PR / 검증 SHA·명령·결과: **미기록**

### R54 — PR #54

- 상태: **후속 반영·검증 미확인**
- 작업: V5-W2-A, V5-W4-A 및 관련 D 검사
- 담당/검토 경계(기존 소유권 기준): A 김형준님(@kimhyounjun), C/B API·체인 경계 검토, D 독립 재검증
- 재사용: 기관 신청·키 목록·활성화 UI, 세션/CSRF·고유 요청 ID·UNKNOWN/429 오류 처리
- 재사용: 접근성 보완과 컴포넌트·브라우저 회귀, 합성 QA 기록
- 중복/선행: 이 head는 #55에 포함됩니다. #55와 함께 전체 변경을 중복 적용하지 않습니다.
- 전환/미완료: 기존 서버 기관키·단일 운영자 활성화 UI는 5.0 기관 지갑·2-of-3 공동승인에 맞춰 변경합니다. A 자체 12 PASS는 #51의 D 독립 재검증이나 5.0 완료를 대신하지 않습니다.
- 주요 고정 원본: [apps/web/app/finals/page.tsx](https://github.com/OriginProof-3web/OriginProof/blob/de334ac2d1fc7d2bb2b8aa0e776b3b8d4d473999/apps/web/app/finals/page.tsx), [apps/web/app/finals/keys/page.tsx](https://github.com/OriginProof-3web/OriginProof/blob/de334ac2d1fc7d2bb2b8aa0e776b3b8d4d473999/apps/web/app/finals/keys/page.tsx), [apps/web/e2e/w2-live.spec.ts](https://github.com/OriginProof-3web/OriginProof/blob/de334ac2d1fc7d2bb2b8aa0e776b3b8d4d473999/apps/web/e2e/w2-live.spec.ts), [docs/portfolio/W2-A.md](https://github.com/OriginProof-3web/OriginProof/blob/de334ac2d1fc7d2bb2b8aa0e776b3b8d4d473999/docs/portfolio/W2-A.md)
- 종료·상세 인계 근거: [PR 댓글](https://github.com/OriginProof-3web/OriginProof/pull/54#issuecomment-6172635307)
- 후속 반영 PR / 검증 SHA·명령·결과: **미기록**

### R48 — PR #48

- 상태: **후속 반영·검증 미확인**
- 작업: V5-W3-A, V5-W4-A 및 관련 D 검사
- 담당/검토 경계(기존 소유권 기준): A 김형준님(@kimhyounjun), C 공개 조회 계약 검토, D QR/세션 검증
- 재사용: 공개 식별자 링크만 담는 QR 생성·PNG 저장, 오류 안내·비동기 교체 처리
- 재사용: 기존 공식 웹 디자인·컴포넌트 및 QR 생성/해독·새 세션 회귀
- 중복/선행: 이 head는 #53과 #55에 포함됩니다. 세 원본의 동일 변경을 중복 적용하지 않습니다.
- 전환/미완료: 신규 링크의 documentId·version과 조회/내용 비교 범위를 5.0 계약에 맞춥니다. 기존 QR에 원문·토큰·개인키를 넣지 않는 원칙을 유지합니다. 공개 체인/휴대폰 실기기 검증은 기존 결과에 포함되지 않습니다.
- 주요 고정 원본: [apps/web/official/components/business/ProofQr.tsx](https://github.com/OriginProof-3web/OriginProof/blob/76533198a4130a81d33917f6af08c7b6fa6188ff/apps/web/official/components/business/ProofQr.tsx), [apps/web/official/components/business/BusinessWorkspace.tsx](https://github.com/OriginProof-3web/OriginProof/blob/76533198a4130a81d33917f6af08c7b6fa6188ff/apps/web/official/components/business/BusinessWorkspace.tsx), [apps/web/e2e/proof-qr.spec.ts](https://github.com/OriginProof-3web/OriginProof/blob/76533198a4130a81d33917f6af08c7b6fa6188ff/apps/web/e2e/proof-qr.spec.ts), [apps/web/W3_QR_VALIDATION.md](https://github.com/OriginProof-3web/OriginProof/blob/76533198a4130a81d33917f6af08c7b6fa6188ff/apps/web/W3_QR_VALIDATION.md)
- 종료·상세 인계 근거: [PR 댓글](https://github.com/OriginProof-3web/OriginProof/pull/48#issuecomment-6172638414)
- 후속 반영 PR / 검증 SHA·명령·결과: **미기록**

### R53 — PR #53

- 상태: **후속 반영·검증 미확인**
- 작업: V5-W2-A~V5-W5-A의 적용 가능한 UI 작업
- 담당/검토 경계(기존 소유권 기준): A 김형준님(@kimhyounjun), B/C 서명·상태·Operation 경계, D 독립 UI 검사
- 재사용: official 화면·API client·QR·역할별 조회·오류·기존 Operation 복구 구조
- 재사용: 키 교체·철회·새 세션·권한·접근성의 기존 화면과 검사 자산
- 중복/선행: #48을 포함하고 이 head는 #55에 포함됩니다. #55의 누적본과 중복 적용하지 않습니다.
- 전환/미완료: 신규 기관키는 서버 생성 대신 지갑 서명을 사용하며 공동승인·문서 버전·현재 경고를 새 계약에 맞춥니다. 기존 수신자 consume은 레거시 호환 회귀로만 보존합니다. D3 브라우저 최종 연결·W4/5.0 전체 완료는 확인되지 않았습니다.
- 주요 고정 원본: [apps/web/official/components/business/BusinessWorkspace.tsx](https://github.com/OriginProof-3web/OriginProof/blob/2b350de60cac35ee10e242c95eae281e06ad18d7/apps/web/official/components/business/BusinessWorkspace.tsx), [apps/web/official/components/user/UserWorkspace.tsx](https://github.com/OriginProof-3web/OriginProof/blob/2b350de60cac35ee10e242c95eae281e06ad18d7/apps/web/official/components/user/UserWorkspace.tsx), [apps/web/official/admin-entry.tsx](https://github.com/OriginProof-3web/OriginProof/blob/2b350de60cac35ee10e242c95eae281e06ad18d7/apps/web/official/admin-entry.tsx), [docs/portfolio/W4-A.md](https://github.com/OriginProof-3web/OriginProof/blob/2b350de60cac35ee10e242c95eae281e06ad18d7/docs/portfolio/W4-A.md)
- 종료·상세 인계 근거: [PR 댓글](https://github.com/OriginProof-3web/OriginProof/pull/53#issuecomment-6172645357)
- 후속 반영 PR / 검증 SHA·명령·결과: **미기록**

### R55 — PR #55

- 상태: **후속 반영·검증 미확인**
- 작업: V5-W2-A~V5-W5-A 및 V5-W1-C의 재사용 통합 순서
- 담당/검토 경계(기존 소유권 기준): A 김형준님(@kimhyounjun) UI, C 통합·API 재사용 선정, B 체인/RPC, D 실패 재검증
- 재사용: official 디자인·화면·오류/세션·접근성·늦은 응답 차단·중복 요청 방지
- 재사용: 누적된 기존 API/DB/키/Operation 구현과 검사 중 5.0에서도 필요한 부분의 재사용 원본
- 중복/선행: #54·#53·#48 head를 포함하는 누적본입니다. 개별 수정 원본과 이 누적본 전체를 중복 적용하지 않습니다. 일부 기존 기반 코드는 #39의 보존 원본 및 phase 결과와도 겹칩니다.
- 전환/미완료: mixed G07 실패 원인/해결은 미확정이며 종료로 해결 처리하지 않습니다. 신규 기관 지갑·공동승인·document/version·공개 안내 검증 기준에 맞춰 후속 통합하고 새 실제 연결 검사가 필요합니다.
- 주요 고정 원본: [apps/web/official/components/user/UserWorkspace.tsx](https://github.com/OriginProof-3web/OriginProof/blob/56dbd82407e7d04cca97162aebbf276ec6a9f607/apps/web/official/components/user/UserWorkspace.tsx), [apps/web/official/components/business/BusinessWorkspace.tsx](https://github.com/OriginProof-3web/OriginProof/blob/56dbd82407e7d04cca97162aebbf276ec6a9f607/apps/web/official/components/business/BusinessWorkspace.tsx), [apps/web/W5_UI_VALIDATION.md](https://github.com/OriginProof-3web/OriginProof/blob/56dbd82407e7d04cca97162aebbf276ec6a9f607/apps/web/W5_UI_VALIDATION.md), [apps/api/src/originproof_api/finals_proofs.py](https://github.com/OriginProof-3web/OriginProof/blob/56dbd82407e7d04cca97162aebbf276ec6a9f607/apps/api/src/originproof_api/finals_proofs.py)
- 종료·상세 인계 근거: [PR 댓글](https://github.com/OriginProof-3web/OriginProof/pull/55#issuecomment-6172649943)
- 후속 반영 PR / 검증 SHA·명령·결과: **미기록**

### R51 — PR #51

- 상태: **후속 반영·검증 미확인**
- 작업: V5-W2-D 및 V5-W4-D/V5-W5-D의 적용 가능한 회귀
- 담당/검토 경계(기존 소유권 기준): D 여인준님(@yijun0330), A UI 후속, C 검토·통합
- 재사용: 격리된 실제 브라우저·새 세션·권한·UNKNOWN·접근성 QA와 안전한 준비 도구
- 재사용: 기존 연결 6 PASS / 수용 6 FAIL을 분리한 환경·실패·합성 화면 기록
- 중복/선행: 이번 종료는 QA 실행·소비 리뷰 승인을 뜻하지 않습니다. #54/#55의 UI 수정 원본과 함께 재사용 범위를 확인합니다.
- 전환/미완료: #54는 A 자체 수정·검사 근거이며 D 독립 갱신을 대신하지 않습니다. 과거 6 FAIL과 전체 D2 미완료를 종료 시 PASS로 바꾸지 않습니다. 5.0 공동승인·지갑 기준에 맞춘 QA를 추가하고 실제 연결에서 재실행합니다.
- 주요 고정 원본: [fixtures/finals/prepare_w2_browser_qa.py](https://github.com/OriginProof-3web/OriginProof/blob/17f78e300b04aa9395fb20f6f76f5313d705db3d/fixtures/finals/prepare_w2_browser_qa.py), [fixtures/finals/w2_browser_qa.spec.ts](https://github.com/OriginProof-3web/OriginProof/blob/17f78e300b04aa9395fb20f6f76f5313d705db3d/fixtures/finals/w2_browser_qa.spec.ts), [docs/qa/w2-d-browser.md](https://github.com/OriginProof-3web/OriginProof/blob/17f78e300b04aa9395fb20f6f76f5313d705db3d/docs/qa/w2-d-browser.md), [docs/qa/w2-d-browser-environment.json](https://github.com/OriginProof-3web/OriginProof/blob/17f78e300b04aa9395fb20f6f76f5313d705db3d/docs/qa/w2-d-browser-environment.json)
- 종료·상세 인계 근거: [PR 댓글](https://github.com/OriginProof-3web/OriginProof/pull/51#issuecomment-6172657098)
- 후속 반영 PR / 검증 SHA·명령·결과: **미기록**

### R43 — PR #43

- 상태: **후속 반영·검증 미확인**
- 작업: V5-W5-D/C/A의 AI 결과·확인·통합 검사
- 담당/검토 경계(기존 소유권 기준): D 여인준님(@yijun0330), C 확인/비교 계약·서버 검증, A 확인·정정 UI
- 재사용: 기존 provider·prompt의 모호한 값 null·확인 필요 안내와 오추출/삽입 지시 안전성 회귀
- 재사용: AI 후보·내용 비교·발행 검증을 분리하는 인계 계약과 합성 평가 자료
- 중복/선행: 기존 승인·검사 이력은 보존하며 이번 종료를 전체 AI flow 또는 5.0 승인으로 취급하지 않습니다.
- 전환/미완료: 현재 헤더는 확인/grounding 강제가 아니며 이 한계는 유지합니다. 입력 선정은 회의 후 확정, Decisions API는 현 개발 범위 밖입니다. 구 v1/v2 판정을 조용히 바꾸지 않고 신규 5.0 응답·확인·검증 경계는 관련 원본과 검사로 연결합니다.
- 주요 고정 원본: [services/analyzer/src/originproof_analyzer/service.py](https://github.com/OriginProof-3web/OriginProof/blob/c16de660914389ba8821612aa3d6c64708085185/services/analyzer/src/originproof_analyzer/service.py), [services/analyzer/src/originproof_analyzer/prompts/card_payment_notice_v4.md](https://github.com/OriginProof-3web/OriginProof/blob/c16de660914389ba8821612aa3d6c64708085185/services/analyzer/src/originproof_analyzer/prompts/card_payment_notice_v4.md), [services/analyzer/tests/test_extraction_safety.py](https://github.com/OriginProof-3web/OriginProof/blob/c16de660914389ba8821612aa3d6c64708085185/services/analyzer/tests/test_extraction_safety.py), [docs/handoffs/analyzer-confirmation-contract.md](https://github.com/OriginProof-3web/OriginProof/blob/c16de660914389ba8821612aa3d6c64708085185/docs/handoffs/analyzer-confirmation-contract.md)
- 종료·상세 인계 근거: [PR 댓글](https://github.com/OriginProof-3web/OriginProof/pull/43#issuecomment-6172660336)
- 후속 반영 PR / 검증 SHA·명령·결과: **미기록**

### R37 — PR #37

- 상태: **후속 반영·검증 미확인**
- 작업: V5-W1-C, V5-W3-C~V5-W6-C의 적용 가능한 기반
- 담당/검토 경계(기존 소유권 기준): C 사용자님(@Jordi2801K), B Adapter/indexer, A 응답 소비, D 장애·연결 검사
- 재사용: Operation 멱등성·UNKNOWN 재조회·감사/pagination·현재 체인 대조·readiness·안전한 seed
- 재사용: projection/scanner의 중복 이벤트·checkpoint·복구와 API/Compose/보안·실패 회귀
- 중복/선행: #38은 이 head를 포함하는 후속 원본입니다. 두 PR의 공통 변경을 중복 적용하지 않습니다.
- 전환/미완료: 기존 서명/ABI·Proof lifecycle과 projection migration은 신규 기관 지갑·문서 버전·공동승인 이벤트에 맞춰 변경합니다. 기존 projection을 현재 유효성의 권위로 쓰지 않는 원칙을 유지합니다. 운영 DB에 migration/reset을 실행하지 않습니다.
- 주요 고정 원본: [apps/api/src/originproof_api/operations.py](https://github.com/OriginProof-3web/OriginProof/blob/9651062c9f36e124b76796278c996764678e1c77/apps/api/src/originproof_api/operations.py), [apps/api/src/originproof_api/security.py](https://github.com/OriginProof-3web/OriginProof/blob/9651062c9f36e124b76796278c996764678e1c77/apps/api/src/originproof_api/security.py), [apps/api/src/originproof_api/projection.py](https://github.com/OriginProof-3web/OriginProof/blob/9651062c9f36e124b76796278c996764678e1c77/apps/api/src/originproof_api/projection.py), [services/indexer/src/originproof_indexer/projection.py](https://github.com/OriginProof-3web/OriginProof/blob/9651062c9f36e124b76796278c996764678e1c77/services/indexer/src/originproof_indexer/projection.py)
- 종료·상세 인계 근거: [PR 댓글](https://github.com/OriginProof-3web/OriginProof/pull/37#issuecomment-6172676579)
- 후속 반영 PR / 검증 SHA·명령·결과: **미기록**

### R38 — PR #38

- 상태: **후속 반영·검증 미확인**
- 작업: V5-W6-C/B/D 및 5.0 보안·복구 검증
- 담당/검토 경계(기존 소유권 기준): C 사용자님(@Jordi2801K), B Writer/체인 복구, D 독립 복원·장애 검사
- 재사용: 제출/복구 참조 검증·UNKNOWN 유지·프로세스 종료/재시작·DB dump/restore·멱등성 보존 검사
- 재사용: seed credential/FIFO·권한 보호, dependency audit·CI·복구 runbook의 적용 가능한 보완
- 중복/선행: #37 head를 포함합니다. #37과의 공통 기반을 한 번만 반영하고 #38 고유 보완을 별도로 추적합니다.
- 전환/미완료: 서버 기관키 백업/복원은 레거시 경로에 한정하고 신규 기관 지갑키를 서버가 보관하지 않습니다. 과거 lockfile을 일괄 덮어쓰지 않고 현재 의존성과 적용 여부를 확인합니다. 실제 복구·신규 서명/nonce/버전/이벤트 회귀는 후속 통합 SHA에서 검증합니다.
- 주요 고정 원본: [apps/api/src/infrastructure/blockchain/writer.py](https://github.com/OriginProof-3web/OriginProof/blob/3ef1fd40943914c1450e8bc05047119ab7eabbc0/apps/api/src/infrastructure/blockchain/writer.py), [apps/api/tests/test_w6_c_security.py](https://github.com/OriginProof-3web/OriginProof/blob/3ef1fd40943914c1450e8bc05047119ab7eabbc0/apps/api/tests/test_w6_c_security.py), [scripts/ci/test_w6_c_recovery.py](https://github.com/OriginProof-3web/OriginProof/blob/3ef1fd40943914c1450e8bc05047119ab7eabbc0/scripts/ci/test_w6_c_recovery.py), [docs/api/w6_c_recovery_runbook.md](https://github.com/OriginProof-3web/OriginProof/blob/3ef1fd40943914c1450e8bc05047119ab7eabbc0/docs/api/w6_c_recovery_runbook.md)
- 종료·상세 인계 근거: [PR 댓글](https://github.com/OriginProof-3web/OriginProof/pull/38#issuecomment-6172679826)
- 후속 반영 PR / 검증 SHA·명령·결과: **미기록**

## 4. 공통 미완료와 경계

- **G07:** mixed RPC/reorg·재시작 뒤 Reader UNAVAILABLE 원인/해결은 미확정입니다. B/C가 원인을 확인하고 D가 같은 후속 제품 SHA에서 재검사합니다. fresh 18 PASS와 mixed 17 PASS/1 FAIL을 구분합니다.
- **기관 권한/서명/문서:** 신규 2-of-3·기관 지갑 EIP-712·문서 소유/버전·nonce/deadline을 새 원본 모델/ABI/DB/웹에서 검증합니다. 과거 Proof ID를 documentId로 이름만 바꾸거나 과거 서명을 신규 발행 사실로 해석하지 않습니다.
- **구버전 보존:** 기존 v1/v2 서명·binding·consume·자료 읽기와 해당 회귀를 유지합니다. 서버 기관키 백업은 레거시 한정이며 신규 기관키를 서버에 수집/보관하지 않습니다.
- **입력/AI:** 입력 지원은 팀 회의 후 확정하며 Decisions API는 현재 개발 범위 밖입니다. 과거 입력 코드의 존재나 높은 confidence를 입력 선정·grounding 성공으로 취급하지 않습니다.
- **승인/기여:** PR 종료·문서 기록·Codex 기술 검토와 사람의 개인 기여 확인·소유자/소비 리뷰·단계 완료를 구분합니다. 담당자 이름은 기존 역할 기준이며 실제 착수/확인까지 완료로 표시하지 않습니다.

## 5. 완료 기록

현재 새 5.0 코드 반영·실제 연결·회귀 검증이 확인되어 활성 목록에서 완료로 옮긴 항목은 없습니다. 완료되면 항목 ID·재사용 범위·반영 PR·검증 SHA/명령/결과·한계를 여기에 남깁니다. 앞선 네 PR 병합은 2절의 과거 변경 반영 기록으로 구분합니다.
