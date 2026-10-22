# D 개발 후속 구현·검사 — 2026-10-21

사용자의 “할 수 있는 것은 모두 진행” 지시로 Codex가 D 경로의 평가 실행기·수용 검사 도구·실제 로컬 독립 검증 QA를 구현했습니다. 계획서5.1 / v5-shared-0.2 / ADR0004입니다. [PR #76](https://github.com/OriginProof-3web/OriginProof/pull/76), D `codex/v5-d-independent-qa`. 기능 코드 `d35e8d1a6bc88b5ab4290af3fba1029e26a47d38`, 실제 EVM 하네스 수정 `5b50ac4b450ed94440c832b93f0011feed1188d5`, #69 반영 후 수용 검사 실행 `a24426f80eae372a488b2c6c104dbd71aaee9290`를 이후 문서 커밋과 구분합니다. [구조화 결과](v5-d-development-completion-20261021.json).

## 기준·보존·재사용

integration `ec8e15c6bc684ae1e8d68f53ea40b4a8e47aad67`, 최신 phase/W5 `2c81b8e10fbac1d14fa3526dbc4128996e428f7e`를 D W2→W3→W4→W5→QA에 정상 merge했습니다. #64/#68/#69의 B 계약·RPC/체인 기초를 채택했고 B가 병합한 lock 변경을 그대로 사용했습니다. D가 별도 패키지·버전·계약·생성물 사본을 추가하지 않았습니다. 충돌 없이 기존 D/C 대행 구현·작성 이력·기여와 사용자 원본을 보존했습니다. phase/통합 branch 직접 개발·원격 병합은 하지 않았습니다.

기존 provider/규칙/후보 관측·평가기, common model·Golden, D JUnit guard·stage/consumer·성능/독립 QA를 재사용합니다. 기존 mock/rules 평가 CLI의 기본 동작은 그대로이며 평가 함수에 검증된 case ID 선택만 추가했습니다. 입력 지원 활성화·Decisions API·기관 발행 판정을 추가하지 않았습니다.

## 1. 실제 모델 평가를 위한 제한 실행기

[실행기](../../services/analyzer/src/originproof_analyzer/live_evaluation.py)는 기본 계획 출력만 수행합니다. [정책 예시](../../fixtures/synthetic/v5_d_live_evaluation_policy.example.json)는 승인false·상한0이며 현재 corpus도 입력/라벨·분할 리뷰 전이라 실제 실행을 차단합니다. 사람의 승인이나 예산을 AI가 채우지 않았습니다.

```sh
.uv-venv/bin/python -m originproof_analyzer.live_evaluation \
  --manifest fixtures/synthetic/phishing_sources_v1.json \
  --policy fixtures/synthetic/v5_d_live_evaluation_policy.example.json \
  --journal build/qa/private-model-evaluation.json
```

계획 출력은 네트워크·SDK client·키 조회·journal 생성 없이 종료합니다. 실제 `--execute`를 붙여도 현재 정책은 BLOCKED/exit2이고 유료 호출0입니다. 사람이 입력/라벨·분할을 검토한 manifest와 정확한 SHA256, 승인된 평가 범위/예산 참조, 양의 상한을 기입한 별도 정책을 제공한 뒤에만 실행할 수 있습니다. 모델은 이미 선택된 gpt-6-luna를 고정하며 Jev는 사용하지 않습니다.

- 실제 provider의 Responses/Structured Outputs·store=false를 재사용하고 SDK retry=0, 공식 HTTPS Responses endpoint만 허용합니다. wrapper는 전송 직전에 출력 상한을 적용하며 한 사례에서 HTTP 재전송을 허용하지 않습니다. [공식 Responses 매개변수](https://developers.openai.com/api/reference/python/resources/responses/methods/create), [Python SDK 재시도 설정](https://developers.openai.com/api/reference/python)을 대조했습니다.
- 호출 수는 journal의 누적 예약 수로 제한합니다. 각 호출의 최대 출력 토큰 전체를 먼저 예약하고 실제 사용량이 적거나 누락돼도 예산을 환급하지 않습니다. 보고된 출력 사용량이 상한을 넘으면 그 실행과 재개를 모두 중단합니다. 입력 문자 수도 제한합니다. **출력 토큰 상한이며 입력 비용까지 포함한 금액 hard cap은 아닙니다.** 확인된 input/output/total usage만 별도로 합산하고 비용은 null입니다.
- `--stop-after N`은 이번 실행에서 처리할 사례 수입니다. 같은 정책·corpus·코드·prompt·SDK의 같은 journal에 `--resume --execute`하면 처리한 ID는 재호출하지 않습니다. 취소/중단 시 이미 예약된 사례는 UNKNOWN/실패 분모로 보존하고 자동 재시도하지 않습니다. 불명 결과의 지연은 시간 통계에서 분리합니다.
- journal은 숫자·case ID·예측/기대 위험 수준·오류 코드만 저장하는 원자적0600 파일입니다. 전체 원문·인용·원시 응답·키를 저장하지 않습니다. 프로세스 lock이 있으면 실행을 거부합니다. 강제 종료로 남은 lock은 해당 프로세스가 종료됐는지 사람이 확인하기 전에는 지우거나 우회하지 않습니다.
- 지표는 규칙+LLM 파이프라인 분류와 검증 전 후보 근거 품질을 구분합니다. 부분 실행을 전체 분할 완료로 표시하지 않으며 사람 평가/입력 수용 완료로 자동 판정하지 않습니다. 보류36개 예측은 계속0입니다.

[새 검사18개](../../services/analyzer/tests/test_live_evaluation.py)는 실제 SDK+MockTransport이며 호출/출력 상한, retry0, 중단 후 UNKNOWN 보존, 동일 사례 재호출 방지, 정책·corpus·checksum·lock 거부, 비밀값/원문 비저장을 확인했습니다. 테스트의 승인 메타데이터는 폐기 가능한 복사본의 SIMULATED_TEST이며 실제 라벨/예산 승인이 아닙니다.

## 2. 동일 QA HEAD의 수용 증거 실행 도구

[수용 실행기](../../fixtures/finals/v5_d_acceptance_runner.py)는 clean QA HEAD·lock hash·Python/package fingerprint를 묶고 기존 stage43/consumer31/성능16/D독립22를 명시 실행합니다. 기본은 계획입니다. 실행 중 source/lock 변경, child 오류, 수 감소/필수 module 누락·중복·skip·JUnit summary 불일치를 실패로 남깁니다. 로그와 summary는0600이며 output을 덮지 않습니다.

```sh
.uv-venv/bin/python fixtures/finals/v5_d_acceptance_runner.py
.uv-venv/bin/python fixtures/finals/v5_d_acceptance_runner.py --execute
```

최신 실행 `a24426f80eae372a488b2c6c104dbd71aaee9290`의 네 묶음이 모두 PASS이고 source_consistent=true입니다. 기본 build/qa의 UUID 디렉터리에 명령 대상·정확 수·XML SHA256·원래 V5-F01~21 수용표의 남은 조건을 연결합니다. D 독립22와 C 기존49를 함께 돌리는 CI의71은 별도 범위입니다.

도구 단위10개가 통과했습니다. 합성 검사만으로 실제 수용을 통과시키지 않아 최종 상태는 SUPPORTING_SUITES_PASS_ACCEPTANCE_BLOCKED / exit2이며, 검사가 실패한 exit1과 다릅니다. 실제 G07/Anvil 검증은 아래의 별도 고정 제품 기록을 함께 검토해야 합니다. 새 phase/W6나 단계 완료를 만들지 않았습니다.

## 3. 실제 로컬 Registry에 대한 서비스 API 밖 독립 검증

새 B 구현을 반영한 뒤 [opt-in D QA](../../fixtures/finals/v5_d_live_independent_qa.py)를 구현했습니다. B Registry/ABI와 공통 EIP-712·원본 생성 모델을 사용하고, C #63 `68ea0c20718937cd0c93d683e3cfa9b3995a9666`의 검증 코드·helper/Golden/ABI는 기존 네 hash를 확인해 읽기 전용 재사용합니다. B의 `test_wallet_live.py@c259eab755e121564c790fd55dd2b2830f72bda3`의 폐기 노드·공동승인/발행 순서를 참고했고 B/C 생산 코드는 수정하거나 타 branch를 merge하지 않았습니다.

제품 `33396ba409662ef33ddee339eba670263bbcb761`의 불변 git archive로 G07 도구가 만든 deployer 이미지와 revision label, 그 제품의 생성 ABI=컴파일 ABI를 대조했습니다. D QA 실행은 `5b50ac4b450ed94440c832b93f0011feed1188d5`입니다. 이후 #69 merge는 이 D QA·공통 Python·계약/ABI 소스를 바꾸지 않았음을 diff로 확인했으며 실제 실행 기록의 SHA를 새 HEAD로 바꾸지 않았습니다.

```sh
# 제품 SHA는 불변 git object여야 하며, 같은 revision의 deployer 이미지가 필요합니다.
# 기존 G07 runner가 immutable product archive에서 해당 이미지를 빌드합니다.
D_C63_SOURCE_DIR=/path/to/immutable-c63 \
D_WALLET_INDEPENDENT_LIVE=1 D_WALLET_PRODUCT_SHA="$PRODUCT_SHA" \
D_LIVE_REPORT=/path/to/new-private-report.json PYTHONPATH=fixtures/finals \
  .uv-venv/bin/python -m pytest -q -o addopts= fixtures/finals/v5_d_live_independent_qa.py
```

새 loopback Anvil만 만들고 실제 B Registry 배포→서로 다른2명 승인→기관 서명 발행을 실행했습니다. 두 템플릿에서 C 검증 함수와 **실제 CLI subprocess**의 정상 원본/보호 필드, 원본/필드 변조, 다음 버전 뒤 과거 SUPERSEDED, 최신 REVOKED와 과거 상태 보존이 확인됐습니다. RPC stop 시 INCONCLUSIVE, restart 뒤 실제 상태 재조회가 확인됐습니다. **실제 로컬 EVM 1 PASS**, 서비스 API·DB·브라우저·AI 호출0이며 노드는 삭제됐습니다. 공개 체인/별도 조직 운영/실제 제품 통합 검증은 아닙니다.

최초 실행 `d35e8d1`은 두 템플릿의 정상/변조/과거 상태까지 통과한 뒤 RPC 복구에 실패했습니다. Docker가 임의 host port를 재할당했는데 D 하네스가 이전 endpoint를 유지한 원인이었습니다. 실패 기록과 정리 결과를 보존하고 새 포트를 재조회하도록 수정했습니다. 재검사에서 rpc_endpoint_rebound_on_restart=true와 상태 복구를 확인했습니다. B/C 계약 결함으로 처리하거나 실패를 덮지 않았습니다.

## 4. C 요청을 반영한 G07 mixed5회

C의 이전 리뷰는 mixed5회 이상을 예로 요청했습니다. 최신 B #64/#68 반영 후 clean QA `2b8afe2bd1e500c27eaef185283806b2cbf70d48`, 제품 `33396ba409662ef33ddee339eba670263bbcb761`, 동일 lock `bd617d34973fcae555ddc543388aacf017a3ef71616e407c125f73de089e812f`에서 **fresh1+mixed5**를 실제 실행했습니다. 여섯 회 모두 필수18개 그룹 PASS·자원 정리 true입니다. 이전 실패·fresh1/mixed3 결과는 보존합니다.

B는 앞선 d757a26의 fresh1/mixed3 증거에 대해 #76에서 검토 완료를 밝혔습니다. 새 회차의 원인/증거와 C 최종 검토는 별도 확인이 필요하므로 G07은 OPEN이며 판정 PASS_REQUIRES_B_C_REVIEW를 유지합니다. 신규 지갑 통합 브라우저 검사와 구분합니다.

## 5. 검사와 실제 남은 경계

| 검사 | 실제 결과 |
| --- | --- |
| 기본 전체 Python at5b50ac4 | 730 PASS / 기존 live opt-in10 SKIP / 기존 Starlette 경고1 |
| 새 실행기/수용 도구 단위 | SDK mock18 + 수용10 PASS |
| 기존 평가·후보 지표와 새 도구 | 54 PASS; 위 검사와 겹쳐 합산하지 않음 |
| 최신 HEAD 수용 supporting suites | stage43/consumer31/성능16/D독립22 PASS, skip0 |
| 실제 독립 로컬 EVM | 최초 QA 실패 보존, 수정 후1 PASS·두 템플릿 CLI·상태/변조·RPC 복구 |
| 실제 G07 | fresh1/mixed5 각18 PASS, 모든 소유 자원 정리 |
| 생성물·Ruff·YAML/bash·diff | PASS / 생성물 변경 없음 |

입력 선정·라벨/분할 사람 리뷰·실제 평가 범위/예산이 남아 있어 **유료/보류 평가·미선정 변환은 실행하지 않았습니다**. A/B/C의 같은 후보에서 실제 지갑/Registry/API/DB/브라우저 연결 및 성능·공개 배포 범위·다른 노트북·동일 RC3회는 준비 인계 후 실행합니다. C #85 seed-only ready503/P0 준비 조건 정리와 작성자 외 최신 HEAD 리뷰도 남습니다. B/C 코드의 최종 제품 연결을 D가 임의 변경하지 않았고 사람의 대행 확인/Approve를 대신 게시하지 않았습니다.

재개 경계 최종 보완: 공통 모델·입력/설정/오류 원본과 OpenAI/httpx/Pydantic/Python 환경도 식별값에 포함했습니다. 같은 corpus라도 런타임이 바뀌면 재호출 전에 거부하며 기존 중단·재개 검사에서 확인했습니다. 이 보완은 실제 EVM/G07 제품이나 원본 자료를 바꾸지 않습니다.
