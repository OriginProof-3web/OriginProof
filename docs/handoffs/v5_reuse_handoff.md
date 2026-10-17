# 5.0 기능 기준의 기존 코드 재사용 인계

- 문서 버전: **1.1** · 최초 작성/PR 상태 확인: **2026-10-15, 한국시간** · B W1/W2/W3/W4 검토 추가: **2026-10-16, 한국시간**
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

최초 작성 당시 [#56](https://github.com/OriginProof-3web/OriginProof/pull/56)은 OPEN/Draft였습니다. 2026-10-16 fetch/조회에서는 integration에 MERGED이며 병합 SHA는 `33bc4f4e7456c5ef7c2df8c8bf09f8014e0169f8`입니다. 계획·지침·v5-shared-0.1 준비 계약 반영이며 Registry/API/DB/브라우저 지갑 실제 연결 완료를 뜻하지 않습니다. 아래 과거 인계 상태와 후속 B 검토를 구분합니다.

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

## 4.1 V5-W1-B 계약 검토·독립 검사 (2026-10-16)

- 담당: B 여하민님 `@hamin1228`; Codex가 비교·검사·기록을 보조했습니다. 사람의 소유자 승인과 C/A/D 리뷰는 미확인입니다.
- 상태: **계약 차이 검토·독립 서명 검사 완료 / 후속 설계·소비자 리뷰·실제 연결 대기**. W1 단계 완료나 R39/R37/R38/R55 전체 인계 완료가 아닙니다.
- 브랜치: `codex/v5-w1-b-contract-review`; 시작 기준 `9feec138bf3d6d8a379b211583f92db1716e54f2` (integration `33bc4f4` + 로컬 기여 보존).
- 과거 phase/W1~W4는 보존합니다. 새 v5 단계 통합 브랜치가 정해질 때 PR 대상을 C와 조율하며 과거 phase를 다시 전진시키지 않습니다. 원격 push/PR은 이번 범위에서 미실행입니다.
- 로컬 기준은 계획서 5.1·v5-shared-0.1입니다. C 비교 원본은 [#63의 고정 head](https://github.com/OriginProof-3web/OriginProof/tree/6e0e924c77e9a5b83a8522df4d3cfdc797e8822c), 계약 **v5-shared-0.2**이며 미병합 Draft 소비 계약으로만 대조했습니다. 다른 담당 브랜치를 병합하거나 0.2로 로컬 버전을 올리지 않았습니다.

### 기존 구현과 신규 계약의 전환표

| 영역 | 기존/재사용 | 신규 경계·필수 검사 | 작업 |
| --- | --- | --- | --- |
| 기관 권한 | IssuerRegistry의 상태 검사·실패 사례 | 서로 다른 고정 승인자 3명 중 2명; 단독 등록/재활성화·중복/만료 거부, 배포자 우회 없음 | W2-B / V5-F02~03 |
| 키 | IssuerKeyRegistry·구배포 조회/검사 | KeyProof 일회성·issuer/signer 고정; 등록/교체/사고 block; 구키 신규 발행 차단과 과거 정상 서명 구분 | W2/W4-B / V5-F05,09 |
| 서명 | 원본 canonical JSON·Golden·OpenZeppelin ECDSA | Publish/Revoke/KeyProof·domain·알고리즘/schema·nonce/deadline; 서명 검증과 실제 nonce 소비/만료 거부는 별도 | W1/W3-B / V5-F04~05 |
| 문서 | 과거 ProofStatusRegistry는 고정 SHA의 레거시 원본 | documentId 소유 고정·최신+1·원자적 대체·철회 후 구버전 미복구; 신규 공개 안내에 consume 없음 | W3/W4-B / V5-F06,08,19 |
| Reader/Writer | RPC 오류 분리·기존 Operation/UNKNOWN·manifest 자산 | 기존 issuerStatus/keyStatus selector·getKey 반환 해석을 새 ABI에 재사용하지 않음; 새 WalletRegistry Adapter와 배포 식별 | W3/W5-B / V5-F12~13 |
| Indexer | 이벤트 중복·checkpoint·명시적 reorg 회복 검사 | 현재 저장 키에는 계약/배포 구분이 없음. 새 이벤트·배포 분리와 canonical 상태 직접 대조 필요 | W5/W6-B / V5-F13 |

R39(`ab86892`), R37(`9651062`), R38(`3ef1fd4`), R55(`56dbd82`)는 앞선 고정 원본을 사용합니다. R38의 R37 포함과 R55의 A 누적 중복을 유지하고 과거 PR 전체를 재병합하지 않습니다. 기존 로컬 bytes Reader·SQLite projection·검사는 baseline에서 보존돼 있습니다. 현재 작업본에 없는 Writer/ProofStatusRegistry/consume 전체는 과거 원본을 참조하며 이번 W1 검사로 실행 완료를 주장하지 않습니다.

### C 소비 계약 대조와 후속 설계 항목

고정 C head의 [WalletRegistry port](https://github.com/OriginProof-3web/OriginProof/blob/6e0e924c77e9a5b83a8522df4d3cfdc797e8822c/packages/python/originproof_core/wallet_ports.py)와 [실행 API 인계](https://github.com/OriginProof-3web/OriginProof/blob/6e0e924c77e9a5b83a8522df4d3cfdc797e8822c/docs/api/v5_c_runtime.md)를 읽었습니다.

- 공유 Solidity 인터페이스·커밋 ABI·Python wallet_signatures 원본은 로컬 0.1과 C 0.2가 byte 동일합니다. Golden도 revision을 제외한 domain/message/digest/signature/proposal 전체가 동일합니다. 0.2의 Operation 오류·분석 참조/제약 추가를 새로운 서명 규격으로 해석하지 않습니다.
- `issuer/key/document/proposal`은 같은 canonical chain/contract/blockNumber/hash 근거를 반환해야 합니다. `getIssuer` 외 별도 nonce 조회를 포함한 RPC 호출은 동일 조회 위치로 고정합니다. 0 block sentinel은 port의 선택 block=None으로 변환하며 과거 키 이력을 보존합니다.
- `transaction/find_transaction`은 실제 calldata 해독·sender·canonical receipt·필요 이벤트/현재 상태를 검증합니다. intent echo나 hash 존재만으로 CONFIRMED를 반환하지 않습니다. `find_transaction`은 검색만 하며 재전송하지 않습니다.
- REACTIVATE는 ABI상 전 필드 0의 KeyProof와 빈 signature `0x`입니다. API의 선택 null을 ABI null로 넣지 않습니다. 철회 확정은 실제 REVOKED 상태가 필요합니다.
- **B-C01 승인자 확인:** port의 `is_approver(address)`에 대응하는 조회 함수가 준비 ABI에 없습니다. 고정 승인자 manifest/검증된 배포 근거로 확인할지 additive getter를 둘지 C/B가 연결 전에 정해야 합니다. 이번에는 ABI를 임의 변경하지 않았습니다.
- **B-C02 승인자 목록:** getProposal은 승인 수만 반환하지만 C ProposalView는 주소 목록을 소비합니다. ProposalApproved 이벤트의 중복 없는 canonical replay/조회 block 일치·count 대조가 필요합니다. 이벤트 복원/검색 범위는 B Adapter에서 정의하고 C와 확인합니다.
- **B-C03 UNKNOWN/배포:** find_transaction의 검색 시작 block·로그/nonce 범위·RPC 불가 결과와 새 manifest/확정 기준은 B 구현과 C Operation 복구 검토가 필요합니다. G07과 신규 ABI 실제 연결은 미해결입니다.

### 독립 검사와 근거

검증한 코드 SHA: `dee70526af24c0878f00bac322d6670c97e5e427` (로컬 커밋, 원격 미공유). 이후 기록 커밋은 문서만 변경합니다. 검사 대상은 Solidity Golden 검사의 W1 보강본이며 생성 fixture는 수정하지 않았습니다. [개인 기록](../portfolio/W1-B.md)에 과거 기여와 이번 범위를 구분합니다.

| 실행 | 결과 | 의미·한계 |
| --- | --- | --- |
| `forge test --root packages/contracts --offline` | **21 PASS**, 0 FAIL/SKIP | 기존 Registry 10 + Golden 11(기존 4/신규 7). 두 fuzz 각각 512회. 새 Registry 상태/실제 지갑 검사는 아님 |
| `UV_PROJECT_ENVIRONMENT=.uv-venv uv run --locked --all-packages --all-groups pytest -q packages/python/tests/test_wallet_contract.py` | **24 PASS** | Python 모델/서명·기존 생성 ABI 검사 |
| `node scripts/ci/check_wallet_browser_hashes.mjs` | PASS | 두 템플릿 원본·보호 필드 hash, 실제 브라우저 지갑 아님 |
| `make generate` 및 생성물 diff | PASS, 생성물 변경 없음 | Schema/TypeScript/예정 OpenAPI·ABI·구/신규 Golden·합성 예시 보존 |
| 변경 Solidity format·문서 링크·diff·사용자 원본 hash | PASS | 사용자 파일 5개 상태/내용 보존 |

신규 검사는 Publish 두 템플릿의 16필드, Revoke 8필드, KeyProof 6필드를 각각 단독 변조해 기존 서명자의 불일치를 확인합니다. 제안 ID의 chain/address/7필드와 EIP domain name/version 변경, high-s·잘못된 v·잘못된 길이 거부, uint256 nonce/uint64 deadline fuzz를 추가했습니다. 만료 시각 비교·nonce의 원자적 소비·2-of-3 실행은 Registry가 없어 검증하지 않았습니다.

SG01~16은 계속 NOT_EXECUTED입니다. 실제 Registry 배포/receipt·신규 DB/Adapter·브라우저·v2/consume 전체 회귀·G07 재현·공개 체인·유료 AI·C Draft CI/사람 리뷰는 이번 미실행입니다. 입력 종류는 회의 후 결정하고 Decisions API는 범위 밖입니다.

## 4.2 V5-W2-B 공동승인·키 증명·정지 독립 구현 (2026-10-16)

- 담당: B 여하민님 `@hamin1228`, Codex 구현·검사 보조. 상태: **W2 Contract 독립 구현·검사 완료 / 배포·Adapter·C/A/D 실제 연결·작성자 외 리뷰 대기**. W2 단계 완료가 아닙니다.
- 브랜치: `codex/v5-w2-b-governance`; 시작 SHA `c2111e379889d8550aa6ff893d44f576fb78189a` (자기 W1 준비 결과). 구현 `fa333c699d33a223b0d00d97ea353a29fe058f75`; Golden 교차 검사를 포함한 최종 검증 코드 **`0f240dbd2ee42c059e26e4bdbb3d0dc843858fd7`**. 이후 기록 커밋은 문서만 변경합니다.
- 범위: B의 Contract·컴파일 ABI·Foundry 검사와 인계/기여 기록만 수정했습니다. C API/모델·A 웹·D 분석기, 기존 사용자 변경·구배포·과거 phase는 변경하지 않았습니다. 원격 push/PR·새 환경 배포는 미실행입니다.

### 산출물과 동작

- [OriginProofWalletGovernance.sol](../../packages/contracts/src/OriginProofWalletGovernance.sol)은 **공유 Registry의 W2 부분 구현**입니다. 전체 IOriginProofWalletRegistry를 구현했다고 선언하지 않습니다. 발행/철회/문서/업무 nonce 함수는 아직 없으며 호출하면 성공하지 않습니다. 이 산출물을 새 발행 Registry로 연결하지 않습니다.
- [실제 컴파일 ABI](../../packages/contracts/abi/OriginProofWalletGovernance.json)는 W2의 propose/approve/suspendIssuer/governanceNonce/getIssuer/getKey/getProposal 7개 함수와 4개 이벤트가 기존 준비 ABI와 완전히 같습니다. 상속한 OpenZeppelin EIP712의 표준 domain 조회·오류/생성자는 실제 ABI에 포함됩니다. isApprover·권한 변경·업그레이드·배포자 우회 함수는 추가하지 않았습니다. 공유 인터페이스/ABI·모델·서명·Golden 버전은 그대로입니다.
- 배포 생성자에서 서로 다른 0이 아닌 승인자 3명을 고정합니다. 생성자는 추가 관리자가 아니며 세 주소 중 하나일 때만 동일한 한 표를 갖습니다. 승인자 교체/업그레이드 경로는 없습니다.
- REGISTER/ROTATE 제안 생성은 승인으로 세지 않습니다. 기관·새 signer·application/challenge·만료에 묶인 EIP-712 KeyProof를 검증하고 challenge를 한 번 소비합니다. domain은 실제 chain/address, OriginProof/1이며 low-s·65 bytes·v=27/28을 검사합니다.
- 제안은 chain/address와 모든 proposal 필드로 고정됩니다. 서로 다른 승인자 2명의 두 번째 승인에서만 실행·기관/키 이력·governance nonce 전이가 원자적으로 일어납니다. 중복/만료/같은 nonce 경쟁·이미 실행된 제안은 거부합니다. 두 번째 승인 중 실패하면 승인 수와 상태·nonce가 함께 되돌아갑니다.
- 긴급 정지는 승인자 1명 또는 해당 기관의 현재 키만 수행합니다. OTHER/ABUSE_REPORT/KEY_COMPROMISE hash만 받습니다. 최초 정지는 governance nonce를 증가시켜 정지 전 제안을 무효화합니다. 반복 정지로 복구 제안 nonce를 계속 소모하지 않습니다. 이미 정지 중 새로 발견한 키 사고는 compromiseBlock을 기록하고 기존 재활성화 제안의 실행도 차단합니다.
- 키 교체는 이전 registered/retired/compromise block을 보존하고, 정지 상태를 자동 해제하지 않습니다. keyId는 전역 재사용 불가이며 같은 기관에서 이미 사용한 signer 주소도 새 keyId로 다시 활성화하지 않습니다. 사고 키의 재활성화는 거부하고 새 키 공동 교체 후 공동 재활성화가 필요합니다. REACTIVATE의 proof는 전부 0이고 signature는 빈 bytes이며 현재 키/주소/메타데이터를 바꿀 수 없습니다.
- 키 이력의 0 block은 미등록 sentinel이므로 block 0 실행은 거부하고, block은 SafeCast로 uint64 범위를 확인합니다. 정상 배포/이벤트 block은 새 manifest와 함께 소비해야 합니다.

### 기존 검사·생성물과 결과

[Foundry 검사](../../packages/contracts/test/OriginProofWalletGovernance.t.sol)에 정상·거부·재전송·시각 경계·동시 nonce 경쟁·실패 원자성·키 사고 복구·이벤트 재구성·fuzz를 추가했습니다.

| 검사 | 실제 결과·범위 |
| --- | --- |
| `forge test --root packages/contracts --offline` | **48 PASS / 0 FAIL / 0 SKIP**. 기존 Registry 10 + 공유 Golden 11 + W2 27. W2의 승인자 쌍/비승인자와 기존 2개 fuzz 각각 512회 |
| 기존 Python 생성 Golden 직접 소비 | 위 27개 중 1개. fixture의 합성 주소에 컨트랙트 runtime을 etch하고 chain/time을 고정하여 원본 Python 서명·제안 ID로 2-of-3 활성화 성공. 실제 RPC 배포/지갑 검사가 아님 |
| Python 공유 계약 | `UV_PROJECT_ENVIRONMENT=.uv-venv uv run --locked --all-packages --all-groups pytest -q packages/python/tests/test_wallet_contract.py` **24 PASS** |
| 브라우저 hash 교차 검사 | `node scripts/ci/check_wallet_browser_hashes.mjs` PASS, 두 합성 템플릿. 실제 브라우저 지갑 서명 아님 |
| 생성 일관성 | `make generate` 후 기존 Schema/TS/예정 OpenAPI·공유 ABI·구/신규 Golden·예시 diff 없음. 신규 ABI는 out artifact와 JSON 동일·공유 7함수/4이벤트 동일 |
| 변경 파일 품질·보존 | 두 Solidity format·문서 내부 링크·diff 검사 통과. 사용자 원본 5개 상태/내용 hash 동일. 의존성/lockfile 변경 없음 |

신규 ABI 재생성은 저장소 루트에서 다음 명령을 사용합니다. forge 설치 위치에 맞춰 PATH를 설정하며 공유 ABI exporter나 C 생성기를 수정하지 않습니다.

```sh
forge inspect --root packages/contracts --offline OriginProofWalletGovernance abi --json > packages/contracts/abi/OriginProofWalletGovernance.json
```

### 소비자 인계와 남은 경계

B-C01은 선택한 기존 ABI를 유지하므로 실제 is_approver 확인을 위한 고정 승인자 constructor/배포 근거·manifest 검증이 후속입니다. B-C02는 ProposalApproved의 proposalId/approver/count와 두 번째 ProposalExecuted 이벤트를 검사했습니다. canonical block 고정·이벤트 replay·getProposal count와 주소 목록 대조를 하는 실제 Adapter는 아직 없습니다. B-C03 UNKNOWN 검색·새 배포 식별과 G07은 미해결입니다.

API가 W2 artifact에 nextNonce/document 등을 호출하거나 readiness 성공으로 처리해서는 안 됩니다. W3의 publish/업무 nonce, W4의 버전/철회가 추가된 실제 통합 Registry 및 새 manifest/Adapter 준비 뒤 C와 연결합니다. 이번 작업은 C Draft 0.2와 기존 준비 ABI의 W2 부분에 대한 B 구현이지 C의 API/DB나 A/D 동작을 검증한 것이 아닙니다.

실제 RPC/receipt·API/DB·브라우저 지갑·공개 체인·배포/가스 실측·D 독립 QA·구 v2/consume 전체 회귀·G07 재현은 미실행입니다. SG01~16의 공유 실행 상태는 그대로 NOT_EXECUTED이며 이번 단위 검사 결과로 일괄 PASS로 바꾸지 않습니다. [W2 B 개인 기록](../portfolio/W2-B.md)에 과거 기여와 이번 결과를 구분합니다. W3 기능은 이번에 시작하지 않았습니다.

## 4.3 V5-W3-B 최초 버전 기관 서명 발행 (2026-10-16)

- 담당 B `@hamin1228`, Codex 구현·검사 보조. **Contract 독립 구현·검사 완료 / 실제 배포·Adapter/API/DB·지갑·작성자 외 리뷰 대기**입니다. W3 단계 전체 완료가 아닙니다.
- 브랜치 `codex/v5-w3-b-publication`, 시작 `5f91ac8e3405ac2f3bbe9ae19e15b81dd1f58c6e` (자기 W2 결과).
- 검증 코드 **`f8cc461f725340e0a0d4f992aa849288a200780f`**. 이후 인계 커밋은 문서만 변경합니다.
- 선행 공유: [기준 #64](https://github.com/OriginProof-3web/OriginProof/pull/64) → [W1 #65](https://github.com/OriginProof-3web/OriginProof/pull/65) → [W2 #66](https://github.com/OriginProof-3web/OriginProof/pull/66). 모두 Draft이며 승인/병합·단계 완료를 뜻하지 않습니다. 착수 때 #66의 python-quality/contracts SUCCESS를 확인했습니다. 과거 문서의 push/PR 미실행 표기는 해당 기록 시점이며 이 절에서 후속 공유와 구분합니다.

### 실제 변경과 계약

[OriginProofWalletRegistry.sol](../../packages/contracts/src/OriginProofWalletRegistry.sol)은 W2 권한 관리를 상속하고 `publish`, `nextNonce`, `latestVersion`, `getDocument`를 추가합니다. W2의 기관/키 저장소와 block 변환 helper만 private→internal로 열었으며 외부 W2 ABI와 권한 동작은 유지합니다. W2 PR 자체 브랜치는 변경하지 않습니다.

1. Publish action=1, 지원 내용/서명 schema, SHA-256 알고리즘 코드 1, 0이 아닌 원본/보호 hash를 검사합니다. 보호 필드/원본 bytes 자체는 체인에 제출하지 않으며 실제 내용과 hash의 일치는 C/A가 별도로 재계산합니다. 컨트랙트 서명 성공을 원문의 사실성으로 해석하지 않습니다.
2. 공유 JSON 정수 범위와 `issuedAt < deadline <= expiresAt`, `현재 시각 < deadline`을 검사합니다. issuedAt은 서명된 자기 선언 시각이며 과거 발행 권한의 근거로 삼지 않습니다. 실제 발행 시각·block은 별도 기록합니다.
3. 등록·ACTIVE 기관과 현재 keyId/signer·기관 소유·등록/미교체/비사고 키를 확인합니다. msg.sender는 중계자일 수 있으며 기관 업무 서명을 대신하지 않습니다.
4. `documentId = keccak256(abi.encode(issuerId, docKey))`, 기관별 정확한 다음 업무 nonce와 최초 version=1·미등록 문서를 확인합니다. 같은 기관에서도 기존 문서 덮어쓰기/새 버전은 아직 허용하지 않습니다.
5. 실제 chain/address의 OriginProof/1 EIP-712로 16개 필드 전체를 검증합니다. 서명은 65-byte·v27/28·low-s이며 등록 기관의 현재 signer여야 합니다.
6. 성공 시에만 불변 문서 버전·publishedAt/publishedBlock을 저장하고 업무 nonce를 하나 소비한 뒤 DocumentPublished를 기록합니다. governance nonce는 발행으로 변경하지 않습니다. 실패 요청은 문서/nonce를 변경하지 않습니다.

getDocument는 없는 문서/버전을 UnknownDocument로 거부합니다. latestVersion은 미등록 시 0, 등록 시 1입니다. 저장 state=1은 ACTIVE이고 기간 만료/기관 정지·키 사고 경고는 조회 시각/기관·키 이력과 함께 소비해야 합니다. 정상 키 교체 뒤에도 과거 문서의 keyId/hash/기록은 보존됩니다.

[실제 W3 ABI](../../packages/contracts/abi/OriginProofWalletRegistry.json)는 컴파일 out과 JSON 동일하며 공유 계약의 **11함수/5이벤트**와 완전히 일치합니다. OpenZeppelin 표준 EIP712 domain 조회/오류·생성자를 포함하고, `revoke`는 아직 없습니다. 전체 공유 인터페이스 구현 또는 발행/철회/버전 기능 완료로 표시하지 않습니다. C/A/D 원본·공유 인터페이스·서명 모델·Schema·Golden·lockfile은 변경하지 않았습니다.

```sh
forge inspect --root packages/contracts --offline OriginProofWalletRegistry abi --json > packages/contracts/abi/OriginProofWalletRegistry.json
```

### 검사와 실제 한계

| 검사 | 실제 결과·환경 |
| --- | --- |
| `forge test --root packages/contracts --offline` | **68 PASS / 0 FAIL / 0 SKIP** = 기존 48 + W3 20, 총 fuzz 5개 각 512회. Foundry 내부 EVM·합성 키/기관 |
| 16필드 변조/권한/복구 경계 | 서명 필드 변조·잘못된 chain/contract·high-s/v/길이·타 기관 ID/키·구키 발행·정지/사고·재전송/nonce gap·만료/시간/스키마·덮어쓰기 거부, 실패 후 nonce/문서 불변 |
| 원본 Python Golden | 납부·공식 안내 2개를 새 runtime의 합성 fixture 주소에 etch해 원본 KeyProof/Publish 서명으로 활성화/발행 성공. 실제 RPC 배포 아님 |
| 전체 Python | `UV_PROJECT_ENVIRONMENT=.uv-venv uv run --locked --all-packages --all-groups pytest -q` **179 PASS / 1 live SKIP**, 기존 anyio deprecation warning 1 |
| 생성·소비 대조 | Node 두 템플릿 hash PASS; make generate 후 기존 공유 ABI·Schema/TS/OpenAPI·Golden/예시 무변경, W2 실제 ABI 유지, 신규 ABI compiler와 동일 |
| 품질·보존 | 변경 Solidity format·diff·문서 내부 링크 PASS, 기존 사용자 5개 변경 hash 보존. 최초 fmt 확인의 assembly 줄바꿈은 재포맷 후 통과, 로직 변경 없음 |

실제 RPC/receipt/manifest·API/DB·브라우저 지갑·D 독립 QA·공개 체인·성능/가스 운영 비용·G07·v2/consume 전체 재검사는 미실행입니다. SG01~16의 공유 상태는 계속 NOT_EXECUTED이며 단위 검사 결과로 일괄 바꾸지 않습니다. 기존 회귀 수치를 실제 지갑 연결 또는 새로운 기능 수용 완료로 합산하지 않습니다.

### 다음 담당과 W4 경계

B의 Adapter·canonical event/receipt/배포 식별(B-C01~03), C/A의 원본 재계산·저장/서명 요청·실제 소비 연결, D 독립 재현이 남습니다. C Draft 0.2의 타입/서명과 같은 원본을 소비하며 아직 다른 담당 브랜치를 병합하지 않았습니다.

다음 버전·SUPERSEDED 전이·철회·철회용 nonce 소비는 **W4 후속**입니다. 이번 W3에서는 version=2/revoke가 성공하지 않습니다. 다음 단계는 같은 기관의 최신+1·원자적 대체와 정지 중 현재 키 철회를 구현하고, 최신 철회로 과거 버전이 복구되지 않는지 검사해야 합니다. 입력 회의 결정·Decisions 제외·G07 미해결·레거시 원본 보존 방침은 유지합니다. [W3 B 기여 기록](../portfolio/W3-B.md)에 개인/재사용·실제 검증·미완료를 구분합니다.

## 4.4 V5-W4-B 버전·원자적 대체·서명 철회 (2026-10-16)

- 담당 B `@hamin1228`, Codex 구현·검사 보조. 상태: **Contract 독립 구현·검사 완료 / 실제 배포·Adapter/API/DB·지갑·D 독립 검증·작성자 외 리뷰 대기**입니다. W4 단계 전체 완료가 아닙니다.
- 브랜치 `codex/v5-w4-b-document-lifecycle`, 시작 `004f774e89a278ec8ab4c5dba233d0d7c3eb0a97` (자기 W3). 검증 코드 **`a7b47fdd91e516d67c1a7d1db6be43f967ceabe8`**, 이후 인계 커밋은 문서만 변경합니다.
- 선행 [W3 Draft #67](https://github.com/OriginProof-3web/OriginProof/pull/67)은 착수 시 python-quality/contracts SUCCESS를 확인했습니다. 자기 선행 브랜치 대상으로 후속 Draft를 공유하며 과거 phase와 다른 담당 브랜치를 변경/병합하지 않습니다.

### 동작·저장·호환

[OriginProofWalletRegistry.sol](../../packages/contracts/src/OriginProofWalletRegistry.sol)에 문서별 버전 mapping과 별도 최신 포인터를 둡니다. 최초는 1, 이후 정확히 최신+1이고 공유 JSON safe integer 범위를 지킵니다. 같은 documentId의 기관/docKey는 고정하며 기존 버전의 hash·키·시각/block은 덮어쓰지 않습니다.

새 버전 저장·이전 최신의 state=SUPERSEDED(3)·최신 포인터·업무 nonce·DocumentSuperseded/DocumentPublished 이벤트가 한 거래에서 처리됩니다. 동일 다음 버전의 경쟁에서는 하나만 성공하고 나머지는 VersionConflict입니다. 이 검사 순서를 nonce보다 앞에 두어, 기존 W3의 같은 버전 재전송도 VersionConflict로 거부됩니다. 거부와 상태 불변 회귀를 유지하면서 해당 기대 오류만 W4 규칙에 맞췄습니다.

`revoke`는 action=2·자신의 기관/문서/버전·현재 활성 비사고 키·chain/address/domain·nonce·deadline을 검사합니다. 기관 ACTIVE/SUSPENDED 모두에서 현재 키 철회를 허용하며 사고/교체된 구키는 거부합니다. 성공 시 해당 버전 state=REVOKED(2), 동일한 기관별 publish/revoke nonce 소비·DocumentRevoked 이벤트만 변경하고 최신 포인터·원본/키 이력을 보존합니다. 같은 nonce 재전송과 새 nonce로 이미 철회된 버전을 다시 철회하는 요청은 각각 거부하며 실패 nonce는 소비하지 않습니다.

- 최신 철회로 과거 버전을 ACTIVE로 복구하지 않습니다. 만료/정지는 REVOKED/SUPERSEDED를 덮지 않습니다. expired는 저장 enum이 아닌 조회 시각의 파생 상태입니다.
- 과거 SUPERSEDED 버전도 소유 기관의 현재 키로 철회할 수 있으며 최신 버전에 영향을 주지 않습니다.
- 철회된 최신 버전 다음에도 정확한 최신+1을 발행할 수 있습니다. 공유 규칙의 이전 최신→SUPERSEDED 전이를 그대로 적용하므로 그 이전 버전의 현재 state는 3이 되지만 원본 hash와 과거 DocumentRevoked 이벤트는 보존됩니다. 상태 조회 하나로 철회 이력 전체를 대체하지 않습니다.
- 정상 키 교체 후 과거 정상 서명/발행 키 이력을 보존하고 현재 키로 과거 문서를 철회합니다. 사고 시에는 정지→새 키 공동 교체→정지 상태에서 필요한 버전 철회→공동 재활성화 순서를 적용합니다.
- 발행/revoke 원본·서명은 여전히 체인 밖에 둡니다. hash/서명 성공은 내용의 사실성·행동 안전을 보증하지 않습니다. 레거시 binding/consume을 신규 안내에 추가하지 않습니다.

[실제 ABI](../../packages/contracts/abi/OriginProofWalletRegistry.json)는 컴파일 out과 동일하며 공유 인터페이스의 **12함수·7이벤트 전체**와 일치합니다. 공유 인터페이스/준비 ABI·서명 모델/Golden·C/A/D 코드는 변경하지 않았습니다. 전체 ABI 형태 일치가 실제 API/웹·운영 연결 완료를 뜻하지 않습니다.

저장 layout은 W3의 단일 버전에서 버전별 mapping/최신 포인터로 바뀝니다. 이 컨트랙트는 업그레이드/관리자 우회 경로가 없으며 기존 주소에 덮어쓰지 않습니다. 실제 배포 시 별도 새 manifest/주소·배포 구분과 상태 이관/검증 범위를 B/C가 정해야 합니다. 이번에 어떤 실제 배포나 DB migration도 실행하지 않았습니다. W2/W3의 기존 코드/브랜치·배포 자료를 보존했습니다.

### 검사·실패와 수정

| 검사 | 결과·범위 |
| --- | --- |
| Foundry 전체 offline | **88 PASS / 0 FAIL / 0 SKIP** = 기존68 + W4 20. 버전별 이력/경쟁/실패 불변·철회/nonce 경쟁 양순서·정지/사고/정상 교체·원본 Golden 포함 |
| 철회 high-s/v 추가 확인 | 최종 코드에서 해당 검사 **1 PASS**. 전체 통과 뒤 같은 검사에 high-s/잘못된 v 사례를 추가해 대상만 재실행 |
| fuzz | 총6개 각512회. W4는 2~8버전 이력 뒤 최신 철회·과거 미복구를 검사 |
| Python 전체 | `UV_PROJECT_ENVIRONMENT=.uv-venv uv run --locked --all-packages --all-groups pytest -q`: **179 PASS / 1 live SKIP**, 기존 anyio warning1 |
| 생성·Node·ABI | make generate·두 템플릿 Node hash PASS. 기존 Schema/TS/OpenAPI·공유 ABI·W2 ABI·구/신규 Golden·예시 무변경, W4 ABI compiler/공유 계약 일치 |
| 품질/보존 | 변경 Solidity format·문서 내부 링크·diff PASS. 사용자 파일 5개의 원본 상태/hash 보존, 의존성/lockfile 변경 없음 |

최초 W4 확장 검사에서는 82 PASS/6 FAIL이었습니다. 내부 nextVersion 도우미가 memory struct를 참조로 받아 이전 버전 기대값까지 바꾼 것이 원인이었습니다. 도우미가 ABI encode/decode로 별도 사본을 만들도록 고쳤고 기대값·거부 규칙을 완화하지 않고 전체 88 PASS로 재검증했습니다. 변수 shadow warning도 이름을 구분해 해소했습니다. 원본 Python Revoke Golden도 실제 컨트랙트 runtime에서 소비했으며 합성 fixture 주소 etch 방식이지 실제 RPC/지갑 배포는 아닙니다.

실제 RPC/receipt·동시 네트워크 거래·manifest/Adapter·API/DB·브라우저·D 독립 QA·공개 체인·v2/consume 전체 재검사·G07·성능/가스 운영 실측은 미실행입니다. Foundry의 합성 거래 순서 검사를 실제 네트워크 동시성·receipt 검증으로 합산하지 않습니다. SG01~16은 공유 fixture에서 계속 NOT_EXECUTED입니다.

### 인계·다음 단계

ABI 재생성 명령은 4.3절과 같습니다. B-C01 승인자 배포 근거·B-C02 canonical 승인 목록/이벤트·B-C03 UNKNOWN 검색/배포 식별은 실제 Adapter에서 남아 있습니다. 이후 W5는 신규 이벤트·현재 상태 직접 조회를 기존 indexer와 연결하고 지연된 projection으로 현재 성공을 만들지 않도록 검증합니다. G07은 별도 재현/원인/수정·D 재검사가 필요합니다. 입력 회의 결정과 Decisions 제외는 유지합니다. [W4 B 기여 기록](../portfolio/W4-B.md)에 과거 기록·이번 기여·실제 범위를 구분합니다.

## 5. 완료 기록

현재 새 5.0 코드 반영·실제 연결·회귀 검증이 확인되어 활성 목록에서 완료로 옮긴 항목은 없습니다. 완료되면 항목 ID·재사용 범위·반영 PR·검증 SHA/명령/결과·한계를 여기에 남깁니다. 앞선 네 PR 병합은 2절의 과거 변경 반영 기록으로 구분합니다.

## 4.5 V5-W5-B 1차 ABI 증거·배포별 이벤트 journal (2026-10-16)

`codex/v5-w5-b-chain-evidence`에서 자기 W4 `a4bfa22bf870f3bd5ae02e439636fbf8204444a7`를 기준으로 B 경로의 `wallet_rpc.py`, `wallet_projection.py`와 합성 검사 50개를 추가했습니다. 생성된 구현 ABI를 소비하며 ABI/공유 모델 원본을 변경하지 않습니다. 상세한 흐름·실제 명령·사용 경계는 [B 인계](../blockchain/v5_w5_chain_evidence.md), 기여 기록은 [W5-B](../portfolio/W5-B.md)입니다.

**준비된 것:** chain/address/deployment hash/runtime code 확인, canonical hash-pinned view 조회, 생성 ABI의 이벤트 7종 해석, 배포별 journal/checkpoint 원자 저장·restart·명시 rewind, 실제 tx calldata/receipt 증거. projection은 현재 상태 조회에서 소비하지 않습니다. 직접 제출 증거는 C의 CONFIRMED 판정이 아닙니다.

**미완료:** C 고정 Draft `6e0e924c77e9a5b83a8522df4d3cfdc797e8822c`의 원본 port는 이 브랜치에 없어 사본·임의 병합 없이 변환을 남겼습니다. B-C01 승인자 배포 provenance, B-C02 승인 목록/count·상태 대조, B-C03 intent별 receipt/event/state 대조·UNKNOWN 원본 검색·중계와 C Operation 연결, 누락 getter의 custom-error 구분·실제 배포 manifest/RPC·PostgreSQL/지갑 검사가 남습니다. **W5 전체 완료가 아닌 저수준 독립 구현/합성 검사 완료**입니다.

Python **229 PASS/1 live SKIP**, 신규 50 PASS 포함. 공식 lint·구조·문법·Node hash·생성물 diff 통과. 외부 Foundry lib를 포함한 확장 lint는 기존 외부 오류 26건으로 실패하여 공식 범위와 구분했습니다. Solidity/ABI 무변경으로 Foundry 재실행은 생략했습니다. 실제 EVM/RPC/API/DB/지갑·D QA·G07 재현·v2/consume 전체 실환경·공개 체인·유료 AI는 미실행이며 SG01~16은 바꾸지 않았습니다. head 역행/reorg 방어 합성 통과로 **G07을 해결 처리하지 않습니다.** 사용자 변경 5개와 legacy/고정 과거 SHA를 보존합니다.


## 4.6 V5-W5-B 2차 미등록·승인/거래 상태 대조 (2026-10-17)

자기 W5 1차 `7666bb9bf2d85804b9abe9be5a87ea122e1d914d` 위의 `codex/v5-w5-b-reconciliation`에서 정확한 getter별 custom error만 미등록으로 구분하고, 생성 ABI 기반 승인 주소/count·동일 tx 실행·전체 intent/receipt inclusion/이벤트·과거 및 현재 상태를 대조했습니다. 변경 경로는 B RPC·새 reconciler·합성 검사와 기록입니다. 상세 흐름·사용법·한계는 [2차 B 인계](../blockchain/v5_w5_reconciliation.md), 기여는 [W5-B](../portfolio/W5-B.md)를 따릅니다.

B-C02 승인 이력과 B-C03 거래별 대조의 저수준 독립 구현/합성 검사를 보강했습니다. 과거 발행 성공을 현재 유효로 바꾸지 않고 후속 철회·대체·정지/키 사고와 재활성화를 구분합니다. 정지 순간을 receipt 블록 끝 상태에서 분리할 수 없으면 보류 오류입니다. C WalletTransaction/CONFIRMED/DB를 직접 구현하지 않습니다.

전체 Python **281 PASS/1 live SKIP**, 신규 2차52·기존1차50 PASS 포함. 공식 lint·구조·Node hash·재생성 diff·공백 검사 통과. Solidity/ABI 무변경으로 로컬 Foundry는 재실행하지 않았습니다. 실제 RPC·EVM·PostgreSQL·API/지갑·독립 QA·공개 체인·G07 재현·v2/consume 전체 실환경은 미실행입니다.

C #63은 고정 `6e0e924` Draft이며 원본 port가 현 B 브랜치/integration에 없어 사본 없이 변환을 남겼습니다. B-C01 고정 승인자 배포 근거, UNKNOWN 원본 검색/submit·최종성/Operation 연결과 실제 통합은 후속입니다. 착수 시 integration `4a9b92d`의 D 반영을 확인했으며 이번 자기 W5 검사와 구분합니다. 사용자 원본 변경5개와 legacy/과거 phase를 보존하고 **G07·SG01~16·W5 전체 완료 상태를 해결/PASS로 올리지 않습니다.**


## 4.7 V5-W5-B 3차 실제 로컬 RPC·UNKNOWN 원본 검색 (2026-10-17)

자기2차 `6916224` 위의 `codex/v5-w5-b-live-recovery`: 코드 `5a51e4b`, 최종 실제 wallet RPC 검증 `a064b63f9b44e5f9ccf5a6c9a4f237612d03e0e3`. B의 `WalletRecovery.find_transaction`은 전체 calldata·필요 sender·canonical 위치의 원본 후보를 페이지별로 찾고2차 Reconciler로 다시 검증합니다. known hash·실패/성공 시도·pending·checkpoint reorg와 관측 business nonce를 구분합니다. 전송 메서드/재전송 허가/Operation 상태 변경은 없으며 C 원본 port의 직접 구현이 아닙니다.

일반306 PASS/2 opt-in SKIP, 신규 합성25 포함. 실제 새 합성 Anvil Registry/RPC 별도1 PASS: EIP-712·2-of-3·발행/원자 대체/철회·정지/재활성화·실제 accepted 응답 유실 뒤 hash 없는 복구(중계자 nonce는1개만 증가)·실패 replay·pending·SQLite restart·실제 reorg/명시 rewind·RPC 단절. 최종 ABI/원본 생성물 일관성·공식 lint·구조·문법·Node hash 통과. [3차 인계](../blockchain/v5_w5_live_recovery.md), [실행 증거/종료한 합성 배포 manifest](../blockchain/evidence/v5_w5_live_a064b63.json), [개인 기여](../portfolio/W5-B.md)에 실제 범위를 기록했습니다.

초기 합성 padding fixture1FAIL과 live 수락/채굴 가정1FAIL을 수정·재검증했습니다. C의 Operation/DB/dispatcher·port/submit·최종성, 승인자 manifest 소비와 운영 재배포·PostgreSQL·브라우저·독립 QA가 남습니다. **빈 검색은 재전송 허가가 아니며 G07은 미해결**입니다. fresh 로컬 reorg를 mixed G07 해결이나 W5 전체/SG01~16 PASS로 합산하지 않습니다. 사용자5개 변경·legacy·타 담당 생산 코드를 보존합니다.
