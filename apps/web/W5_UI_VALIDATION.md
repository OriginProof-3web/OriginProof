# W5 A 화면 검증 · 2026-10-06

담당 A 김형준 `@kimhyounjun`, `W5-A1~A3`, branch `codex/w5-a-ui-completion`, [초안 PR #55](https://github.com/OriginProof-3web/OriginProof/pull/55).
A 웹 보완과 자체 브라우저 검사는 통과했습니다. **팀 W5 완료는 아닙니다. 최신 혼합 장애 검사 G07 실패, D 독립 확인, 작성자 외 리뷰와 최종 통합 SHA가 남았습니다.**
기계 판독 근거: [검사 요약·SHA·환경·실패 관측값](test/evidence/w5-20261006.json).

## 기준과 변경

- 시작 `06d6ab9ab5bc8c8eb9d87ac079d4770e36495ed1`. UI 제품 실행 SHA `eb538a2cd19cea5786023834bc6be2c83609faf5`.
- 깨끗한 복제본: 정적/39개 컴포넌트/빌드 `729142168368b5c394164ca1d4ef3621eb12f021`; 마지막 브라우저 코드 `407ea5a`; 이후 API 재현 진입점 `6d159b6` 추가. UI 제품 코드는 동일합니다. 검사 결과 표시 보강은 `6d159b6` + 로컬 변경에서 1 PASS(6.2초), 검사 파일 hash도 근거에 기록했습니다. 이후 기록 변경을 제품 재검증으로 표현하지 않습니다.
- 실제 API/Adapter/Contract는 C #38 `3ef1fd40943914c1450e8bc05047119ab7eabbc0`; D QA 원본 `a3f55c6991061ac445d2223f19ff1b2a48acab0e`를 읽기 전용 재사용했습니다. 하나의 최종 integration SHA 검사가 아닙니다.
- 401에서 보호된 정보 제거·재로그인, 상태별 오류와 읽기 재조회, 늦은 응답 차단, 중복 요청과 결과 미확인 작업 자동 재전송 방지를 보완했습니다.
- 신청 DB 상태와 현재 체인 상태를 분리했습니다. 초기값은 미확인, 키 조회가 실패해도 성공한 신청 조회는 표시하고 503 시 과거 체인 상태를 제거합니다.
- Sidebar/본문의 부족한 텍스트 대비와 좁은 화면의 운영자 입력 폭을 수정했습니다. 사용자 제공 디자인/랜드 화면 배치는 유지합니다.
- `해커톤 본선/웹 디자인`에 소스·bundle을 반영했고 8768의 제공 파일과 SHA256 일치를 확인했습니다. 기존 command는 index에서 시작합니다.

## 실제 검사 결과

| 명령/범위 | 최종 결과 | 실제/모의 경계 |
| --- | --- | --- |
| 깨끗한 복제본 `cd apps/web && npm test` | **39 PASS** | 컴포넌트·HTTP 응답 mock 회귀 |
| `npm run lint`, `tsc --noEmit`, `npm run build` | PASS | official/Next 빌드; 기존 CSS autoprefixer 경고 1개 |
| `run-w5-admin.py` → `w5-admin-live.spec.ts` | **1 PASS, 26.5초** | 기존 8768 관리자 UI → 요청별 실제 독립 API/PG/Anvil 연결 |
| `w5-admin-accessibility.spec.ts` | **1 PASS, 12.6초; 결과 표시 보강 재검사 1 PASS, 6.2초** | 기존 8768 실제 로그인·세 역할, axe WCAG A/AA |
| D QA의 FRESH API 재실행 | **18 PASS / 0 FAIL** | 실제 HTTP·PostgreSQL·로컬 EVM, browser NOT_RUN |
| D QA의 MIXED_DIAGNOSTIC 첫 재실행 | **18 PASS / 0 FAIL** | 실제 혼합 상태·재시작·reorg·RPC 장애 |
| 재현 진입점 `run-w5-api.py`의 마지막 MIXED 재실행 | **17 PASS / 1 FAIL** | **G07 재발: issuer UNAVAILABLE**. 전체 통과/해결 판정 금지 |

API 검사는 18개 그룹이며 18개의 브라우저 테스트라는 뜻이 아닙니다. 모든 재실행은 A가 수행했습니다. D의 검사 코드를 썼다는 이유로 D 독립 승인이라고 부르지 않습니다.

### 관리자 브라우저로 확인한 경로

계정만 seed한 새 합성 환경에서 두 기관 각각 신청 → 운영자 승인 → 체인 활성화 → 최초 공개키 등록 → PAYMENT_REQUEST/OFFICIAL_DOCUMENT 발행 → 개인 ID 조회(PROOF_ONLY) → 원본 값 비교(VERIFIED/FULL_COMPARISON) → 변조 확인(AMOUNT_MISMATCH/FIELD_MISMATCH) → 발행 목록 폐기 → PROOF_REVOKED를 확인했습니다.
Bank의 정상 키 교체 후 기존 Proof 유효성, 별도 새 Proof 1회 사용/CONSUMED와 재사용 버튼 비활성화도 확인했습니다.
새로고침·다른 관리자 URL 이동·뒤로가기 전후 서버의 두 기관 발행 목록이 동일해 새 거래가 반복되지 않았습니다.
버튼/입력/동의는 focus·Enter·Space로 실행했습니다. **한국어 rotate select만 Playwright selectOption을 사용했으므로 모든 컨트롤의 수동 키보드 검사를 완료했다고 주장하지 않습니다.**

503/401 응답 주입은 브라우저 UI의 실패·기존 결과 제거·수동 재조회·재로그인 검증이며 실제 API 중단/세션 만료 자체의 독립 재현은 아닙니다. 실제 RPC 장애·원자적 사용·권한·복구 경계는 API 그룹 검사와 구분합니다.
390×844는 사이드바를 접은 상태에서 가로 넘침과 axe를 확인했습니다. 화면 낭독기 수동 검사·실제 휴대폰 QR·외부 서비스·유료 AI는 미실행입니다. AI는 mock이며 진위 판정에 사용하지 않습니다.

### 첫 실패와 수정

- axe 대비 부족 6개와 모바일 운영자 입력 넘침 → 텍스트 대비/폭 보완 → 최종 접근성 PASS.
- 신청 상태 ACTIVE 기본값과 병렬 키 오류로 신청 갱신 누락 → 초기 미확인/신청 별도 갱신 → 회귀 및 fresh 경로 PASS.
- 깨끗한 복제본의 의존성 symlink는 Vitest 확장 문제로 실패 → `pnpm install --frozen-lockfile --ignore-scripts`, official `npm ci --ignore-scripts`로 새 설치 → 39 PASS. 루트는 pnpm 저장소이며 root npm ci는 사용하지 않습니다.
- Colima가 `/private/tmp`를 공유하지 않아 배포 manifest가 실제 호스트에 없는 상태에서 503 → 공유되는 W5_ADMIN_OUTPUT_DIR로 실행, manifest 누락 시 조기 중단 → clean clone fresh 경로 PASS. 성공을 만드는 API 대체/숨긴 mutation 재시도는 없습니다.
- 이전 status/combobox 선택자와 native 기관 select의 잘못된 키 입력 → 실제 레이블/역할 및 native type-ahead로 수정. 당시 실패 기록은 보존합니다.
- **G07**: 처음 fresh/mixed에서는 미재현됐지만 마지막 mixed에서 두 차례 기관 snapshot 실패가 관측됐습니다. verification INCONCLUSIVE, DEPENDENCY_UNAVAILABLE, issuer UNAVAILABLE, 후속 키/서명/Proof NOT_RUN. Reader 원인이 확정되지 않아 C/B 진단과 D 재현이 필요합니다. A가 UI 재조회로 이 API 회귀를 통과시킨 것은 아닙니다.

## 재현과 환경

[로컬 재현 절차](LOCAL_ADMIN_TESTS.md#w5-추가-재현-2026-10-06). 기존 8768 관리자 페이지를 사용하며 새 테스트 사이트는 없습니다.
macOS, Node **26.0.0**/pnpm11.19, Python **3.13.15**, PostgreSQL16.4/Foundry1.4.4 pinned fixture, Chromium.
계획의 Node22.18/Python3.13.0과 다르므로 지정 버전의 별도 재현은 남습니다. 공식 디자인 런타임 `npm audit --omit=dev` 0건; 개발 의존성 포함 기존 4 high와 기존 빌드 경고는 별도 보존하며 전체 보안 완료를 주장하지 않습니다.
Owned 임시 PG/Anvil/network 정리 확인. 기존 8768/8780의 DB·사용자 기록 reset 없음. 계정·쿠키·키·원문·전체 payload는 공개 근거에서 제외했습니다.

## 단계 판정과 인계

| 항목 | 현재 상태 | 후속 담당 |
| --- | --- | --- |
| W5-A1 상태/실패/재시도 보완 | 구현·자체 39개 회귀·fresh 브라우저 PASS | 작성자 외 리뷰 |
| W5-A2 접근성·키보드 핵심 경로 | 핵심 경로/자동 axe PASS, 수동 낭독기/native select 독립 검사 남음 | D W5-D2 |
| W5-A3 실제 결과 표현·두 기관 전체 웹 | fresh 연결 PASS, mixed G07 회귀 실패 보존 | C/B 원인 진단, D 동일 후보 재검사 |
| W5 단계 완료 | **미완료** | G07 해결, A~D 동일 최종 SHA·F01~F15 매핑, D 독립 수용·리뷰·기여 사실 확인·phase/W5 승격 |

phase/W5는 현재 미생성입니다. 자신의 PR을 스스로 승인하지 않았으며, 작성자 외 승인/팀원 완료를 가정하지 않습니다. W6/W7의 시연·RC·영상·리허설 완료도 주장하지 않습니다.
