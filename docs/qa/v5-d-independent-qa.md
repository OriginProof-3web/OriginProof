# D 독립 연결 QA · G07 재검사

- 실행일: 2026-10-16 한국시간. 계획서 **5.1**, 병합된 공유 준비 계약 **v5-shared-0.1**.
- 현재 작업 브랜치: `codex/v5-d-independent-qa`. 앞선 분석 브랜치 `codex/v5-w5-d-analysis@cc517019043b4c508c6b7d1e9e5399642af1d33c`에서 분기했습니다.
- D 분석기 구현: `98d2c5400aa0e3e398dbb8df720b6d1445fae6db`. 연결 QA 실행 소스: `55431546711fa25fd77d7bebf3c05b63e5a6326d`.
- C 소비 후보: [#62](https://github.com/OriginProof-3web/OriginProof/pull/62) `eaa0d166269833cf7ee49675cfa777b0208c3725`. 병합/checkout 없이 고정 Git archive와 그 후보의 locked 환경을 사용했습니다. 후보의 v5-shared-0.2를 병합 기준으로 승격하지 않았습니다.
- 구조화 근거와 파일 hash: [결과 JSON](v5-d-independent-results.json). 작성자 외 사람/소유자 리뷰는 대기입니다.

## 결과와 검사 경계

| 검사 | 실제 결과 | 범위 |
| --- | --- | --- |
| 앞선 D 전체 Python 회귀 | 292 PASS / 0 FAIL / 0 SKIP | 분석 구현 SHA의 단위·ASGI·mock·코어·기존 v1 회귀. 이후 제품 코드 변경 없음 |
| D Analyzer를 C #62 locked 환경에서 실행 | 251 PASS / 0 FAIL / 0 SKIP | 새 공통 모델·SDK 소비 호환성, 실제 모델/RPC 아님 |
| D 분석기 → C 분석 접수/보관 | 12 PASS / 0 FAIL / 0 SKIP | ASGI + in-memory SQLite + 합성 Registry + mock LLM. 기본 입력 차단·보관 4조합·권한·삭제 후 늦은 결과·위험/발행 독립 |
| G07 mixed 진단 | 18 보고 그룹 PASS / 0 FAIL | 과거 고정 제품의 실제 socket HTTP·PostgreSQL·Anvil·Reader/Writer·projection/API 재시작·reorg. 브라우저 미실행 |
| `make generate` | PASS, 재생성 diff 없음 | 원본 생성기를 사용, v1/v5 Schema·타입·OpenAPI·Golden·예시 유지 |
| Ruff·compileall·diff | PASS | 새 QA 파일 포함. compileall은 Python 정적 타입 검사가 아님 |

251개는 292개와 겹칩니다. G07의 보고 그룹 안에도 여러 호출이 포함되므로 전체 합계나 독립 브라우저 검사 수로 합산하지 않습니다. Python 환경은 모두 3.13.7이며 지정 3.13.0과 차이가 있습니다. C 환경은 pytest 9.1.1 / FastAPI 0.142.2 / Starlette 1.7.0, D 환경은 pytest 8.4.2 / FastAPI 0.115 계열입니다. 기존 TestClient deprecation warning은 별도로 남았습니다. 의존성/lockfile 변경은 없습니다.

## D 분석기와 C 보관 연결

[D 검사](../../fixtures/finals/v5_d_analysis_integration_qa.py)는 C 자체 합성 processor 대신 실제 D `PhishingAnalyzer`를 주입합니다. 입력 지원은 격리된 테스트 app에서만 켰고 제품 기본값은 계속 false입니다. socket 연결을 차단하고 OPENAI_API_KEY를 제거했으며 mock은 명시적으로 주입했습니다.

- RULE 근거와 원래 Unicode 위치를 유지하고 모델 미실행을 보고합니다. 보관 4조합·10분/7일 만료·원본 삭제·목록 노출을 검사했습니다.
- 실제 서명 계산과 C 합성 Registry 증거로 **HIGH + VERIFIED**, **NO_CLEAR_INDICATORS + TAMPERED**를 확인했습니다. 후자의 위험 분류는 명시적 mock replay입니다.
- **HIGH + NOT_REGISTERED**, **HIGH + INCONCLUSIVE(RPC timeout 모의)**도 각각 유지됩니다. 발행 결과는 C 세션의 원본 snapshot이며 D는 verification을 만들지 않습니다.
- 다른 계정의 검증 세션/보고서/원본/삭제 접근을 거부했습니다. 분석 도중 삭제 후 실제 D callback이 늦게 끝나도 CANCELLED를 덮어쓰거나 원본을 복원하지 않습니다.
- DG12의 겹친 반복은 D가 먼저 격리해 UNDETERMINED와 GROUNDING_MISMATCH 제한으로 반환합니다. **C 자체 ground_report의 결함은 여전히 미해결**입니다. 같은 C SHA에 대한 앞선 직접 소비 검사는 30 PASS / DG12 1 FAIL이며 이 결과를 지우지 않았습니다.

첫 실행은 D QA 단언 3건이 실패했습니다. 요청 scope(PROTECTED_FIELDS)를 결과 scope와 혼동한 2건은 공유 계약의 FULL_COMPARISON으로 수정했고, 삭제 시 task 취소를 요구한 1건은 계약이 요구하는 영속 상태 차단과 늦은 결과 폐기를 검사하도록 수정했습니다. C/D 제품 코드를 바꾸거나 실패를 skip/xfail로 바꾸지 않았습니다. 수정 후 동일 C 후보에서 12개가 통과했습니다.

재현 명령은 두 소스의 경계를 명시합니다. C archive의 의존성은 그 후보의 lock으로 설치해야 합니다.

```sh
# OP_D_ROOT: 이 D 작업 브랜치, OP_C_ROOT: 위 고정 C SHA의 archive 절대 경로
cd "$OP_C_ROOT"
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH="$OP_D_ROOT/services/analyzer/src:$OP_C_ROOT/packages/python:$OP_C_ROOT/apps/api/src:$OP_C_ROOT/apps/api/tests:$OP_C_ROOT/services/indexer/src" \
  .uv-venv/bin/python -m pytest -q -p no:cacheprovider \
  "$OP_D_ROOT/fixtures/finals/v5_d_analysis_integration_qa.py"
```

## G07은 재현되지 않았지만 미해결 유지

기존 D 자산 `a3f55c6991061ac445d2223f19ff1b2a48acab0e`에서 [HTTP QA](../../fixtures/finals/w5_p0_api_qa.py)와 [projection QA](../../fixtures/finals/w5_projection_qa.py) 두 파일만 동일하게 재사용했습니다. 과거 PR/제품 브랜치 전체를 병합하지 않았습니다. 실행 QA HEAD는 `5c06d26da2cfc91a93963a390938af3145d16179`, 실행 시 dirty=false입니다. 이후 커밋은 별도 C 연결 검사 단언만 바꿨고 이 두 파일은 동일합니다.

대상 제품은 **과거 `9651062c9f36e124b76796278c996764678e1c77`**입니다. 신규 C #62/A 웹/B 지갑 Registry 전체의 실제 통합 성공을 뜻하지 않습니다. W4 helper는 `0bb5da42d64b9ce298cb2de2951b327da6bc4fc7`, seed는 `78cce405357ae1f509a9bfebdbb07af4b02b2411`의 고정 원본을 사용했습니다.

```sh
# 자신이 새로 만드는 폐기용 자원만 허용하는 명시적 opt-in입니다.
W5_D_API_QA=1 W5_D_MIXED_STACK_QA=1 \
  .uv-venv/bin/python fixtures/finals/w5_p0_api_qa.py
```

이번에는 projection 재생·API process 재시작·reorg 뒤 같은 혼합 스택에서 lifecycle 회귀까지 통과했습니다. 과거의 **mixed 17 PASS / 1 FAIL**은 그대로 유효한 실패 관측입니다. 이번 1회 PASS는 비결정적 실패를 재현하지 못했다는 증거이며 **원인 규명·제품 수정·G07 해결 근거가 아닙니다**. B/C의 Reader/RPC 재연결·시간/체인 상태 전이 원인 확인과 동일 수정 후보 재검사가 남습니다. 추가 반복 성공으로 원인 검증을 대신하지 않았습니다.

새 합성 PostgreSQL(tmpfs)·Anvil·네트워크만 생성하고 해당 Anvil의 중지/재시작·reorg를 수행했습니다. 종료 시 소유 컨테이너/네트워크 부재와 별도 API process 종료를 확인했습니다. 기존 사용자 DB·서비스·OS 시간·배포를 초기화하지 않았습니다. 기능 그룹은 1000 requests/min·100 logins/min의 테스트 전용 상향값을 사용하고, 기본 제한 120/10은 별도 그룹에서 확인했습니다. Foundry 1.4.4 이미지 digest와 설정 hash는 JSON에 기록했습니다. 실제 provider 호출은 0입니다.

## 남은 작업과 사용자 결정

1. 팀의 Q01 입력 종류/우선순위와 Q05 모델/전송·유료 평가 범위 결정. 현재 모두 미정으로 유지합니다.
2. A 또는 C가 [60개 합성 원본 초안](../../fixtures/synthetic/phishing_sources_v1.json)의 라벨·근거·24/36 분할을 리뷰한 뒤 평가셋을 동결합니다. 개발 기준선 macro-F1 0.451863은 실제 LLM 성능이 아니며 보류 36개 모델 평가는 미실행입니다.
3. C는 DG12 근거 함수 수정, B/C는 G07 원인/수정 인계를 진행합니다. D는 같은 수정 후보에서 실패를 재검사합니다. 이번에는 다른 소유자 제품 소스를 수정하지 않았습니다.
4. A/B/C가 같은 신규 통합 후보를 인계하면 지갑/Registry/실제 PostgreSQL/웹 브라우저·QR·권한·consume·선정 입력을 연결 검증합니다. 공개 네트워크·다른 장비·clean clone의 새 분석기 재현·최종 리허설은 미실행입니다.

원래 `OriginProof` 폴더의 파일 hash 4,551개(3개 symlink의 대상 파일 포함)가 백업과 일치합니다. 기존 D/phase/integration 브랜치를 보존하고 전용 작업 브랜치에서만 변경했습니다. 원격 push·PR 생성·병합·팀원 메시지 발송은 하지 않았습니다. Codex가 D 구현·합성 초안·검사·기록을 수행했고 사람의 기여 확인이나 리뷰 승인을 대신 기록하지 않습니다.
