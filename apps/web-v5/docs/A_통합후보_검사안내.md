# A 통합 후보 검사 안내 (5안 화면 × OriginProof d0111d8)

작성: 배너(기획) · 2026-10-26 · 대상 화면 `페이지/business.html` · 감사팀 재작업 T6 반영(미연결 기준표 U1~U9, Registry 단계표 R1~R5, seed 출력 대조, 미실행 사유) · T6 2차(T2 프록시 반영: 0절 주소·절차 확정, 2절, 4절 실서버 칸, 7-2절, U3·U4·U5, 11절 본부 검사 결과 신설)
근거: `docs/5안_기술연결_결과.md`(피터), `docs/T2_T5_개발메모.md`(피터), `개발/op5-proxy.mjs`·`개발/5안 d0111d8 프록시 시작.command`(읽기만), `페이지/js/op5_client.js`·`op5_connect.js`·`op5_scenes.js`·`api_adapter.js`, `개발/collaboration-server.py`·`개발/local-runtime.py`와 그 프록시(5안 밖, 읽기만), 상위 `tools/local_proxy.py`(읽기만), 감사 복제본에서 `git show d0111d8:<경로>`로만 읽은 파일

**기준표 위치**: 미연결 항목의 원본 표는 이 문서 5-1절(U1~U9), Registry 오류 단계표는 5-2절(R1~R5)이다. `docs/5안_기술연결_결과.md` 8-0절에 같은 표를 그대로 옮겼다. 두 문서의 ID·개수(U 9개, R 5개)는 같아야 하며, 고칠 때는 이 문서를 먼저 고치고 결과 문서에 그대로 복사한다.

표기 규칙
- “ ” 안의 글은 화면에 나오는 문구이며, 코드 문자열과 글자 하나까지 같다(9절 대조 결과). 실행 중에 채워지는 값(번호·초·주소)은 “ ” 밖에 `…`로 적었다.
- 비밀번호·키·토큰·메일 비밀값은 이 문서에 한 글자도 적지 않는다. env는 이름만 적는다.

---

## 0. 검사 주소와 본부 실행 절차 (가장 먼저 읽기)

**확정(T6, T2 결과 반영)**: d0111d8 검사는 화면 하나·프록시 하나로 한다. 화면 주소는 `http://127.0.0.1:8790/business.html?mode=api`이다. 같은 출처 프록시 `개발/op5-proxy.mjs`가 `페이지/`를 내보내고, `/api/v1/`·`/api/v2/`·`/api/v3/`·`/api/health/`를 d0111d8 API(`http://127.0.0.1:8000`)로 넘긴다. 0-3절의 이전 길(8768 협업 서버, `tools/local_proxy.py`, 직접 연결)은 쓰지 않는다. 이 절은 9절 결정 1번의 2번 길("d0111d8용 같은 출처 프록시를 따로 둔다")을 택한 결과다.

**상태**: 프록시 파일 마련, 본부 실행 대기. 팀은 프록시·서버·docker·브라우저를 실행하지 않았다. 아래 절차의 결과는 아직 하나도 없다. 본부 실측 전에는 어떤 실서버 항목도 통과로 적지 않는다. 결과는 11절 표에 적는다.

### 0-1. 확정 주소와 실행 절차 (한 표)

| 순서 | 누가·어디서 | 명령 / 여는 곳 | 확인할 것 |
| --- | --- | --- | --- |
| 1 | 본부 · d0111d8을 체크아웃한 작업 폴더 | `.env`가 없으면 `.env.example`을 복사한다. 항목 이름만 적는다(값은 문서에 쓰지 않음): `API_WALLET_REGISTRY_ADDRESS`는 비워 둔다. `API_WALLET_TEXT_INPUT_ENABLED`는 합성 검사이므로 true로 켠다. `API_BROWSER_ORIGINS`는 **바꾸지 않는다**(0-2절). `API_SESSION_COOKIE_SECURE`는 기본(false)으로 둔다(Q3) | 2-1절 표의 항목 이름과 같은지 |
| 2 | 같은 폴더 | `make finals-up` | 끝에 `http://127.0.0.1:8000/health/ready` 200 |
| 3 | 같은 폴더 | `make v5-wallet-seed` | alembic 출력 뒤 3줄(안내 1 + 설정 2). 3절 표와 대조 |
| 4 | 같은 폴더 | seed 출력 2줄을 `.env`의 `API_WALLET_INTERNAL_APPROVERS`·`API_WALLET_OPERATOR_ADDRESSES`에 넣는다(승인 지갑 자리는 Governance 고정 주소로 바꿈, 3절) → `make api-reload` | ready 다시 200 |
| 5 | 본부 · 5안 폴더 | `"/Users/khj/Desktop/해커톤 직원/web-5안/개발/5안 d0111d8 프록시 시작.command"` (같은 일: `cd "/Users/khj/Desktop/해커톤 직원/web-5안" && OP5_PROXY_PORT=8790 OP5_UPSTREAM=http://127.0.0.1:8000 node 개발/op5-proxy.mjs`) | 출력 “브라우저에서 열기: http://127.0.0.1:8790/business.html?mode=api”, 이어서 “5안 프록시: http://127.0.0.1:8790/business.html?mode=api  →  http://127.0.0.1:8000 (/api 를 떼고 전달)”, “끄기: Ctrl+C”. node가 없으면 “node 가 없어요” |
| 6 | 브라우저(본부) | `http://127.0.0.1:8790/business.html?mode=api` | 실서버 모드로 시작(값은 localStorage에 남음). 주소는 **`127.0.0.1`로만** 연다(`localhost`도 받지만 쿠키가 따로 붙으므로 섞지 않음) |
| 7 | 같은 화면 | 사이드바 `기관 상태` → 4-4 1·2번 | live·ready가 d0111d8 API 값으로 나오는지 |
| 8 | 같은 화면 | `로그인 화면 열기` → `http://127.0.0.1:8790/business-login.html`에서 seed 기관 계정(`v5_bank`)으로 사람이 직접 로그인 → `business.html`로 돌아옴 | 4-4 4번(“로그인” 구역에 계정·역할 issuer) |
| 9 | 같은 화면 | 4-1 실서버(입력·결과) → 4-3 실서버(보관·삭제) → 4-2 실서버(지갑) → 4-4 나머지 순서로 | 각 표의 기대 문구. 결과는 11절에 |
| 10 | 본부 · 5안 폴더 | T5 첫 화면 캡처 2건 생성 뒤 `node 개발/png-diff.mjs <기준> <새>` 2번(7-2절 N6) | 다른 픽셀 0(종료 0)이면 통과 |

- 포트를 바꾸려면 5번에 `OP5_PROXY_PORT=<포트>`를 앞에 붙인다. 그러면 6~9번 주소의 `8790`도 같이 바뀐다. 8768·8770·8780·8000·3000·8001, 1024 미만, 숫자가 아닌 값은 프록시가 받지 않고 “설정 오류: …”를 내고 종료 코드 2로 끝난다(`op5-proxy.mjs:17`·`:30-37`·`:171`).
- 업스트림은 `OP5_UPSTREAM`으로 바꾼다. `http://127.0.0.1|localhost|[::1]:포트`만 받는다(경로·https·다른 호스트 거부, `:38-43`).
- 끄기: 프록시 창에서 Ctrl+C, API는 d0111d8 폴더의 Makefile 절차대로.

### 0-2. 프록시 동작 (코드에서 확인, `개발/op5-proxy.mjs`, 피터 메모 `docs/T2_T5_개발메모.md` 2절)

| 항목 | 값 |
| --- | --- |
| 듣는 주소 | `127.0.0.1`만(`:174`). 기본 포트 8790(`:15`) |
| 정적 | `페이지/`를 GET·HEAD로 내보냄. `/` = `business.html`. `.`으로 시작하는 이름·`..`·인코딩된 `..`·역슬래시는 404(`:72-79`, `:152-155`) |
| API 경로 | `/api/v1/`·`/api/v2/`·`/api/v3/`·`/api/health/`만, 앞의 `/api`를 떼고 넘김(`:18`, `:117-118`). 그 밖의 `/api…`는 404, 업스트림을 부르지 않음 |
| 메서드 | GET·HEAD·POST·DELETE(`:19`). 다른 메서드는 405 |
| 넘기는 요청 헤더 | Cookie·X-CSRF-Token·X-Request-ID·Content-Type·Accept(`:21`), 다시 계산한 Content-Length(`:130`). Origin·Referer·Sec-Fetch-*·X-Forwarded-*는 넘기지 않음 |
| 돌려주는 응답 헤더 | 상태코드 그대로. Content-Type·Set-Cookie·Retry-After·X-Request-ID·Cache-Control·X-Content-Type-Options·Content-Disposition(`:22`) |
| Set-Cookie | `Domain=` 속성만 뺌(`:81-84`). Secure·HttpOnly·SameSite·Path·Max-Age는 그대로 |
| Origin 검사 | POST·DELETE에 d0111d8 `security.py:58-63`과 같은 규칙을 프록시 자기 출처(`http://127.0.0.1:<포트>`·`http://localhost:<포트>`) 기준으로 먼저 적용, 어긋나면 403 `ORIGIN_FORBIDDEN`(`:120-125`). 통과하면 Origin·Sec-Fetch-*를 빼고 넘김 → API에서 `origin` 없음·`sec-fetch-site` 없음이라 통과. **그래서 `.env`의 `API_BROWSER_ORIGINS`를 바꿀 필요가 없다** |
| Host 검사 | Host가 `127.0.0.1:<포트>`·`localhost:<포트>`가 아니면 421(`:112`) |
| 본문 상한 | 요청 1 MiB(넘으면 413 `REQUEST_TOO_LARGE`), 응답 16 MiB |
| 업스트림 오류 | 연결 실패 502 `UPSTREAM_UNREACHABLE`, 30초 초과 504 `UPSTREAM_TIMEOUT`(`:134-138`). 칸 이름은 v3이면 `detail`, 그 밖이면 `error` |
| 로그 | 시각·메서드·경로·상태만(쿠키·본문은 남기지 않음) |
| 시험 | `시험/op5_proxy.test.mjs` 12건, 가짜 업스트림 함수로만(소켓 listen 없음). **실제 `node:http` 업스트림 호출(`httpForward`, `:47-60`)은 시험하지 않았다**(7-2절 N7) |

### 0-3. 이전 길을 쓰지 않는 이유 (기록)

아래는 T6 1차에서 확인한 이전 길의 제한이다. 0-1절 프록시로 대신하므로 검사에 쓰지 않는다(U3·U4·U5).

근거: `개발/collaboration-server.py`가 실행하는 `/Users/khj/Desktop/해커톤/OriginProof-w5-a-completion/apps/web/test/local-console-server.py`(5안 밖, 읽기만 함)

| 확인한 것 | 코드에서 본 동작 | 화면에 보이는 것 |
| --- | --- | --- |
| GET이 넘어가는 경로 | `/api/v1/`, `/api/v2/`, `/api/health/`만 `proxy()`로 넘김 | `GET /api/v3/…`는 정적 파일 처리로 404 → “찾지 못했어요.” |
| POST가 넘어가는 경로 | `/api/v1/`, `/api/v2/`만 | `POST /api/v3/inputs`는 `/run-pr/` 처리로 빠져서 404 → AI 칸 “이 서버에는 분석 경로가 없어요.”, `POST /api/v3/verifications` 404 → “이 서버에는 v3 검증 경로가 없어요.”(그 뒤 v1 확인으로 넘어감) |
| DELETE | `do_DELETE` 없음(Python 기본 501) | 지우기 → “서버가 지금 처리하지 못했어요.” + “이 화면에서는 지운 것으로 보고 늦은 응답을 버려요.” |
| 응답 헤더 | `content-type`·`set-cookie`·`x-request-id`만 돌려줌 | 429가 와도 초가 빠짐 → “요청이 많아 잠시 막혔어요.” 뒤에 초 안내 없음 |
| 프록시가 보내는 곳 | `127.0.0.1:8780`(`admin-runtime.py`, 소스 커밋 `3ef1fd4`) | **d0111d8이 아니고 `make finals-up` API(8000)도 아님**(피터 문서에 없는 내용, 8절) |
| POST 출처 검사 | `Host`가 `127.0.0.1:8768`, `Origin`이 `http://127.0.0.1:8768`이어야 함 | `localhost:8768`으로 열면 POST가 403 |

다른 길도 막혀 있었다(미연결 U4·U5).
- 화면의 `연결 주소 바꾸기`로 `http://127.0.0.1:8000`(finals-up API)에 바로 붙으면 다른 출처 요청이 된다. 그런데 d0111d8 API에는 CORS 처리(CORSMiddleware)가 없고(`main.py:120` 미들웨어는 RequestSecurity 하나), `.env.example:31`의 `API_BROWSER_ORIGINS` 기본 목록에도 `http://127.0.0.1:8768`이 없다. 그래서 브라우저가 이 요청을 막는다(U5).
- 상위 폴더의 `tools/local_proxy.py`도 대신 쓸 수 없다. 이 중계는 `web-prototype/` 폴더만 내보내고(`:28` `WEB_ROOT`), GET·POST만 받으며(`:100-108`, DELETE는 기본 501), 브라우저 Cookie를 넘기지 않고(`:13`·`:33`) Set-Cookie를 돌려주지 않는다(`:34`). 그래서 로그인 세션을 만들 수 없다. 또 `X-Jjin-Target` 헤더가 없으면 403을 주는데(`:71-73`), 5안 연결 경로는 이 헤더를 보내지 않는다(`api_adapter.js:478`은 web-2안 중계 모드에서만 붙임)(U4).

T6 1차의 세 길(이전 프록시 고치기 / d0111d8용 프록시 따로 두기 / 실서버 검사 미루기) 가운데 2번이 T2 프록시로 마련됐다. 이전 프록시(5안 밖 파일)는 고치지 않았다.

판정 규칙: 본부가 0-1절 절차를 실행하기 전에는 4절 각 화면의 **장면 재현** 칸과 7절 시험만 통과·실패로 판정한다. **실서버** 칸은 "미실행"으로 적고 사유는 "프록시 파일 마련, 본부 실행 대기(U3)"로 적는다. 미실행 항목과 사유 전체는 7-2절, 본부 실측 결과는 11절 표에 있다.

---

## 1. 통합 후보

| 항목 | 값 |
| --- | --- |
| 저장소 | OriginProof(감사 복제본 `~/Desktop/2반/OriginProof-감사`, 작업 트리는 d0111d8이 아님 → 체크아웃 금지, `git show d0111d8:<경로>`로만 읽기) |
| 후보 SHA | `d0111d82490a0c30d9b36275776487ebd4ba69e8` (짧게 `d0111d8`) |
| 가리키는 가지 | `origin/phase/W6`, `origin/integration` (둘 다 이 커밋) |
| 커밋 내용 | "Merge pull request #95 from OriginProof-3web/phase/W5" (W5 승격본), 2026-10-25 01:08 +0900 |
| 화면 쪽 기준 | 5안 연결 코드 머리말: "계약 기준: OriginProof phase/W6 d0111d8"(`페이지/js/op5_client.js` 6줄) |

---

## 2. 실행 방법

### 2-1. d0111d8 API (본부 docker, 팀은 실행 금지)

감사 복제본이 아니라 d0111d8을 체크아웃한 별도 작업 폴더에서 실행한다(`Makefile`·runbook `docs/runbooks/v5_wallet_local.md` 기준).

```sh
# .env 가 없으면 .env.example 을 복사해 만든다(make bootstrap 이 하는 일과 같음)
make finals-up        # mvp-up → deploy-local → api-reload → finals-seed(P0 계정), 끝에 http://127.0.0.1:8000/health/ready 200 확인
make v5-wallet-seed   # db-upgrade(alembic 출력이 먼저 나옴) 뒤 v5 명부 합성 계정 생성, 끝에 안내 1줄 + 설정 2줄 출력(비밀값 없음, 3절)
# .env 를 바꾼 뒤에는
make api-reload
```

| 서비스 | 주소(docker-compose.yml, d0111d8) |
| --- | --- |
| API | `http://127.0.0.1:8000` (`/health/live`, `/health/ready`, `/v1`, `/v2`, `/v3`) |
| 기존 웹(Next) | `http://127.0.0.1:3000` |
| 분석기 | `http://127.0.0.1:8001` |

`.env` 항목 이름(값은 적지 않음. 출처 `.env.example`·runbook 3절·`docs/api/v5_c_runtime.md`)

| 항목 이름 | 이번 검사에서 보는 이유 |
| --- | --- |
| `API_WALLET_REGISTRY_ADDRESS` | 비우면 finals-up ready 200. 넣으면 ready 503(현재 한계). `.env.example`에는 주석으로만 있다 |
| `API_WALLET_INTERNAL_APPROVERS` | `make v5-wallet-seed` 출력 둘째 묶음을 넣는다 |
| `API_WALLET_OPERATOR_ADDRESSES` | seed 출력의 승인 지갑 자리를 Governance 배포 때 고정한 주소로 바꿔 넣는다 |
| `API_WALLET_DEMO_EMAIL_ENABLED` | 데모 메일을 쓸 때만 켠다 |
| `API_WALLET_EMAIL_SECRET` | 비밀값이다. Git·로그·문서에 남기지 않는다. `.env.example`에는 주석으로만 있다 |
| `API_WALLET_TEXT_INPUT_ENABLED` | 기본 false면 `/v3/inputs`가 409 `INPUT_SUPPORT_UNDECIDED`다. 합성 검사에서만 true |
| `API_WALLET_RELAY_ENABLED` | 기본 false(기관 지갑 직접 제출) |
| `API_SIGNER_DIRECTORY` | `test-accounts.json`이 생기는 폴더(3절) |
| `API_BROWSER_ORIGINS` | Origin 검사 목록. **T2 프록시(8790)를 쓰면 바꾸지 않는다**: 프록시가 Origin을 먼저 검사하고 빼서 넘긴다(0-2절). 기본 목록에 8768·8790이 없는 것은 그대로 둔다 |
| `API_SESSION_COOKIE_SECURE` | 기본 false로 둔다. 프록시→API는 http라 Secure가 붙지 않고 `http://127.0.0.1:8790`에 쿠키가 저장된다(피터 메모 2-2). true로 켠 검사는 하지 않는다(Q3, 9절) |
| `API_FINALS_PAYMENT_ISSUER_ID`, `API_FINALS_DOCUMENT_ISSUER_ID` | 기존 v1/v2 데모 기관이다. v5 명부 기관(`iss_origin_mock_bank`, `iss_origin_mock_office`)과 다르다 |
| `API_PORT`, `API_BLOCKCHAIN_CHAIN_ID`, `LLM_PROVIDER` | 포트·체인 domain·분석 공급자 확인용 |

ready 판정(runbook 6절): 합성 검사를 하려면 `make finals-up` + `make v5-wallet-seed`에 `API_WALLET_REGISTRY_ADDRESS`를 비워 둔다. 이 조건에서만 `/health/ready` 200을 기대한다. 주소를 넣으면 Registry가 주입되지 않은 상태라 503이 정상이다.

### 2-2. 5안 화면

| 방법 | 명령 / 여는 곳 | 쓰는 검사 |
| --- | --- | --- |
| 파일로 열기(서버 없음) | `/Users/khj/Desktop/해커톤 직원/web-5안/페이지/business.html?demo=<장면>` | 장면 재현 4개(가짜 응답이라 파일로 열어도 동작) |
| **d0111d8 실서버 검사(확정)** | `"/Users/khj/Desktop/해커톤 직원/web-5안/개발/5안 d0111d8 프록시 시작.command"` (먼저 2-1절 `make finals-up`) | 화면 `http://127.0.0.1:8790/business.html?mode=api`, 같은 출처 프록시 `http://127.0.0.1:8790/api/…` → `http://127.0.0.1:8000`. 4절 **실서버** 칸 전부. 절차는 0-1절 |
| 5안 협업 서버(d0111d8 검사에 쓰지 않음) | `"/Users/khj/Desktop/해커톤 직원/web-5안/개발/협업 테스트 시작.command"` (빌드 → `local-runtime.py` → `collaboration-server.py`) | 화면 `http://127.0.0.1:8768/business.html`, 프록시 `http://127.0.0.1:8768/api/…`는 8780(`3ef1fd4`)으로 감(0-3절, U3) |
| 모드 쿼리 | `business.html?mode=api` / `?mode=sample` | 실서버 모드 / 예시 모드로 시작 |
| 밝은 화면 | `business.html?theme=light` | 첫 화면 비교 |

T2 프록시가 쓰지 않는 포트(`op5-proxy.mjs:17` `RESERVED_PORTS`): 8768·8770·8780·8000·3000·8001. 아래 협업 서버 포트와 d0111d8 포트(2-1절 표)와 겹치지 않게 막아 둔 것이다.

`협업 테스트 시작.command`가 함께 띄우는 것(코드에서 확인한 포트, 모두 d0111d8이 아님, d0111d8 검사에 쓰지 않음)

| 포트 | 무엇 | 소스 커밋 |
| --- | --- | --- |
| 8768 | 화면 + `/api` 프록시(`local-console-server.py`) | (5안 밖 웹 소스) |
| 8780 / 8781 | 프록시가 보내는 API / 분석기(`admin-runtime.py`) | `3ef1fd4…` |
| 8770 | `local-runtime.py`가 띄우는 API(프록시는 쓰지 않음) | `121e1cad…` |
| 18545, 18546 | 로컬 EVM(Anvil 31337) | — |

화면 파일을 `file://`로 열고 `?demo` 없이 실서버 모드로 보내면 “이 화면이 파일로 열려 있어 같은 출처 /api 연결을 쓸 수 없어요. 개발/협업 테스트 시작.command 로 연 화면에서 해 주세요.”가 나온다(`op5_client.js:89`, 코드 문구 그대로). 이 안내는 옛 실행 파일 이름을 가리킨다. d0111d8 검사는 `5안 d0111d8 프록시 시작.command`로 연다. 화면 문구는 바꾸지 않았다(질문 Q2, 9절).

---

## 3. 합성 계정 (위치와 확인 방법만)

- 만드는 명령: `make v5-wallet-seed`. Makefile(d0111d8) `:142` `v5-wallet-seed: db-upgrade` → `:143` `$(COMPOSE) exec -T api uv run --no-sync --package originproof-api python scripts/fixtures/seed_accounts.py --v5-wallet`. 앞의 `db-upgrade`(`:42-43`, alembic upgrade head)가 먼저 돈다.
- 만드는 계정(`seed_accounts.py:22-30` `V5_WALLET_ACCOUNTS`, 이름은 비밀값 아님): 명부 기관 두 곳(`iss_origin_mock_bank`, `iss_origin_mock_office`)마다 신청자(`v5_bank`, `v5_office`)·내부 승인자(`v5_bank_approver`, `v5_office_approver`) — 모두 역할 issuer, 운영 승인자 3명(`v5_operator1`~`3`, 역할 operator). 다시 실행해도 기존 계정은 그대로다. 같은 이름이 다른 역할/기관으로 있으면 멈춘다(`:66` `existing account identity differs; seed stopped`, 출력이 아니라 오류).
- 비밀번호가 있는 파일: `API_SIGNER_DIRECTORY` 아래 `test-accounts.json`(권한 0600, `seed_accounts.py:161`). `.env.example:25` 기본값으로는 `build/secrets/issuer-signers/test-accounts.json`이다. docker에서는 api 컨테이너의 `/workspace/build/secrets/issuer-signers/test-accounts.json`(이름 있는 볼륨 `issuer-signers`)이다. 비밀번호는 출력하지 않는다(`:113` 주석, print 문에 없음).

seed 출력(d0111d8 `scripts/fixtures/seed_accounts.py` print 문과 한 줄씩 대조, T6)

| 줄 | 원문(파일:줄) | 실제 출력 모양 | 이 문서 이전 판 | 대조 |
| --- | --- | --- | --- | --- |
| 1 | `:163` `print("v5 wallet accounts ready; local credential file: test-accounts.json (0600)")` | “v5 wallet accounts ready; local credential file: test-accounts.json (0600)” | 같은 글 | 일치 |
| 2 | `:164` `print("\n".join(v5_wallet_env(ids)))` 의 첫 줄 = `:107` `"API_WALLET_INTERNAL_APPROVERS=" + json.dumps(approvers, separators=(",", ":"))` | `API_WALLET_INTERNAL_APPROVERS={"iss_origin_mock_bank":"acct_…","iss_origin_mock_office":"acct_…"}` (값은 각 기관 내부 승인자 계정 ID, `:101-104`) | "설정 두 줄"로만 적음 | 불일치(내용 빠짐) → 이번에 채움 |
| 3 | 같은 print 의 둘째 줄 = `:108` `"API_WALLET_OPERATOR_ADDRESSES=" + json.dumps(operators, separators=(",", ":"))` | `API_WALLET_OPERATOR_ADDRESSES={"acct_…":"<approver1 wallet address>","acct_…":"<approver2 wallet address>","acct_…":"<approver3 wallet address>"}` (키는 `v5_operator1`~`3` 계정 ID, 값은 자리표시 글자 그대로, `:105`) | "설정 두 줄"로만 적음 | 불일치(내용 빠짐) → 이번에 채움 |

- 출력 줄 수는 3줄(안내 1 + 설정 2)이다. 그 앞에 `db-upgrade`의 alembic 출력이 붙는다. `acct_…`는 실행할 때 정해지는 계정 ID라 `…`로 적었다(비밀값 아님).
- 3줄째의 `<approverN wallet address>`는 실제 주소가 아니다. runbook `v5_wallet_local.md:34`대로 Governance 배포 때 고정한 승인 지갑 주소로 바꿔 `.env`에 넣는다.
- 확인 방법(내용은 열지 않음):
  ```sh
  docker compose exec -T api ls -l /workspace/build/secrets/issuer-signers/test-accounts.json   # 있음 · -rw------- 확인
  make v5-wallet-seed   # 두 번 실행 → 같은 계정 ID·같은 설정 두 줄(runbook 6절 완료 기준 1)
  ```
- 로그인은 `business-login.html`에서 사람이 직접 한다. 기관(issuer) 계정은 로그인하면 `business.html`로 간다. 비밀번호를 채팅 입력칸에 쓰지 않는다. 화면 안내도 같다: “로그인은 기존 로그인 화면(business-login.html)에서 해요. 비밀번호는 이 대화에 쓰지 마세요.”
- 주의: 5안 협업 서버 프록시(8768 → 8780)가 받는 계정은 `admin-runtime.py`의 합성 계정이고, d0111d8의 `test-accounts.json` 계정이 아니다(0-3절). d0111d8 seed 계정은 T2 프록시 화면(`http://127.0.0.1:8790/business-login.html`)에서 로그인한다(0-1절 8번).

---

## 4. 화면별 검사 절차

공통 확인(모든 장면)
- AI 말풍선 머리 칩은 3가지 중 하나만 나온다: “예시 모드” / “실서버 모드” / “장면 재현 · 가짜 응답”.
- 오른쪽 직원 칩은 5가지만 나온다: “대기”·“확인 중”·“확인됨”·“연결 전”·“문제 찾음”.
- 첫 화면(쿼리 없음)은 연결 전과 같아야 한다. 안내 줄은 첫 보내기 전까지 “Enter 보내기 · Shift+Enter 줄바꿈 · AI 답변은 아직 연결 전이에요”다.
- 사이드바 메뉴 이름: “새 Proof 발행”·“기관 상태”·“공개키 관리”·“발행 목록”·“작업 이력”·“도움말”, 검색칸 이름표 “최근 확인 검색”.

### 4-1. 입력·결과

**장면 재현** `business.html?demo=example`(예시 모드, 서버 안 부름)

| 순서 | 누를 곳 | 기대 결과 문구 |
| --- | --- | --- |
| 1 | (자동) 변조 예시가 입력돼 보내짐 | AI 말풍선에 “블록체인 결정”·“AI 설명”·“다음 행동” 구역, AI 설명 끝 줄 “AI는 설명만 하고 발행 여부를 판정하지 않아요.” |
| 2 | 오른쪽 직원 패널 | 원본 대조관 칩 “문제 찾음”, 패널 아래 글 “예시 응답이에요. 서버에 보내지 않았어요.” |
| 3 | 입력칸 아래 안내 줄 | “Enter 보내기 · Shift+Enter 줄바꿈 · ” 뒤에 “예시 모드(예시 응답)” |
| 4 | 말풍선의 `자세히 보기` | 새 말풍선 제목 “자세히” |

**장면 재현** `business.html?demo=api`(실서버 모드 모양, 가짜 응답)

| 순서 | 누를 곳 | 기대 결과 문구 |
| --- | --- | --- |
| 1 | (자동) 글 보내기 → 분석 FAILED `ANALYZER_UNAVAILABLE` | AI 칸 “이 확인 기능은 아직 연결 전이에요.” + “서버에 분석 처리기가 없어요.” |
| 2 | (자동) 문서 ID `{"document_id":"0x…","version":1}` → INCONCLUSIVE + `CHAIN_UNAVAILABLE` | “v3 검증은 장부 연결부가 없어 연결 전이에요.”, 결론 “검증 엔진이 아직 연결 전이라 공식 기록을 확인하지 못했어요.” |
| 3 | (자동) 두 번째 글 → 429 `ANALYSIS_LIMIT`, Retry-After 600 | “요청이 많아 잠시 막혔어요.” + `600`“초 뒤에 다시 해 보세요.”(초는 응답 값) |

**실서버**(d0111d8, 화면은 `http://127.0.0.1:8790/business.html?mode=api`, 0-1절 1~8번 뒤. 상태: 미실행 — 프록시 파일 마련, 본부 실행 대기. 결과는 11절 H6)

| 순서 | 누를 곳 | 조건 | 기대 결과 문구 |
| --- | --- | --- | --- |
| 1 | 로그인 없이 입력칸에 글 → Enter | — | AI 칸 “분석은 로그인이 필요해요. 왼쪽 메뉴 기관 상태에서 로그인 화면을 열어 주세요.” |
| 2 | 기관 계정으로 로그인 후 글 → Enter | `API_WALLET_TEXT_INPUT_ENABLED` false(기본) | “서버가 입력 받기를 아직 켜지 않았어요.”(409 `INPUT_SUPPORT_UNDECIDED`) |
| 3 | 같은 글 → Enter | 위 값 true(합성 검사), 분석기 미주입 | “서버에 분석 처리기가 없어요.”(FAILED `ANALYZER_UNAVAILABLE`), 결과 말풍선 “보관” 구역에 분석 번호 `ana_…` |
| 4 | 10분 안에 분석 6건째 또는 진행 중 1건이 있을 때 | — | “요청이 많아 잠시 막혔어요.” + `<Retry-After 값>`“초 뒤에 다시 해 보세요.”(T2 프록시는 `Retry-After`를 돌려준다, `op5-proxy.mjs:22`. 초는 서버 응답 값) |
| 5 | 문서 ID JSON 보내기 | Registry 주소 비움 / 넣음 | 비움: “v3 검증은 장부 설정이 없어 연결 전이에요.”(503 `WALLET_REGISTRY_NOT_CONFIGURED`). 넣음: “v3 검증은 장부 연결부가 없어 연결 전이에요.”(INCONCLUSIVE+`CHAIN_UNAVAILABLE`) |
| 6 | `＋`로 파일 첨부 후 글 보내기 | — | “개는 서버로 보내지 않았어요. 첨부 업로드는 아직 연결 전이에요(서버 계약에 업로드 경로 없음).”(앞에 `첨부 N`) |
| 7 | 답이 오기 전에 같은 글을 한 번 더 보내기 | — | “같은 내용을 이미 확인하고 있어요. 결과가 나오면 여기에 보여 드려요.” — 서버 접수 기록 1건 |

### 4-2. 지갑

**장면 재현** `business.html?demo=wallet`(가짜 지갑)

| 순서 | 누를 곳 | 기대 결과 문구 |
| --- | --- | --- |
| 1 | (자동) 사이드바 `새 Proof 발행` | 제목 “새 Proof 발행(기관 지갑)”, 첫 줄 “1. 발행 초안 보내기(document-drafts)”, 다섯째 줄 “5. 작업 확인 — UNKNOWN 이면 다시 보내지 않고 복구 조회(reconcile)”, 단추 `예시 초안을 입력칸에 넣기`·`초안 보내기 시작` |
| 2 | (자동) `공개키 관리` | “등록된 키가 없어요.”, 단추 `지갑 키 증명 시작(key-challenges → key-proofs)` |
| 3 | (자동) 그 단추 | “지갑 키 증명” 아래 ✓ “기관 신청 번호 확인: ” `app_scene` → ✓ “지갑 연결: ” `0x1111…1111` → ✕ “서버에 블록체인 장부(Registry) 연결부가 아직 붙지 않았어요. 체인을 조회하는 지갑 기능은 연결된 뒤에 쓸 수 있어요.” `(코드: WALLET_REGISTRY_UNAVAILABLE · HTTP 503)` |

주의: d0111d8 실서버의 `key-challenges`는 Registry를 조회하지 않는다. 그래서 실서버에서는 3번이 이 장면과 다르게 나온다(아래 표 2번, 8절).

**실서버**(같은 화면 `http://127.0.0.1:8790/business.html?mode=api`. 상태: 미실행 — 프록시 파일 마련, 본부 실행 대기. 결과는 11절 H8)

| 순서 | 누를 곳 | 조건 | 기대 결과 문구 |
| --- | --- | --- | --- |
| 1 | 지갑 확장 없는 브라우저에서 `공개키 관리` 또는 `새 Proof 발행` | — | 제목 “지갑 필요”, “이 브라우저에는 지갑(window.ethereum)이 없어요. 서명은 기관 지갑에서만 하고, 서버에는 개인키를 보내지 않아요.” |
| 1-1 | seed 계정(`v5_bank`)으로 로그인, 기관 확인 안 함 → `공개키 관리` → `지갑 키 증명 시작…` | 기관 신청 없음(U2) | ✕ “이 계정의 기관 신청 번호(app_…)를 찾지 못했어요.” `(코드: APPLICATION_NOT_FOUND)` (`/v1/issuer-applications/mine`이 빈 값) |
| 1-2 | 같은 계정 → `새 Proof 발행` → 초안 보내기 | 기관 신청 없음 또는 메일·내부 승인 안 끝남(U2) | ✕ “기관 확인(명부·메일·내부 승인)이 먼저 끝나야 해요.” `(코드: INSTITUTION_CHECKS_REQUIRED · HTTP 409)` — Registry 단계(R2)보다 먼저 남(`wallet_documents.py:73-75`) |
| 2 | 지갑 있는 브라우저 → `공개키 관리` → `지갑 키 증명 시작…` | 기관 확인 끝남 + Registry 주소 비움 | ✕ “서버에 장부(Registry) 주소가 설정되지 않았어요.” `(코드: WALLET_REGISTRY_NOT_CONFIGURED · HTTP 503)` (R1, `wallet_governance.py:52`) |
| 2′ | 같음 | 기관 확인 끝남 + Registry 주소 넣음 | 지갑 서명 창 → ✓ “키 증명을 서버가 받았어요. 이제 운영자가 등록 제안을 준비해요.” |
| 3 | `새 Proof 발행` → `예시 초안을 입력칸에 넣기` → `초안 보내기 시작` → 입력칸 Enter | 기관 확인 끝남 + Registry 미주입(주소 비움·넣음 둘 다, R2가 주소 검사보다 먼저) | ✕ “서버에 블록체인 장부(Registry) 연결부가 아직 붙지 않았어요. 체인을 조회하는 지갑 기능은 연결된 뒤에 쓸 수 있어요.” `(코드: WALLET_REGISTRY_UNAVAILABLE · HTTP 503)` (R2) |
| 4 | 다른 지갑 주소로 서명 단계까지 감 | — | “연결한 지갑 주소가 서명 요청의 기관 지갑 주소와 달라요. 등록한 기관 지갑으로 바꿔 주세요.” |
| 5 | 지갑 창에서 거절 | — | “지갑에서 연결을 거절했어요.” / “지갑에서 서명을 거절했어요.” |
| 6 | 거래 해시 칸에 틀린 값 | — | “거래 해시는 0x + 16진수 64자리예요.” |

### 4-3. 보관·삭제

**장면 재현** `business.html?demo=retention`

| 순서 | 누를 곳 | 기대 결과 문구 |
| --- | --- | --- |
| 1 | (자동) 사이드바 `작업 이력` | “이 탭에서 만든 지갑 작업(v3)” · “아직 없어요.”, 단추 `내 확인 기록(보관한 분석) 보기`·`보관 선택 바꾸기`, “서버 작업 이력(v1)” · “작업이 없어요.” |
| 2 | (자동) 내 확인 기록 | “내 확인 기록” 2줄(`ana_scene_keep1`, `ana_scene_keep2`), 단추 `보고서 받기 …`·`원본 받기 ana_scene_keep1`·`지우기 …` |
| 3 | (자동) `ana_scene_keep2` 지우기 | “분석 ” `ana_scene_keep2` “를 지웠어요. 이 분석에 늦게 오는 응답은 쓰지 않고 버려요.” |
| 4 | (자동) 다시 목록 | “내 확인 기록” 1줄(`ana_scene_keep1`만) |

**실서버**(같은 화면 `http://127.0.0.1:8790/business.html?mode=api`, 기관 계정 로그인, `API_WALLET_TEXT_INPUT_ENABLED` true. 상태: 미실행 — 프록시 파일 마련, 본부 실행 대기. 결과는 11절 H7)

| 순서 | 누를 곳 | 기대 결과 문구 |
| --- | --- | --- |
| 1 | `작업 이력` → `보관 선택 바꾸기` | “보관 선택(다음 분석부터)” · `retain_report ` “끔(끝난 뒤 10분)” ` · retain_original ` “끔(처리 직후 삭제)”(기본) |
| 2 | `보고서 보관 켜기/끄기`, `원본 보관 켜기/끄기` | 줄이 “켬(7일)”로 바뀜 |
| 3 | 글 분석 1건 보내기 → `작업 이력` → `내 확인 기록(보관한 분석) 보기` | 목록 줄 `ana_… · <상태> · 보고서 보관 · 원본 보관`. 없으면 “보관 중인 분석이 없어요. 보관을 켜고 분석하면 여기에 남아요(보고서 7일).” |
| 4 | `지우기 ana_…` 한 번 | 단추 글이 “정말 지울까요? 한 번 더 누르기”로 바뀜 |
| 5 | 한 번 더 | 204 → “를 지웠어요. 이 분석에 늦게 오는 응답은 쓰지 않고 버려요.” 지운 뒤 늦게 온 응답은 “지운 분석이라 늦게 온 응답은 버렸어요.” |
| 6 | 완료된 분석의 `보고서 받기` / `원본 받기` | “보고서를 내려받았어요(” `ana_…-report.json` / “원본을 내려받았어요(” `ana_….txt`. 기한이 지났으면 “결과 보관 시간이 지나 더는 볼 수 없어요.” / “원본을 보관하지 않았거나 보관 시간이 지났어요.” |

주의: 분석기가 주입되지 않으면 분석은 모두 FAILED다. 그래서 실서버에서 COMPLETED 보고서·원본 내려받기(6번)는 분석기를 연결하기 전에는 확인할 수 없다(7-2절 N2). T2 프록시는 `GET /api/v3/analyses…`와 `DELETE /api/v3/analyses/{id}`를 넘기고 204를 그대로 돌려준다(`op5-proxy.mjs:19`·`:146`). 이전 협업 서버(8768)로 열면 3번은 “찾지 못했어요.”, 지우기는 501이 났다(0-3절).

### 4-4. 연결 설정·상태 (사이드바 `기관 상태`)

장면 재현은 `?demo=api`의 첫 말풍선이다(가짜 live 200 / ready 503).

실서버는 같은 화면 `http://127.0.0.1:8790/business.html?mode=api`에서 본다. 상태: 미실행 — 프록시 파일 마련, 본부 실행 대기. 결과는 11절 H5.

| 순서 | 누를 곳 | 기대 결과 문구 |
| --- | --- | --- |
| 1 | `기관 상태` | 제목 “연결 설정”: “지금 모드: ” + “예시 모드” 또는 “실서버 모드”, “연결 주소: ” `/api` “ (같은 출처 프록시)”, 보관 선택 줄 |
| 2 | 같은 말풍선 “서버 상태(/health/live · /health/ready)” | live “서버 프로그램이 켜져 있어요.” `(HTTP 200)`. ready는 “검증 서버가 준비돼 있어요.” `(HTTP 200)` 또는 “서버는 켜져 있지만 아직 준비가 안 됐어요(계정·장부 연결 등 준비 항목이 남음). 꺼진 것과는 달라요.” `(HTTP 503 RUNTIME_NOT_READY)` |
| 3 | 로그인 안 한 상태 | “로그인” 구역에 “로그인이 필요해요.” + “로그인은 기존 로그인 화면(business-login.html)에서 해요. 비밀번호는 이 대화에 쓰지 마세요.”, 단추 `로그인 화면 열기` |
| 4 | 로그인한 상태(기관) | “로그인” 구역 `<계정> · 역할 issuer · 기관 <issuer_id>`, “기관 상태(/v1/issuer/status · 신청)” 구역, 단추 `로그아웃` → “로그아웃했어요.” |
| 5 | `실서버 모드로 바꾸기` / `예시 모드로 바꾸기` | “실서버 모드로 바꿨어요. 연결 주소 ” `/api` “ 로 보내요.” / “예시 모드로 바꿨어요. 서버에 보내지 않고 예시 응답만 보여요.” |
| 6 | `연결 주소 바꾸기` → 입력칸에 `https://example.com` | “주소는 같은 출처 경로(예: /api) 또는 이 컴퓨터 주소(예: http://127.0.0.1:8000)만 받아요.” |
| 7 | 같은 단추 → `http://127.0.0.1:8000` | “연결 주소를 ” … “ 로 바꿨어요.” + “ 다른 주소는 서버가 이 화면 주소를 허용(CORS·Origin)해야 해요.”(d0111d8은 CORS가 없어 실제 요청은 막힘, 0절) |
| 8 | 프록시는 켜고 d0111d8 API(8000)만 끈 채 `연결 다시 확인` | 프록시가 502 `UPSTREAM_UNREACHABLE`(`op5-proxy.mjs:137`)을 주고, 화면은 5xx 일반 문구를 보인다: `live: ` + “서버가 지금 처리하지 못했어요.” + ` (HTTP 502)`, `ready: ` + “서버가 지금 처리하지 못했어요.” + ` (HTTP 502 UPSTREAM_UNREACHABLE)`(`op5_client.js:96`·`:231`·`:235`). 이전 판의 기대 문구 “서버에 닿지 못했어요…”와 다르다(질문 Q1, 화면 코드는 바꾸지 않음) |
| 8′ | 프록시까지 끈 채 `연결 다시 확인` | 요청이 닿지 않아 fetch 실패 → “서버에 닿지 못했어요. 서버가 꺼져 있거나 연결 주소가 틀렸어요.”(`op5_client.js:85-89`) |
| 9 | 예시 모드에서 `작업 이력` / 검색칸 | “예시 모드라 서버 작업 목록은 부르지 않아요.” / “지금은 예시 모드라 서버에 보내지 않아요. 실서버 모드에서 실제 서버로 보내요.” |
| 10 | 사이드바 `도움말` | 알림창 없이 말풍선 제목 “도움말”, 단추 `예시 문자를 입력칸에 넣기` |

T2 프록시(8790)로 열면 2번은 d0111d8 API(8000)의 `/health/live`·`/health/ready`다(`/api/health/`를 넘김, `op5-proxy.mjs:18`). 이전 협업 서버(8768)로 열면 8780(`3ef1fd4`) 서버의 상태가 나오므로 그 화면으로 판정하지 않는다(0-3절).

### 4-5. 데모 쿼리 정리

| 쿼리 | 모드 | 장면 | 캡처 예약 이름(피터 5절) |
| --- | --- | --- | --- |
| `?demo=example` | 예시 | 변조 예시 결과(4-1) | `5안-연결-예시결과-{pc1440,휴대폰390}` |
| `?demo=api` | 실서버 모양(가짜) | 기관 상태 → 분석 연결 전 → 검증 연결 전 → 429(4-1·4-4) | `5안-연결-실서버연결전-…` |
| `?demo=wallet` | 실서버 모양(가짜 지갑) | 발행 단계 → 공개키 → 키 증명 ✕ 503(4-2) | `5안-연결-지갑단계-…` |
| `?demo=retention` | 실서버 모양(가짜) | 작업 이력 → 내 확인 기록 2건 → 1건 지움(4-3) | `5안-연결-보관삭제-…` |
| (없음) / `?theme=light` | — | 첫 화면 그대로 | T5 예약 `5안-T5-첫화면-{어두운,밝은}모드-pc1440x820`(기준과 같은 1440×820, 7-2절 N6). 이전 예약 `5안-연결후-첫화면-…-pc1440`은 1440×900이라 기준과 비교하지 않음(Q4) |

장면은 저장소(localStorage·sessionStorage)에 아무것도 남기지 않는다. 그 밖의 `demo` 값은 무시된다.

---

## 5. 미연결 기준표와 화면 문구

### 5-1. 미연결 기준표 (원본, U1~U9 · 9개)

- 계약 근거는 d0111d8을 `git show d0111d8:<경로>`로 읽은 줄 번호다. 계약 밖(프록시)은 그 파일 경로를 적었다.
- 화면 문구는 `페이지/` 코드 문자열 그대로다. 코드가 문구 뒤에 붙이는 코드 줄은 “ ” 밖 `( )`로 적었다.
- 검수 방법: 각 행의 "화면 위치"를 눌러 "정확한 문구"가 그대로 나오는지 본다. 실서버가 필요한 행은 본부가 A 문서 0-1절 절차를 실행하기 전까지 미실행(7-2절), 실측 결과는 A 문서 11절.

| ID | 이름 | 원인(근거 파일:줄) | 화면 위치 | 화면에 보이는 정확한 문구(코드 위치) | 상태(T6 2차) |
| --- | --- | --- | --- | --- | --- |
| U1 | 공개 체인 없음 | d0111d8 `.env.example:7`·`:10`(`API_BLOCKCHAIN_RPC_URL=http://anvil:8545`, `API_BLOCKCHAIN_CHAIN_ID=31337`), `docker-compose.yml:27-30`(anvil `--chain-id 31337`), `docs/runbooks/v5_wallet_local.md:8`(실제 Registry 연결 아직 안 됨)·`:53`(합성 Registry 결과를 실제 체인 연결 성공으로 보고하지 않음). 공개 테스트넷·메인넷 설정 없음 | 사이드바 `기관 상태` 말풍선의 “기관 상태(/v1/issuer/status · 신청)” 구역 한 줄 | 전용 문구 없음. 줄 모양 `기관 … · 상태 … · 체인 …`(`op5_connect.js:341`, 체인 칸에 응답 `chain_id`가 들어감) | 계약 한계 그대로. 화면에 알릴지 대표 결정 대기(9절 4) |
| U2 | 기관 확인(신청·메일 확인·내부 승인 = 인준/검토) 화면 없음 | d0111d8 `apps/api/src/originproof_api/applications.py:46`(`POST /v1/issuer-applications`), `wallet_onboarding.py:98`·`:149`·`:169`·`:212`(`email-codes`·`demo-inbox`·`email-verifications`·`internal-approvals`), `:241-247`(안 끝나면 409 `INSTITUTION_CHECKS_REQUIRED`), `wallet_governance.py:46`(key-challenges 앞), `wallet_documents.py:73-75`(document-drafts·revoke-drafts 앞). 5안 연결 코드는 이 쓰기 경로를 하나도 부르지 않음 | 사이드바 `기관 상태` 말풍선 / `공개키 관리` → `지갑 키 증명 시작(key-challenges → key-proofs)` ✕ 줄 / `새 Proof 발행` 초안 ✕ 줄 | “기관 신청 기록이 없어요.”(`op5_connect.js:344`) · ✕ “이 계정의 기관 신청 번호(app_…)를 찾지 못했어요.” (코드: APPLICATION_NOT_FOUND)(`op5_client.js:386`) · ✕ “기관 확인(명부·메일·내부 승인)이 먼저 끝나야 해요.” (코드: INSTITUTION_CHECKS_REQUIRED · HTTP 409)(`op5_client.js:40`) | 미연결 그대로. 기관 확인을 끝낼 수단 본부 결정 대기(9절 3). 실서버 확인 미실행 |
| U3 | 5안 협업 서버 프록시(8768) 제한: `/api/v3/`·DELETE·`Retry-After`를 넘기지 않고, 보내는 곳이 d0111d8이 아님 → T2 같은 출처 프록시(8790)로 대신함 | 5안 밖 `/Users/khj/Desktop/해커톤/OriginProof-w5-a-completion/apps/web/test/local-console-server.py`(`개발/collaboration-server.py:9`가 실행): `:541`·`:566-568`(GET은 `/api/v1/`·`/api/v2/`·`/api/health/`만), `:577`·`:584`(POST는 `/api/v1/`·`/api/v2/`만), `do_DELETE` 없음(Python 기본 501), `:374`(돌려주는 헤더 content-type·set-cookie·x-request-id만), `:367`(보내는 곳 `127.0.0.1:8780`). 대신 쓰는 것: `개발/op5-proxy.mjs` `:18`·`:19`(`/api/v1/`·`/api/v2/`·`/api/v3/`·`/api/health/` × GET·HEAD·POST·DELETE), `:22`(Retry-After·Set-Cookie·X-Request-ID 반환), `:16`(기본 업스트림 `http://127.0.0.1:8000`), `:174`(127.0.0.1만 listen) | AI 설명 칸 / 검증 칸 / 오류 줄 / `지우기` / 429 결과 | “이 서버에는 분석 경로가 없어요.”(`api_adapter.js:661`) · “이 서버에는 v3 검증 경로가 없어요.”(`api_adapter.js:644`) · “찾지 못했어요.”(`op5_client.js:62`, GET 404) · “서버가 지금 처리하지 못했어요.” + “이 화면에서는 지운 것으로 보고 늦은 응답을 버려요.”(`op5_client.js:96`, `op5_connect.js:266`, DELETE 501) · “요청이 많아 잠시 막혔어요.”(`api_adapter.js:450`, 초 안내 없음) — 이상 8768로 열 때. T2 프록시(8790)에서는 v3·DELETE·Retry-After가 넘어가 이 문구들이 나오지 않아야 한다. 대신 업스트림(8000)이 꺼지면 502 `UPSTREAM_UNREACHABLE` → “서버가 지금 처리하지 못했어요.”(`op5_client.js:96`, 질문 Q1) | **프록시 파일 마련, 본부 실행 대기** |
| U4 | 상위 `tools/local_proxy.py` 제한: 5안을 내보내지 않고 로그인 쿠키를 넘기지 않음 | `../tools/local_proxy.py:28`(`WEB_ROOT` = `web-prototype`), `:100-108`(GET·POST만, DELETE는 기본 501), `:13`·`:33`(넘기는 헤더 Content-Type·Accept·X-Request-ID·X-CSRF-Token — Cookie 없음), `:34`(돌려주는 헤더 Content-Type·Retry-After·X-Request-ID — Set-Cookie 없음 → 로그인 세션 못 만듦), `:71-73`(`X-Jjin-Target` 없으면 403 `TARGET_NOT_ALLOWED`). 5안 연결 경로는 이 헤더를 보내지 않음(`api_adapter.js:478`은 중계 모드만, 5안 `callBase` `:503-519`). v3 경로(`:30`)·Retry-After는 넘김 | 없음(5안 화면이 이 중계로 열리지 않음) | 화면 문구 없음. `api_adapter.js:547-549`의 `tools/local_proxy.py` 안내 3개는 web-2안 중계 모드 문구라 5안 연결(`opts.base`) 경로에서는 나오지 않음 | 쓰지 않음(U3의 T2 프록시로 대신). 본부 조치 없음 |
| U5 | `연결 주소 바꾸기`로 d0111d8 API에 바로 붙기(다른 출처) 막힘 | d0111d8 `apps/api/src/originproof_api/main.py:120`(미들웨어는 RequestSecurity 하나, CORSMiddleware 없음), `.env.example:31`(`API_BROWSER_ORIGINS` 기본 목록 :3000·:8000만) | `기관 상태` 말풍선 → `연결 주소 바꾸기` → 입력칸 / 그 뒤 오류 줄 | “다른 주소는 서버가 이 화면 주소를 허용(CORS·Origin)해야 해요.”(`op5_connect.js:321`, 바꾼 직후) · “서버에 닿지 못했어요. 서버가 꺼져 있거나 연결 주소가 틀렸어요.”(`op5_client.js:90`, 브라우저가 막은 뒤) | 쓰지 않음(T2 프록시가 같은 출처로 붙임, `API_BROWSER_ORIGINS` 변경 불필요). 직접 연결이 막히는 것은 그대로 |
| U6 | Registry(체인 장부) 미주입 | d0111d8 `main.py:189`(`app = create_app()`)·`:75`(`wallet_chain=None`), `wallet_runtime.py:42-52`·`:78-79`, runbook `v5_wallet_local.md:8`·`:63`. 단계별 코드·엔드포인트는 5-2절 R1~R5 | 지갑 단계 ✕ 줄 / 검증 칸 / 검색칸(0x…) / `기관 상태` 서버 상태 | 5-2절 "5안 화면 문구" 칸(R1~R5) | 서버 미주입 그대로. 실서버 문구 확인 미실행(본부 실행 대기) |
| U7 | 분석기 미주입 | d0111d8 `main.py:76`(`analysis_processor=None`)·`:189`, `wallet_analyses.py:159-160`(처리기 없으면 분석 FAILED, `error` = `ANALYZER_UNAVAILABLE` — HTTP 오류가 아니라 분석 결과 상태) | 결과 말풍선 `AI 설명` 칸 / 오른쪽 AI 직원 칩 “연결 전” | “이 확인 기능은 아직 연결 전이에요.” + “서버에 분석 처리기가 없어요.”(`api_adapter.js:186`이 한 칸에 이어 붙임, `:409`). `op5_client.js:17`의 “서버에 AI 분석기가 아직 연결되지 않았어요.”는 HTTP 오류 코드 표라 이 흐름에서는 보이지 않음 | 서버 미주입 그대로. 실서버 문구 확인 미실행(본부 실행 대기) |
| U8 | 이미지·PDF·음성 업로드 없음 | d0111d8 `packages/python/originproof_core/wallet_contract.py:489-491`(`TextInputRequest.kind: Literal["TEXT"]`), `docs/api/v5_c_runtime.md:28`(이미지/PDF/STT 비활성) | 결과 말풍선 / 첨부 패널 / `도움말` 말풍선 / 업로드 자리 | “첨부 업로드는 아직 연결 전이에요(서버 계약에 업로드 경로 없음).”(`op5_connect.js:161`, 앞에 `첨부 N개는 서버로 보내지 않았어요.`) · “첨부는 이 브라우저 안에만 있어요. 서버 업로드·이미지 글자 읽기·음성 받아쓰기는 아직 연결 전이에요.”(`business.html:174`) · “· 첨부: 이 브라우저 안에만 있어요. 서버 업로드는 아직 연결 전이에요.”(`op5_connect.js:473`) · `UPLOAD_NOT_CONNECTED`: “첨부 업로드는 아직 연결 전이에요(서버 계약에 업로드 경로가 없어요).”(`op5_client.js:459`) | 계약에 업로드 경로 없음, 그대로 |
| U9 | 글 입력 받기 꺼짐(서버 기본값) | d0111d8 `settings.py:38`(`wallet_text_input_enabled = False`), `.env.example:50`, `wallet_analyses.py:215`(`/v3/inputs`)·`:259`(`/v3/analyses`) → 409 `INPUT_SUPPORT_UNDECIDED` | 결과 말풍선 `AI 설명` 칸 | “서버가 입력 받기를 아직 켜지 않았어요.”(`api_adapter.js:662`). `op5_client.js:34`의 “서버가 글 입력 받기를 아직 켜지 않았어요.”는 분석 흐름에서는 보이지 않음 | 서버 기본값 그대로. 합성 검사는 `.env`로 켬(0-1절 1번). 실서버 확인 미실행 |

### 5-2. Registry 오류 단계와 5안 화면 문구의 차이 (R1~R5 · 5개, U6 세부)

| ID | 코드 | HTTP | 계약 근거(d0111d8) | 나는 엔드포인트와 조건 | 5안 화면 문구(위치) | 차이 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | `WALLET_REGISTRY_NOT_CONFIGURED` | 503 | `wallet_runtime.py:42-44`(`domain` 속성, `API_WALLET_REGISTRY_ADDRESS` 비었을 때) | 주소 비움 + domain을 읽는 곳: `POST /v3/verifications`(`wallet_documents.py:557`·`:580`, 체인 503은 `:534-543`에서 먼저 잡힌 뒤), `POST /v3/key-challenges`(`wallet_governance.py:52`, 단 `:46` 기관 확인 409가 먼저), `POST /v3/key-proofs`(`wallet_runtime.py:154`). document-drafts·revoke-drafts·`GET /v3/documents`는 R2가 먼저라 이 코드까지 안 감 | 검증 칸 “v3 검증은 장부 설정이 없어 연결 전이에요.”(`api_adapter.js:636`, 그 뒤 v1 확인) / 지갑 ✕ “서버에 장부(Registry) 주소가 설정되지 않았어요.” (코드: WALLET_REGISTRY_NOT_CONFIGURED · HTTP 503)(`op5_client.js:16`) | 키 증명에서 이 줄은 기관 확인(U2)이 끝난 뒤에만 보인다. 화면은 "주소 없음"만 말하고, 주소를 넣어도 R2가 남는다는 것은 말하지 않음 |
| R2 | `WALLET_REGISTRY_UNAVAILABLE` | 503 | `wallet_runtime.py:50-52`(체인 객체 없음), `:78-79`(RPC 시간 초과·증거 불일치) | 주소 유무와 무관(체인 검사가 주소 검사보다 먼저). `rpc`를 부르는 곳 전부: `POST /v3/document-drafts`·`revoke-drafts`(`wallet_documents.py:76`, 단 `:73-75` 기관 확인 409가 먼저), `publications`·`revocations`(`:250`·`:254`·`:287`), `POST /v3/operations/{id}/reconcile`(`:402`), `GET /v3/documents/{id}`(`:436`), `GET …/verification-material`(`:473`), proposals 계열(`wallet_runtime.py:104`, 승인 지갑 설정이 없으면 403 `APPROVER_REQUIRED`가 먼저). `POST /v3/verifications`에서는 잡혀서 R3이 됨 | 지갑 ✕ 줄 / 검색칸 0x… 오류 줄: “서버에 블록체인 장부(Registry) 연결부가 아직 붙지 않았어요. 체인을 조회하는 지갑 기능은 연결된 뒤에 쓸 수 있어요.”(`op5_client.js:15`) + (코드: WALLET_REGISTRY_UNAVAILABLE · HTTP 503) | 같은 코드가 Registry를 붙인 뒤의 RPC 시간 초과·증거 불일치(`:78-79`)에서도 나지만 화면은 늘 "아직 붙지 않았어요"라고 말함. `?demo=wallet`은 key-challenges에서 이 코드를 보이지만 계약의 key-challenges는 `rpc`를 부르지 않음(`wallet_governance.py:37-62`, 8절 4) |
| R3 | `CHAIN_UNAVAILABLE`(검증 사유) | 200 | `wallet_documents.py:534-543`(체인 503을 잡아 `unavailable=True`) → `packages/python/originproof_core/wallet_verification.py:98-100`(`current_state` UNAVAILABLE, 결과 INCONCLUSIVE) | `POST /v3/verifications`, 주소 넣음 + 체인 미주입(주소를 비우면 R1) | 검증 칸 “v3 검증은 장부 연결부가 없어 연결 전이에요.”(`api_adapter.js:640`, 그 뒤 v1 확인), 결론 “검증 엔진이 아직 연결 전이라 공식 기록을 확인하지 못했어요.” | 오류가 아니라 200 결과 안 `reason_codes`의 사유. RPC 시간 초과 때도 같은 사유인데 화면은 "연결부가 없어"로 말함 |
| R4 | `RUNTIME_NOT_READY` | 503 | `readiness.py:52-58`(주소가 있으면 기관마다 `rpc("issuer")` → R2) → `:80-81` | `GET /health/ready`, 주소 넣음 + 체인 미주입(runbook `:63` "현재 한계"), 그 밖의 준비 항목 미충족도 같은 코드 | `기관 상태` 말풍선 “서버 상태(/health/live · /health/ready)” 구역: `ready: ` + “서버는 켜져 있지만 아직 준비가 안 됐어요(계정·장부 연결 등 준비 항목이 남음). 꺼진 것과는 달라요.” + ` (HTTP 503 RUNTIME_NOT_READY)`(`op5_client.js:18`·`:234`, `op5_connect.js:326`) | 원인을 구분하지 않음(계약도 코드 하나). "장부 연결" 원인인지는 화면만으로 알 수 없음 |
| R5 | `CHAIN_UNAVAILABLE`(기존 v1 체인) | 503 | `chain_management.py:535`·`:596`·`:615`(기존 Anvil 읽기 실패) | `GET /v1/issuer/status`, `GET /v1/issuer/keys`, `GET /v1/issuer/keys/{id}`. v3 Registry와 별개 | `기관 상태`·`공개키 관리` 오류 줄: “블록체인에 연결하지 못했어요.” + `코드: CHAIN_UNAVAILABLE · HTTP 503`(`op5_client.js:54`, `op5_connect.js:109`) | 같은 이름 `CHAIN_UNAVAILABLE`이 R3(200 사유)과 R5(503 오류) 두 곳에 있고 화면 문구도 다르다. 검수 때 어느 엔드포인트인지로 구분 |

### 5-3. 이전 번호와의 대응

| 이 문서 이전 5절 | 새 ID |
| --- | --- |
| 0 (5안 프록시) | U3 |
| 1 / 1-a / 1-b (Registry) | U6 = R2 / R1 / R3 |
| 2 (분석기) | U7 |
| 3 (입력 받기 꺼짐) | U9 |
| 4 (업로드) | U8 |
| 5 (공개 체인) | U1 |
| (없음, 이번에 더함) | U2(8절 5에서 옮김), U4, U5(0절에서 옮김), R4, R5 |

### 5-4. 자리 없음(피터 6절, 14개)과의 관계

자리 없음은 **별개 범주**다. 자리 없음은 "디자인에 그 칸이 없어 기존 모양으로 대신했고 기능은 동작함"이고, 미연결(U)은 "서버·계약·실행 환경 때문에 기능이 동작하지 않음"이다. 그래서 U 개수에 자리 없음은 넣지 않았다. 겹치는 곳만 적는다.

| 자리 없음 # | 관계 |
| --- | --- |
| 13 첨부 업로드 | U8과 같은 원인(계약에 업로드 경로 없음). 자리 없음 쪽은 "업로드 자리 함수만 둠", U8은 "화면에 연결 전 문구" |
| 11 지갑 거래 보내기 | 계약에 화면용 calldata 규칙이 없음. 다만 거래 해시를 입력칸으로 받는 대신 길이 있어 미연결로 세지 않음 |
| 12 v3 발행 문서 목록 | 계약에 목록 경로가 없음. 검색칸에 문서 ID로 대신 찾을 수 있어 미연결로 세지 않음 |
| 그 밖 1~10, 14 | U와 관계없음(화면 모양 대체) |

---

## 6. 피터 결과 문서 목록과의 대조 (항목·개수)

### 6-1. 자리 없음 (피터 6절, 14개 — 같은 번호)

| # | 항목 | 대신 쓴 방법 | 검사 절차 |
| --- | --- | --- | --- |
| 1 | 화면 위 "지금 모드" 칩 | 말풍선 머리 `.tag-offline` 칩 + `#composerHint` | 4 공통, 4-1 |
| 2 | 연결 설정 화면 | 기관 상태 말풍선 단추 + 입력칸으로 주소 받기, `?mode=` | 4-4 |
| 3 | 결과 카드(두 구역) | AI 말풍선 안 글 구성 | 4-1 |
| 4 | 지갑 단계 카드 | ✓/✕ 줄 + `.add-btn` | 4-2 |
| 5 | 보관/삭제 "내 확인 기록" 카드 | 사이드바 `작업 이력` 말풍선 | 4-3 |
| 6 | 로그인 입력칸 | `business-login.html` 단추 | 4-4 3번 |
| 7 | 직원 칩 `보류`·`해당 없음` | `대기` 칩 + 아래 줄 사유 | 4 공통 |
| 8 | `문제 찾음` 전용 색 | `st st-run`(확인 중과 같은 색) | 4-1 장면 2번 |
| 9 | 말풍선 안 작은 단추 | `.add-btn`(폭 100%) | 4-2·4-3 |
| 10 | '자세히' 펼침 칸 | `자세히 보기` → 새 말풍선 | 4-1 장면 4번 |
| 11 | 지갑 거래 보내기(eth_sendTransaction) | 거래 해시를 입력칸으로 받음 | 4-2 6번 |
| 12 | v3 발행 문서 목록 | v2 목록 + 검색칸에 문서 ID | 4-4(검색칸) |
| 13 | 첨부 업로드 | "연결 전" 유지 + `Hk.op5.uploadAttachment` 자리 | U8(5-4절) |
| 14 | 도움말 | 바깥 click capture → 말풍선 | 4-4 10번 |

개수: 피터 14 = 이 문서 14.

### 6-2. 연결 전 사유 (피터 8-4, 7개 — 검증·분석 칸)

| # | 문구 | 응답 | 이 문서 |
| --- | --- | --- | --- |
| 1 | “v3 검증은 장부 설정이 없어 연결 전이에요.” | 503 `WALLET_REGISTRY_NOT_CONFIGURED` | U6 · R1 |
| 2 | “v3 검증은 장부 연결부가 없어 연결 전이에요.” | INCONCLUSIVE+`CHAIN_UNAVAILABLE` | U6 · R3 |
| 3 | “이 서버에는 v3 검증 경로가 없어요.” | 404/405 | 0절 · U3 |
| 4 | “서버에 분석 처리기가 없어요.” | `ANALYZER_UNAVAILABLE` | U7 |
| 5 | “분석은 로그인이 필요해요. 왼쪽 메뉴 기관 상태에서 로그인 화면을 열어 주세요.” | 401/403 | 4-1 실서버 1번(미연결 아님, 로그인 안내) |
| 6 | “이 서버에는 분석 경로가 없어요.” | 404/405 | 0절 · U3 |
| 7 | “서버가 입력 받기를 아직 켜지 않았어요.” | 409 `INPUT_SUPPORT_UNDECIDED` | U9 |

첨부 "연결 전" 문구(피터 8-5) 3개는 U8에 모두 있다(U8에는 `도움말` 첨부 줄 1개를 더해 4개). 개수: 피터 7 + 3 = 이 문서 7 + 3(+1).

### 6-3. 남은 문제 (피터 7절, 7개)

| # | 내용 | 이 문서 |
| --- | --- | --- |
| 1 | `/api` 프록시가 v3를 넘기지 않음 | 0절(T2 프록시로 대신, 본부 실행 대기), U3 |
| 2 | 서버 기본값(409·503·FAILED) | U9 · U6(R1~R5) · U7 |
| 3 | 브라우저에서 keccak 재계산을 하지 않음(지갑 표시에 기댐) | 9절 결정 사항 |
| 4 | 거래 해시를 사람이 붙여 넣음 | 6-1 11번 |
| 5 | 응답이 없어진 뒤에는 같은 request_id로 다시 물음. v3에는 request_id 목록 조회가 없음 | 4-1 실서버 7번(중복 막기) |
| 6 | 가져온 시험 5건 건너뜀 | 7절 |
| 7 | 실제 브라우저 확인은 본부 실측 | 4절 실서버 칸 전체 |

개수: 피터 7 = 이 문서 7. U1(공개 체인)·U2(기관 확인 화면)·U4(`tools/local_proxy.py`)·U5(직접 연결)는 피터 7절에 없어 이 문서에서 더했다(8절). 피터 결과 문서 8-0절에는 이번 T6에서 U1~U9·R1~R5 표를 그대로 옮겼다.

---

## 7. 시험 실행

설치 없음, node 내장 `node:test`(node v26.0.0).

```sh
cd "/Users/khj/Desktop/해커톤 직원/web-5안"
node --test 시험/가져온/*.test.js 시험/가져온/regression/*.test.js 시험/op5_client.test.js 시험/op5_connect.test.js 시험/op5_proxy.test.mjs 시험/png_diff.test.mjs
```

| 출처 | 전체 | 통과 | 실패 | 건너뜀 |
| --- | --- | --- | --- | --- |
| 피터 보고(결과 문서 3절 T5, 프록시·픽셀 시험 전) | 103 | 98 | 0 | 5 |
| 피터 보고(T2·T5 메모 4절, 프록시 12건·png-diff 5건 더함) | 120 | 115 | 0 | 5 |
| 배너 다시 실행(2026-10-26, 위 명령) | 120 | 115 | 0 | 5 |

`시험/op5_proxy.test.mjs`는 가짜 업스트림 함수와 가짜 req/res로만 돈다(소켓 listen 없음). 실제 `node:http` 업스트림 호출은 증명하지 않는다(7-2절 N7). 실행 파일은 `zsh -n "개발/5안 d0111d8 프록시 시작.command"` 문법 확인만 했다(통과, 실행하지 않음).

건너뛴 5건은 web-2안 화면 전용 파일(app.js·index.html·staff.js 등)을 읽는 시험이다. 5안 화면 시험은 `시험/op5_connect.test.js`가 대신한다. 이 시험은 가짜 fetch·가짜 DOM으로만 돈다. 실서버·실제 브라우저 동작은 증명하지 않는다.

d0111d8 쪽 서버 시험(runbook 5절·`v5_c_runtime.md` "재현한 검사")은 본부가 그 작업 폴더에서 돌린다. 팀은 실행하지 않았다(아래 7-2 미실행 표).

### 7-2. 미실행 항목과 사유

| # | 항목 | 상태 | 사유 | 풀리는 조건 |
| --- | --- | --- | --- | --- |
| N1 | 4-1·4-2·4-3·4-4 각 **실서버** 칸 | 미실행 | 프록시 파일 마련, 본부 실행 대기(U3). 팀은 프록시·서버·docker·브라우저 실행 금지 | 본부가 0-1절 1~9번 실행 → 11절 H5~H8 |
| N2 | 실서버 4-2 2′·3, 4-3 6번(COMPLETED 보고서·원본) | 미실행 | Registry 미주입(U6)·분석기 미주입(U7)이라 계약상 성공 응답이 나올 수 없음. 기관 확인 화면 없음(U2) | B Adapter·분석기 주입, 기관 확인을 다른 도구로 끝냄 |
| N3 | d0111d8 서버 시험(runbook 5절) | 미실행 | 팀은 서버·docker 실행 금지 | 본부가 d0111d8 작업 폴더에서 실행 → 11절 H3 |
| N4 | `make finals-up`·`make v5-wallet-seed` 실제 출력 확인 | 미실행 | docker 실행 금지. 3절 출력 모양은 소스 print 문 대조로만 확인 | 본부 실행(0-1절 2~4번) → 11절 H1·H2 |
| N5 | 실제 브라우저(Enter·한글 조합·도움말 알림창·지갑 확장·내려받기) | 미실행 | 브라우저 실행 금지. 7절 시험은 가짜 DOM·가짜 fetch | 본부 실측 → 11절 H11 |
| N6 | T5 첫 화면 픽셀 비교 2건(어두운·밝은) | 미실행(미실측) | 캡처 2건은 예약만 됨(`캡처/5안-T5-첫화면-어두운모드-pc1440x820.png.캡처요청`, `캡처/5안-T5-첫화면-밝은모드-pc1440x820.png.캡처요청`), PNG는 아직 없음. 팀은 브라우저 실행 금지 | 본부가 캡처 생성 뒤 `cd "/Users/khj/Desktop/해커톤 직원/web-5안"` → `node 개발/png-diff.mjs 캡처/5안-어두운모드-pc1440.png 캡처/5안-T5-첫화면-어두운모드-pc1440x820.png`, `node 개발/png-diff.mjs 캡처/5안-밝은모드-pc1440.png 캡처/5안-T5-첫화면-밝은모드-pc1440x820.png`. 다른 픽셀 0(종료 0)이면 통과, 1 이상(종료 1)이면 다름, 크기 다름(종료 2)이면 실패, 읽기 오류(종료 3). 기준 둘 다 1440×820(피터 메모 3-2) → 11절 T5-1·T5-2 |
| N7 | 프록시의 실제 `node:http` 업스트림 호출(`httpForward`, `op5-proxy.mjs:47-60`), 실제 listen | 미실행 | 팀 환경은 소켓 금지. 시험 12건은 가짜 업스트림 함수로만 | 본부가 0-1절 5~7번 실행 → 11절 H4·H5 |
| N8 | 이전 협업 서버(8768) 경로의 실서버 칸 | 하지 않음 | d0111d8이 아닌 8780으로 보냄(0-3절). 판정 대상이 아님 | 없음 |

---

## 8. 피터 문서와 다른 점 (이번에 코드로 확인)

(T6 2차) 1~3번은 이전 길(8768 협업 서버·직접 연결)에 대한 것이다. d0111d8 검사는 이제 T2 프록시(0절)로 하므로 1~3번은 기록으로 남긴다.

1. **프록시가 보내는 곳이 d0111d8이 아니다.** `local-console-server.py`는 `127.0.0.1:8780`으로 보낸다. 이 서버는 `admin-runtime.py`가 소스 커밋 `3ef1fd4`로 띄운다. `local-runtime.py`가 따로 띄우는 API(8770)는 `121e1cad`다. 피터 7-1은 "v3를 넘기지 않음"만 적었다. 그래서 프록시에 v3를 더하더라도 보내는 곳을 d0111d8(8000)로 바꾸지 않으면 통합 후보 검사가 아니다.
2. **DELETE는 404가 아니라 501**이다(`do_DELETE` 없음). 그래서 화면에는 “서버가 지금 처리하지 못했어요.”가 나온다. 피터 7-1의 "v3 요청은 404"는 GET·POST에만 맞다.
3. **`연결 주소 바꾸기`로 바로 붙이는 길은 코드상 막혀 있다.** d0111d8 API에는 CORS 처리가 없고, `API_BROWSER_ORIGINS` 기본 목록에 8768이 없다. 피터 문서는 "CORS 허용이 있어야 함"으로만 적었다.
4. **`?demo=wallet`의 503 단계는 실서버와 다르다.** 장면은 `key-challenges`에서 503 `WALLET_REGISTRY_UNAVAILABLE`을 보여 준다. 그런데 d0111d8의 `key-challenges`·`key-proofs`는 Registry를 조회하지 않는다. 주소를 비우면 503 `WALLET_REGISTRY_NOT_CONFIGURED`(“서버에 장부(Registry) 주소가 설정되지 않았어요.”)가 나오고, 주소를 넣으면 통과한다. `WALLET_REGISTRY_UNAVAILABLE`은 `document-drafts`·`revoke-drafts`·`proposals`처럼 체인을 조회하는 단계에서 나온다. 캡처 설명(피터 4절 "키 증명 ✕ 503")을 실서버 동작으로 읽으면 안 된다(5-2절 R1·R2).
5. **v5 기관 확인(명부·메일·내부 승인) 화면이 5안에 없다(U2).** 키 증명 전에 `/v3/issuer-applications/{id}` 아래 `email-codes`·`demo-inbox`·`email-verifications`·`internal-approvals`를 끝내야 하는데, 5안 연결에는 이 자리가 없다. 실서버 4-2의 2′는 본부가 다른 도구로 기관 확인을 끝낸 뒤에만 된다. 피터 매핑 표(2절)·자리 없음(6절)에 없다.
6. **"공개 체인 없음"이 피터 문서에 없었다(U1).** 체인은 로컬 Anvil 31337뿐이다. 화면에도 이를 알리는 전용 문구가 없다. (T6에서 결과 문서 8-0절에 U1~U9를 옮겨 이제 두 문서에 같이 있다.)
7. `INPUT_SUPPORT_UNDECIDED` 문구가 두 개다: `api_adapter.js` “서버가 입력 받기를 아직 켜지 않았어요.”(화면에 보임), `op5_client.js` “서버가 글 입력 받기를 아직 켜지 않았어요.”(분석 흐름에서는 안 보임). 피터 8-1은 뒤의 것을, 7-2는 앞의 것을 "화면" 문구로 적었다. 검수 기준은 앞의 것이다.
8. 429 안내 끝말이 둘이다: `api_adapter.js` “초 뒤에 다시 해 보세요.”(결과 말풍선), `op5_client.js` “초 뒤에 다시 해 주세요.”(지갑·보관 등 오류 줄). 둘 다 코드 그대로라 틀린 것은 아니다. 다만 검수 때 어느 화면인지 구분해야 한다.
9. `.env.example`(d0111d8)에는 `API_WALLET_REGISTRY_ADDRESS`·`API_WALLET_EMAIL_SECRET`이 주석으로만 있다. runbook 3절 표에는 설정 항목으로 나온다. `.env`를 만들 때 직접 줄을 더해야 한다.

---

## 9. 대표·본부 결정 필요

1. (본부, 검사 전) ~~0절 세 길 중 하나~~ → T2에서 "d0111d8용 같은 출처 프록시 따로 두기"가 마련됨. 남은 일: 본부가 0-1절 절차를 실행하고 11절을 채운다.
2. (본부) 실서버 검사 조건 하나 고르기: Registry 주소를 비울지(ready 200, 지갑은 `NOT_CONFIGURED`) 넣을지(ready 503, 키 증명까지 됨). `API_WALLET_TEXT_INPUT_ENABLED`를 합성 검사에서 true로 켤지.
3. (본부) v5 기관 확인(메일·내부 승인)을 무엇으로 끝낼지. 5안에는 그 화면이 없다(8절 5).
4. (대표) "공개 체인 없음"을 화면에 알릴지. 지금은 전용 문구가 없다. 알린다면 넣을 자리도 정해야 한다(새 칸 금지라 기존 말풍선 글).
5. (대표) `?demo=wallet` 장면을 실서버 동작(4번 차이)에 맞춰 고칠지, "가짜 응답" 칩만 두고 그대로 쓸지.
6. (대표) 피터 6절 자리 없음 14개를 이대로 승인할지(특히 8번 `문제 찾음`이 색으로 확인 중과 구별되지 않음).
7. (본부) 브라우저에서 keccak을 재계산하지 않고 지갑 표시에 맡기는 것(피터 7-3)을 계약 위반으로 볼지.
8. (대표) **Q1** 프록시는 켜져 있고 API(8000)가 꺼지면 502 `UPSTREAM_UNREACHABLE`이 오고, 화면은 5xx 일반 문구 “서버가 지금 처리하지 못했어요.”를 보인다(`op5_client.js:96`). 이 문서 4-4 8번은 이 실제 문구를 기대 문구로 적었다. 화면 문구를 “서버에 닿지 못했어요…”로 맞출지(`op5_client.js` 문구 표에 한 줄 추가, 피터) 이대로 둘지 정해 주세요.
9. (대표) **Q2** 파일로 연 화면의 안내(`op5_client.js:89`)가 옛 실행 파일 `개발/협업 테스트 시작.command`를 가리킨다. 새 `5안 d0111d8 프록시 시작.command`로 바꿀지(화면 문구 변경) 정해 주세요.
10. (본부) **Q3** `API_SESSION_COOKIE_SECURE=true`로 검사할 계획이 있는지. 있다면 Safari·Firefox가 `http://127.0.0.1`에서 Secure 쿠키를 받는지 실측이 필요하다(피터 메모: Chrome은 받음). 이 문서 0-1절은 기본 false로 검사한다.
11. (대표) **Q4** 첫 화면 기준 캡처가 1440×820이라 T5 예약도 1440×820이다. 이전 예약(`5안-연결후-첫화면-*`, 1440×900)은 기준과 크기가 달라 비교할 수 없다. 820으로 계속 갈지, 900 높이 기준을 새로 찍을지 정해 주세요.

---

## 10. 대조와 비밀값 점검

- 문구 대조: 이 문서의 “ ” 안 문구를 모두 뽑았다. 각 문구가 `페이지/js/op5_client.js`·`op5_connect.js`·`op5_scenes.js`·`api_adapter.js`·`페이지/business.html`·`페이지/business.bundle.js`(유니코드 풀어서) 중 한 곳에 글자 그대로 있는지 확인했다. 예외는 seed 출력 한 줄로, d0111d8 `scripts/fixtures/seed_accounts.py`와 대조했다.
- 비밀값: 이 문서에는 비밀번호·키·토큰·메일 비밀값·DB 접속 문자열 값이 없다. 확인 명령:
  ```sh
  grep -nEi "password|passwd|secret|token|private|BEGIN (RSA|EC|PRIVATE)|postgres(ql)?(\+asyncpg)?://|0x[0-9a-f]{64}" "docs/A_통합후보_검사안내.md"
  ```
  2026-10-26 결과: 6줄이 걸렸고 모두 이름이다. `API_WALLET_EMAIL_SECRET` 항목 이름 2줄, 폴더 이름 `build/secrets/…` 2줄, 이 명령 줄, 이 결과 줄이다. 값은 0건이다.
  T6 2차(2026-10-26) `grep -nEi "password|secret|token|BEGIN"` 결과: 9줄(이 줄 포함), 모두 이름이다. 헤더 이름 `X-CSRF-Token` 2줄(0-2절 표, U4), `API_WALLET_EMAIL_SECRET` 항목 이름 2줄, 폴더 이름 `build/secrets/…` 2줄, 위 명령 줄, 위 결과 줄, 이 줄. 값은 0건이다.
- 문구 대조 결과(2026-10-26): “ ” 안 문구는 중복을 빼고 106개다. 105개는 위 화면 파일에 글자 그대로 있다. 나머지 1개(seed 출력 줄)는 d0111d8 `seed_accounts.py`에 있다. 없는 문구는 0개다.

---

## 11. 본부 검사 결과 (본부가 채움, 지금은 비어 있음)

- 본부가 0-1절 절차대로 실행한 뒤 채운다. 결과 칸에는 **통과 / 실패 / 미실행** 중 하나만 쓴다. 실행하지 않은 항목은 "미실행"과 사유를 비고에 쓴다.
- 기대 문구는 각 "기준" 칸의 절에 있다. 문구가 글자 하나라도 다르면 실패로 적고 비고에 화면 문구를 그대로 옮긴다.
- 비밀번호·키·토큰·메일 비밀값은 비고에 쓰지 않는다. 계정은 이름(`v5_bank` 등)만 쓴다.
- 이 표 말고 다른 곳(4절 표, 결과 문서)에는 결과를 적지 않는다. 결과 문서 8-0-5절은 이 표를 가리키기만 한다.

| # | 항목 | 기준 | 결과(통과/실패/미실행) | 날짜 | 비고 |
| --- | --- | --- | --- | --- | --- |
| H1 | `make finals-up` 끝에 `/health/ready` 200 | 0-1절 2번, 2-1절 | | | |
| H2 | `make v5-wallet-seed` 출력 3줄 모양, 두 번 실행해도 같은 계정 ID·같은 설정 두 줄 | 0-1절 3번, 3절 표 | | | |
| H3 | d0111d8 서버 시험(runbook 5절) | 7-2절 N3 | | | |
| H4 | 프록시 시작 출력 3줄(“브라우저에서 열기: …”, “5안 프록시: … → http://127.0.0.1:8000 (/api 를 떼고 전달)”, “끄기: Ctrl+C”) | 0-1절 5번 | | | |
| H5 | 4-4 연결 설정·상태 1~10번(8·8′ 포함) | 4-4절 | | | |
| H6 | 4-1 입력·결과 실서버 1~7번 | 4-1절 실서버 | | | |
| H7 | 4-3 보관·삭제 실서버 1~6번(6번은 분석기 미주입이면 미실행, N2) | 4-3절 실서버 | | | |
| H8 | 4-2 지갑 실서버 1~6번(2′는 Registry 주소·기관 확인 조건, N2) | 4-2절 실서버 | | | |
| H9 | 로그인 쿠키: `http://127.0.0.1:8790/business-login.html` 로그인 뒤 같은 화면에서 4-4 4번이 나옴(Set-Cookie가 8790에 저장) | 0-1절 8번, 0-2절 | | | |
| H10 | Origin: 다른 출처(예: 8768 화면)에서 `http://127.0.0.1:8790/api/v3/…`로 POST하면 403 `ORIGIN_FORBIDDEN`, 8790 화면의 POST는 통과 | 0-2절 | | | |
| H11 | 실제 브라우저: Enter·한글 조합 Enter·보내기 단추, `도움말` 알림창 없음, 지갑 확장 서명, 보고서·원본 내려받기 | 7-2절 N5, 결과 문서 9절 2·3·5·6 | | | |
| T5-1 | 첫 화면 픽셀 비교(어두운 모드): `node 개발/png-diff.mjs 캡처/5안-어두운모드-pc1440.png 캡처/5안-T5-첫화면-어두운모드-pc1440x820.png` → 다른 픽셀 0(종료 0)이면 통과 | 7-2절 N6 | | | |
| T5-2 | 첫 화면 픽셀 비교(밝은 모드): `node 개발/png-diff.mjs 캡처/5안-밝은모드-pc1440.png 캡처/5안-T5-첫화면-밝은모드-pc1440x820.png` → 다른 픽셀 0(종료 0)이면 통과 | 7-2절 N6 | | | |
