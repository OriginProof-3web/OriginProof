# W3 A QR 후속 검사 — 2026-10-03

## 기준과 범위

- 담당: A 김형준님 / @kimhyounjun, W3-A2 후속. 사용자 요청에 따라 Codex가 구현·검사했습니다.
- branch: `codex/w3-a-qr-followup`, 기준 `phase/W3@121e1cade40f9ac3b001dc7aa24256d9033f0214` (#44 병합 후).
- 검사 대상: 위 기준에 QR 변경을 더한 작업 트리. 변경된 웹 소스/검사/설정의 SHA-256: `d560e6c84ec3a38191082120389130f8c953bbc499cf512a5ce17ab4dd813ce3`. 경로 정렬 후 `경로 + NUL + bytes + NUL`; 문서 추가 전 계산.
- 환경: macOS arm64, Node 26.0.0, pnpm 11.19.0, Next 15.5.3, Chromium/Playwright 1.55.0.
- 사용자님이 이 대화에서 `qrcode`와 타입 추가를 명시 승인했습니다. qrcode 1.5.4, @types/qrcode 1.5.6을 official npm lock에 고정했습니다.
- 메인 index.html, WebGL, SidebarNav 디자인은 변경하지 않았습니다. backend/contract/생성 타입도 변경하지 않았습니다.

## 구현

발행 목록의 실제 Proof 상세에서 **검증 QR 보기 → QR PNG 저장**을 제공합니다. 미발행 초안에는 제공하지 않습니다.
QR은 기존 사용자 조회 링크와 같은 현재 host/port의 공개 `proof_id` 링크만 담습니다.
원문·인증정보·개인키를 담지 않습니다. 실패 시 검증 링크를 사용하도록 안내하고,
이전 Proof의 늦은 생성 응답이 현재 QR을 덮어쓰지 않도록 취소합니다.

## 실제 실행 결과

| 명령/검사 | 결과·범위 |
| --- | --- |
| `pnpm --filter originproof-demo-web lint` | 통과, eslint 경고 없음 |
| `pnpm --filter originproof-demo-web typecheck` | 통과 |
| `pnpm --filter originproof-demo-web test` | 18 passed; QR 링크·실패·비동기 교체 3개 추가 |
| `ORIGINPROOF_API_ORIGIN=http://127.0.0.1:8770 pnpm --filter originproof-demo-web build` | 통과; 기존 autoprefixer end 경고 유지 |
| production Chromium E2E | **12 passed / 0 skipped (6.8초)**; 기존 11개 + QR 1개 |
| macOS Vision QR decode | 합성 API 예시와 실제 PAYMENT_REQUEST/OFFICIAL_DOCUMENT 발행 QR 3개 모두 원래 공개 링크로 해독 |
| PNG 저장 | 256px PNG data URL, Proof별 파일명 다운로드 확인 |
| 실제 API 두 유형 | 발행 → 기관 목록/상세 → QR → 새 익명 세션 PROOF_ONLY → 지정 수신자 FULL_COMPARISON → 금액/문서번호 변조 거부 통과 |
| 타 기관 접근 | 두 유형 목록 분리 및 제한 content 404 통과 |

실제 API는 기존 폐기 가능한 합성 환경 **C #36@85e152cd5550f24874abb267122a5d8ece29e3b9**, PostgreSQL 16.4, Anvil chain 31337입니다.
DB reset/migration/재배포를 하지 않았습니다. 새 합성 Proof 발행은 검사의 부작용입니다.
최신 phase/W3의 backend를 새로 기동한 결과로 주장하지 않습니다.
12개 중 2개가 실제 API 연결이고 나머지는 mock API 화면/회귀 검사입니다. QR 인코딩·Vision 해독은 실제 구현으로 실행했습니다.

재현 명령 (테스트 계정 파일은 로컬 비공개이며 Git에 포함하지 않음):

```sh
swiftc apps/web/test/qr-decode.swift -o /tmp/originproof-qrdecode
ORIGINPROOF_API_ORIGIN=http://127.0.0.1:8770 pnpm --filter originproof-demo-web build
pnpm --filter originproof-demo-web start --hostname 0.0.0.0 --port 3103
# 별도 터미널; 계정 파일 경로를 해당 환경에 맞게 지정
ORIGINPROOF_WEB_BASE_URL=http://127.0.0.1:3103 \
ORIGINPROOF_QR_DECODER=/tmp/originproof-qrdecode \
ORIGINPROOF_TEST_ACCOUNTS=/absolute/private/accounts.json \
pnpm --filter originproof-demo-web test:e2e
```

Vision decoder는 macOS 기본 프레임워크이며 추가 의존성이 없습니다. decoder 환경변수를
생략하는 CI에서는 QR 생성·PNG·공개 조회를 검사하지만 QR 해독을 실행한 것으로 기록하지 않습니다.

## 실패·한계·후속

- 첫 QR E2E는 같은 이름의 사이드바/상단 메뉴 두 개를 구분하지 못했고, 이후에는 접힌 검사 근거의 NOT_RUN을 바로 읽으려 했습니다. 실제 메뉴를 선택하고 검사 근거를 펼치는 순서로 수정했습니다. 제품 디자인은 변경하지 않았습니다.
- 휴대폰 카메라/LAN 스캔은 미실행입니다. PC에서 LAN 주소로 접속한 뒤 생성해야 QR에도 LAN host가 들어갑니다. localhost QR을 다른 기기에 사용할 수 있다고 표시하지 않습니다.
- D 독립 실제 QA [#47](https://github.com/OriginProof-3web/OriginProof/pull/47) head `59084570960e94a76bf041c513043816e6075ae1`는 확인 시 OPEN입니다. 해당 결과는 D의 증거이며 이번 QR 검사에 합산하지 않습니다.
- npm audit는 기존 Tailwind CLI → parcel/watcher → micromatch → braces 경로의 high 4개를 보고합니다. QR 패키지는 해당 목록에 없습니다. 기존 의존성 교체는 하지 않았습니다. audit 전체 통과로 주장하지 않습니다.
- 새 QR 변경의 작성자 외 리뷰/CI와 최신 통합 backend에서의 재현은 남아 있습니다. PR은 사용자님께 결과를 먼저 보고한 뒤 진행합니다. W3 팀 전체 완료 판정은 하지 않습니다.

## 커밋 후 별도 소스 재현

- 실행 SHA: `d54efe6` (QR 구현·검사·기록 커밋).
- `git archive`로 별도 임시 디렉터리에 추출 후 frozen install, 웹 typecheck,
  component **18 passed**, production build가 모두 통과했습니다.
- 이 별도 디렉터리에서 브라우저는 재실행하지 않았습니다. 브라우저 12 passed는 앞의
  동일 제품 소스/production 서버 검사입니다. 다음 문서 커밋은 이 기록만 추가합니다.
- audit high 4개 경로의 lock 버전은 기준 SHA와 동일함을 비교했습니다.
