# W3 A — 기존 디자인과 실제 Proof API 연결

- 담당 범위: 김형준님 / A / @kimhyounjun, W3-A1~A3.
- 작업 브랜치: `codex/w3-a-official-web`.
- 시작: `phase/W3@1f8ed632ea9c74091abaf2fe2ec32882038f731f`.
- PR: [#44](https://github.com/OriginProof-3web/OriginProof/pull/44), phase/W3 대상의 W3 웹 구현입니다. 사용자님이 2026-10-03 CI 보완·병합과 이전 준비 PR #29의 대체 정리를 요청하셨습니다. QR·독립 실제 연결 QA와 팀 전체 단계 완료는 별도입니다.

## 실행

루트에서 `pnpm install --frozen-lockfile` 후:

```sh
ORIGINPROOF_API_ORIGIN=http://127.0.0.1:8000 pnpm --filter originproof-demo-web dev --hostname 127.0.0.1
```

`http://127.0.0.1:3000/`은 원본 메인 디자인 `index.html`로 열립니다. 기관 로그인은
`business-login.html`, 사용자 로그인은 `user-login.html`, 운영자는 `admin.html`입니다.
Next.js의 기존 `/api` rewrite를 사용합니다. 운영자 인증은 서버 role로 확인합니다.
빈 로그인 입력의 화면 탐색은 기존 디자인 요청을 보존하지만 인증 세션을 만들지 않습니다.

`official/`은 제공받은 HTML·React·CSS 원본과 기존 디자인의 lockfile을 보관합니다.
기존 esbuild/Tailwind 빌드로 `public/`에 정적 화면을 생성하며 iframe·별도 웹 서버를
추가하지 않았습니다. `public/`의 생성 파일은 Git에서 제외합니다. dev/build/typecheck
명령은 디자인의 고정 npm lockfile을 설치합니다. 기존 MVP는 `/mvp`, 기존 W1/W2 검사
화면은 `/finals`에 보존했습니다.

## 계약·다른 담당자의 작업

C #35 `17c24a36a46c6b2a823a3b7fac20c97c6faee98f`의
`packages/schemas/generated/types/{api,originproof}.ts`를 수정 없이
`official/components/{api,core}-types.generated.ts`로 복사했습니다.
현재 phase/W3에 병합된 계약의 소비자 snapshot이며, 공유 생성물 원본을 수작업으로 바꾸지 않았습니다.
2026-10-03 두 snapshot과 현재 공유 생성물의 byte 일치를 확인했습니다. API의 허용 기관·문서 코드는 C 설정이
결정합니다. 현재 P0 두 합성 기관만 표시합니다.

실제 브라우저 연결은 별도 합성 PostgreSQL·Anvil 환경의 C #36
`85e152cd5550f24874abb267122a5d8ece29e3b9`(C #35 포함)에 실행했습니다.
이 과거 live 결과는 현재 `phase/W3` 통합 SHA의 실제 브라우저 검증 결과를 의미하지 않습니다.
현재 branch에는 C #35, B #40, D #46이 포함된 `phase/W3@9047163`을 반영했습니다.
다른 담당자의 backend·contract 경로는 수정하지 않았습니다.

## 구현과 남은 부분

- A1: 서버 생성 ID·서명·binding만 사용. 두 유형 필수 입력·양의 정수·통화·미래 만료,
  FastAPI 422 loc별 오류, 제출 중 중복 차단, 동일 body 재시도 시 request ID 재사용.
  발행 응답 후 목록 새로고침 실패를 발행 실패로 바꾸지 않습니다.
- A2: 자기 기관 목록/제한 상세, ID 복사, 공개 ID만 담은 검증 링크. 다른 기관의 목록과
  content 접근 차단을 기존 실제 서버 검사로 확인했습니다. QR 생성·디코딩·휴대폰
  LAN 스캔은 별도 후속 작업이며, 이번 CI 보완에서 새 의존성을 추가하지 않았습니다.
- A3: 익명 PROOF_ONLY 조회와 인증된 후보 필드 비교 분리. 실제 enum·checks·reason 표시,
  null lifecycle은 미확인, NOT_RUN은 미실행. 조회는 consume을 호출하지 않습니다.
  권한 실패 시 로그인 링크, 정상/금액·문서번호 변조 비교를 연결했습니다.
- 기존 키 교체 UI는 #36 계약을 사용하는 W4 디자인의 재사용 부분이며 W3 단계 완료
  근거로 포함하지 않습니다. Proof 폐기·consume·AI provider는 이번 W3 완료 범위가 아닙니다.

## 검사 명령

```sh
pnpm --filter originproof-demo-web lint
pnpm --filter originproof-demo-web typecheck
pnpm --filter originproof-demo-web test
pnpm --filter originproof-demo-web build
pnpm --filter originproof-demo-web test:e2e
```

CI의 E2E는 앞 단계에서 만든 production build를 `pnpm start`로 실행합니다.
로컬 기본은 기존 개발 서버입니다. CI 조건을 로컬에서 재현하려면 build 후
`CI=1 pnpm --filter originproof-demo-web test:e2e`를 실행합니다. 기능 검사 context는
`reducedMotion: reduce`를 사용하며, WebGL·일반 애니메이션 성능 검사는 아닙니다.

실제 API 브라우저 검사는 격리된 합성 계정 파일을 명시해야 합니다. 파일은 배열 형태의
username/password 객체이며 저장소에 넣지 않습니다. 계정 파일 환경변수가 없으면 live
검사 2개는 skip합니다. live 검사는 새로운 합성 Proof를 발행하며 DB/체인을 초기화하지
않습니다. trace/video/screenshot에 로그인 비밀값이 기록되지 않도록 live trace를 끕니다.

```sh
ORIGINPROOF_TEST_ACCOUNTS=/private/path/accounts.json pnpm --filter originproof-demo-web test:e2e official-live.spec.ts
```

최신 CI 보완 결과와 과거 live 결과의 구분은 `W3_VALIDATION.md`를 참고합니다.
D의 독립 실제 재현과 QR·팀 단계 완료는 후속 작업입니다.

## 2026-10-03 QR 후속

발행 목록 → Proof 상세 → **검증 QR 보기**에서 QR을 표시하고 **QR PNG 저장**으로 다운로드합니다.
QR 링크는 현재 접속 host/port를 사용합니다. 휴대폰용은 PC에서 LAN 주소로 접속하여 생성해야 합니다.
PC 브라우저·실제 두 유형 QR 해독 검사를 통과했으며 휴대폰 스캔은 미실행입니다.
[후속 검사 기록](W3_QR_VALIDATION.md)을 참고하세요.
