# W3-D — 두 유형 합성 사례와 독립 검사

- 담당: D / 여인준님 `@yijun0330`, 2026-10-02. W3는 개발 단계입니다.
- 시작: `phase/W3@1f8ed632ea9c74091abaf2fe2ec32882038f731f`
- 작업 branch: `test/w3-d-proof-qa`
- D 독립 QA 초안 PR: [#46](https://github.com/OriginProof-3web/OriginProof/pull/46), C 리뷰 요청 완료.
- 검사 코드 SHA: `cbe8aaeea59e18bd4e8529bf59b618683f3e3964`
- [환경 fingerprint](w3-d-environment.json): Python 3.13.7, Node 22.18.0,
  uv 0.8.17. 기존 개인 .env·애플리케이션 소스·공통 모델·Golden은 수정하지 않았습니다.

## 현재 원격·선행 상태

| 담당·PR | 확인 SHA | 현재 상태·D 연결 조건 |
| --- | --- | --- |
| C [#35](https://github.com/OriginProof-3web/OriginProof/pull/35) | `17c24a36a46c6b2a823a3b7fac20c97c6faee98f` | OPEN. 발행/제한 조회/검증 및 migration 0005 후보 계약을 읽었습니다. 현재 phase/W3에는 /v2 발행 API가 없음 |
| B [#40](https://github.com/OriginProof-3web/OriginProof/pull/40) | `92e0e94cba8e7799f709060afc9f4e02d220d142` | OPEN. 동일 블록 Registry snapshot·v2 digest 교차검사·W4 계약 후보. C의 snapshot 소비는 연결 시 확인 |
| A [#44](https://github.com/OriginProof-3web/OriginProof/pull/44) | `668bd72e6c25da9005f53e02f8940c9589acad30` | Draft/OPEN. 공식 디자인 W3 화면과 다른 후보 backend 검사 기록 존재. 최신 phase에 병합된 같은 SHA의 D 브라우저 검사는 별도 필요 |
| D [#43](https://github.com/OriginProof-3web/OriginProof/pull/43) | `c16de660914389ba8821612aa3d6c64708085185` | 기존 AI 후보 안전성 Draft/OPEN 유지. 이번 P0 QA branch에 합치지 않았으며 AI는 W3 발행/검증의 선행 조건이 아님 |

위 PR의 담당자가 보고한 검사 결과를 D의 실행이나 소유자 승인으로 재사용하지 않습니다.
다른 담당자의 branch를 checkout/merge하거나 기능을 대신 구현하지 않았습니다.
W1/W2 단계 최종 병합 대기는 이 W3 독립 준비를 막지 않습니다.

## W3-D1 — 실제 추가한 합성 자료

- [빌더](../../fixtures/finals/build_w3_cases.py), [사례 manifest](../../fixtures/finals/w3_cases.json),
  [자동 검사](../../services/analyzer/tests/test_w3_proof_qa.py).
- PAYMENT_REQUEST / Origin Mock Bank 31개, OFFICIAL_DOCUMENT / Origin Mock Office 33개,
  총 **64개**. 모델 거부 12개, 결정론적 코어 평가 52개입니다.
- C의 기존 `scripts/generate_finals_golden.py`가 만든 공개 v2 서명 벡터 두 개를 그대로
  읽고 SHA-256·payload hash·signing digest·recover signer를 확인합니다. 새 키·서명을 만들거나
  Golden 파일을 덮어쓰지 않습니다. manifest 재생성이 기존 JSON과 동일한지도 검사합니다.
- 정상/ID 단독, 금액·문서번호 단일 변조, 각 필수 필드 누락·null/전체 null,
  누락+변조 우선순위, 잘못된 domain/version/network/type/single_use/기간,
  미등록 기관·키/타 기관 키, 발행 시각의 키 기간, signer/서명 오류,
  payload 변조 및 hash를 바꿔도 서명을 재사용할 수 없는 경우를 포함합니다.
- 비교 변조는 원래 서명된 자료를 유지하고 관찰 candidate의 한 필드만 바꿉니다.
  envelope 자체 변조는 별도 명시한 실패 사례이며 다시 서명하지 않습니다.

### 승인 정책에 따른 기대값

| 조건 | W3 기대값·실제 코어 결과 |
| --- | --- |
| 정상 내용 전체 비교 | VERIFIED / FULL_COMPARISON |
| ID·서명 근거만 검사 | VERIFIED / PROOF_ONLY, candidate_match NOT_RUN |
| 누락만 있음 | INCONCLUSIVE / PARTIAL_COMPARISON / INPUT_INCOMPLETE |
| 실제 불일치와 누락이 함께 있음 | TAMPERED 우선, 부분 비교 범위 유지 |
| 지급 금액 / 문서번호 단일 변조 | AMOUNT_MISMATCH / FIELD_MISMATCH |
| network 불일치·서명 전 필수 실패 | signature 등 의존 검사 NOT_RUN |
| domain/version/유형/기간 입력 위반 | 현재 공통 Pydantic 모델에서 ValidationError; HTTP 상태는 이 검사에서 실행하지 않음 |
| 만료 직전 / 경계 / 직후 | 경계부터 PROOF_EXPIRED. 원래 서명·내용 검사와 현재 유효성을 구분 |
| 모든 W3 코어 사례 | lifecycle_status null, proof_status NOT_RUN. VERIFIED를 ACTIVE/현재 사용 가능으로 표현하지 않음 |

Golden 시각은 고정된 합성 벡터입니다. 테스트가 코어의 `now`만 주입하며 OS 시각은 바꾸지
않습니다. 실제 발행 연결 검사에서는 서버가 새 ID/nonce/salt/시각을 만들고 미래 만료를 사용해야 합니다.

## 실제 실행한 검사

| 명령 | 결과·범위 |
| --- | --- |
| `pytest -q services/analyzer/tests/test_w3_proof_qa.py` | **65 passed**, 코드 SHA cbe8aae. 64개 사례 + manifest/Golden 재현 1건 |
| `make test` | **236 passed, 3 skipped**, 동일 소스의 코드 커밋 직전 실행. skip은 기존 DB/Anvil opt-in 3건 |
| `make test-analyzer` | **195 passed**, 동일 소스의 코드 커밋 직전 실행. 위 65개를 포함하므로 두 수치를 합산하지 않음 |
| `ruff check fixtures/finals/build_w3_cases.py services/analyzer/tests/test_w3_proof_qa.py` | 통과. Makefile Ruff 범위 밖 fixture 빌더도 별도 확인 |
| `make bootstrap-check`, `make lint`, `make typecheck`, `make env-fingerprint` | 통과. Python typecheck는 compileall이며 웹 ESLint/tsc 포함 |
| 문서 링크·`git diff --check` | 통과 |

기본 회귀의 warning 1개는 기존 Starlette/anyio deprecation입니다. Analyzer 테스트는
기존 autouse fixture로 socket 연결을 막고 provider mock/OPENAI_API_KEY 제거를 적용합니다.
이번 결과는 **실제 ECDSA 서명 검증 + 합성 trust record의 모델/코어 검사**입니다.
실제 발행·DB 저장·RPC·체인 상태·브라우저·AI 추출 정확도 성공으로 확대하지 않습니다.
관련 Contract/ABI 변경이 없으므로 Foundry 검사를 이번 변경에서 재실행하지 않았습니다.

재현: 저장소 루트에서 lockfile 의존성을 준비하고 다음을 실행합니다.

```sh
PYTHONPATH=packages/python .uv-venv/bin/python fixtures/finals/build_w3_cases.py
make test-analyzer
```

## W3-D2 — 연결 후 실행할 독립 실패 검사

기준 계약은 C #35의 `docs/api/w3_c_proof_contract.md`입니다. 후보 계약을 현재 phase API로
표현하지 않습니다. C/B 선행이 phase에 반영되면 그 최종 SHA와 manifest로 격리 환경을 구성합니다.

| 검사 | 재현 조작·기대값 | 현재 상태 |
| --- | --- | --- |
| 발행 권한·입력 | 운영자/수신자 발행, 타 유형·기관 코드·임의 issuer/key/nonce/role 주입. 거부하고 Proof/감사 성공 기록 없음 | NOT_RUN — C1 actual API 연결 필요 |
| 동시 같은 요청 | 같은 issuer 세션 두 연결로 동일 request_id POST /v2/issuer/proofs. ID/서명/저장/감사 1건. 같은 ID 다른 내용은 409 | NOT_RUN — C1·실 DB 필요 |
| 서명·저장 실패 | 격리 signer 누락/불일치와 commit 실패 주입. 발행 성공 응답 없음, DB·token·audit 원자적 rollback 확인 | NOT_RUN — C1 실제 구현에 실패 주입 필요 |
| RPC·재배포 | 기관/키 조회 실패 및 deployment 변경. 발행은 실패/보류, 검증은 INCONCLUSIVE/DEPENDENCY_UNAVAILABLE | NOT_RUN — B1/C1/C3 연결 필요 |
| 공개성·기관 분리 | 공개 GET에 payload/금액/문서번호/계정/token/salt/binding/개인키 없음. 타 기관·다른 수신자의 content/비교는 거부 | NOT_RUN — C2 actual API 필요 |
| 두 유형·단일 변조 | 새 발행한 Proof로 지정 수신자 정상·누락·변조 검증. F01/F02/F05/F06/F12/F14의 실제 수행 하위 범위만 기록 | NOT_RUN — C3 actual API 필요 |

C #35 후보 소스는 기관과 키를 각각 조회하며 B #40은 `get_issuer_key_snapshot`을
제공합니다. 두 PR 반영 시 실제 발행/검증 소비가 한 블록 snapshot을 쓰는지 C/B와 확인합니다.
이 기록은 아직 병합되지 않은 후보의 연결 점검 항목이며 새 정책 재승인 요청이 아닙니다.

## W3-D3 — 브라우저 연결 및 단계 마무리

1. A/C/B가 같은 phase SHA에 들어온 환경에서 두 합성 기관을 승인하고 실제 키를 등록합니다.
2. 각 유형을 AI 없이 새로 발행해 실제 저장 ID·공개 링크/QR·기관별 목록을 확인합니다.
3. 새 익명 세션의 ID 조회는 PROOF_ONLY·제한 내용 비공개임을 확인합니다.
4. 지정 수신자의 별도 로그인 세션에서 정상/금액·문서번호 단일 변조/누락을 비교합니다.
5. 다른 수신자·타 기관 거부, 새로고침/로그아웃 후 재조회와 조회 전후 상태 불변을 확인합니다.
6. PC 로컬 링크 기본 재현을 기록합니다. LAN 휴대폰 확인은 설정한 환경에서만 따로 판정합니다.

현재 **NOT_RUN**입니다. A #44의 과거 후보 backend 연결 기록은 D의 같은 SHA 실제 브라우저
검사를 대체하지 않습니다. 사용자 세션·QR/링크·공식 디자인 접근성/실패 화면을 독립 확인해야 합니다.
W4 Proof 상태/폐기/consume·경쟁 처리는 W3 통과에 포함하지 않습니다.
본 PR의 작성자 외 리뷰, D2/D3 연결 검사 및 A~D 기록·최종 SHA 확인 전 W3 완료/승격을 선언하지 않습니다.
