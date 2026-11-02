# D K10 — 연결형 원격지원 지시 누락 수정

- 담당: D 여인준 `@yijun0330`, V5-W6-D. 사용자 요청으로 Codex가 수정·검사를 보조했습니다.
- 기준: `phase/W6` `f1d7b3c0002f406419d44321aff4cff3e90edd57`.
- 브랜치: `codex/v5-w6-d-k10-connected-request`.
- 검증 코드: `1e4e5411085d75ed484a8f64f45dd727c21f4528`.
- 제보·재현 조건: [C의 #113 재승인/K10 원인 정정](https://github.com/OriginProof-3web/OriginProof/pull/113). 붙여쓰기 자체가 아니라 `설치하고 … 주세요` 연결형 누락입니다.

## 변경 전후

| 합성 입력 | 변경 전 규칙 | 변경 후 규칙 |
| --- | --- | --- |
| 원격지원 앱을 설치해 주세요. | HIGH / REMOTE_CONTROL_REQUEST | 동일 |
| 원격지원 앱을 설치하고 연락 주세요. | NO_CLEAR_INDICATORS / 근거 없음 | HIGH / REMOTE_CONTROL_REQUEST |
| 아래 링크에서 원격지원 앱을 설치하고 본인 계좌 비밀번호를 입력해 주세요. | 비밀번호 요청 근거만 검출 | 원격지원 요청 근거도 검출 |
| 원격지원 앱을 설치하고 연락하지 말아 주세요. | 근거 없음 | 동일 |
| 원격지원 앱을 설치하고 싶은지 알려주세요. | 근거 없음 | 동일 |
| 피싱 교육 사례: ‘원격지원 앱을 설치하고 연락 주세요’는 사기 예시입니다. | 근거 없음 | 동일 |

비밀번호가 포함된 제보 문장은 기존 CREDENTIAL_REQUEST 규칙으로도 HIGH일 수 있습니다. 이번 수정의 핵심은 원격지원 근거 누락과, 비밀번호 문구가 없는 연결형의 누락을 함께 해결하는 것입니다. 실제 제보 당시 모델 응답·브라우저 실행 전체를 복원한 것은 아닙니다.

기존 공통 `rule_analysis`·정확한 Unicode 인용 위치 검사·PhishingAnalyzer fallback·C 분석 API를 재사용했습니다. 원격지원 규칙에만 `설치/실행하고 … 요청형`을 추가했습니다. 뒤따르는 구간은 최대 40자로 제한하고 문장·줄·따옴표 경계를 넘지 않으며, 진행/희망 표현·부정·발화 인용 형태를 제외합니다. 다른 규칙의 공통 `_ASK`는 유지했습니다.

단순 연결형 확장은 `연락 안 해 주세요`, `연락했다는 문구를 확인해 주세요`, `연락했다고 알려주세요`를 오탐했습니다. 이 3개 거부 사례를 추가하고 연결 구간을 제한했습니다. 신규 검사는 요청 12개·거부 15개·callback 2개·API 2개, 총 31개입니다.

## 평가·버전 보존

- 현재 규칙: `phishing-rules-0.2`.
- 새 `phishing.py` SHA-256: `22f8149f53ff6db15d4ff342d1ee393f6369fa0395d5ed3a87214b12b3ab43d5`.
- 과거 평가 후보의 규칙 소스 hash `52f9e1103799310e03216894bad12f558432975dbcb1cab6d5d9f2db8844580f`와 후보 JSON은 그대로 보존했습니다.
- 후보 보존 검사는 과거 hash와 현재 후속 버전/hash를 각각 고정하고, 나머지 모델·프롬프트·계약 파일은 기존 hash와 계속 대조합니다. 검사를 삭제하거나 historical 후보의 hash를 새 소스로 덮지 않았습니다.
- [텍스트 최종 36개 결과](v5-d-live-holdout-20261027.md), [이미지 23개 결과](v5-d-live-images-20261030.md), 원본·정답·분할·정책·생성물은 변경하지 않았습니다. 이 수치는 과거 후보의 결과이며 **0.2의 성능 수치로 승계하지 않습니다**.
- 추가 유료 호출 0, 누적 133회. 모든 저장된 유료 정책은 false입니다. 재평가·프롬프트/모델 변경은 실행하지 않았습니다.

## 검사 결과

환경: 같은 Mac, Python 3.13.7·기존 잠금 의존성. 실제 OpenAI 키를 환경에서 제거하고 `LLM_PROVIDER=mock`으로 실행했습니다.

| 검사 | 결과 | 범위·한계 |
| --- | --- | --- |
| 수정 전 K10 신규 검사 최초 25개 | 13 FAIL / 12 PASS | 누락을 먼저 재현; 이후 오탐 3개·callback 1개와 API 2개 추가 |
| 현재 K10 규칙·callback | 29 PASS | 합성 단위/Mock replay, 정확한 원문 위치·발행 판정 독립성 |
| 기본 Python 전체 | 1453 PASS / 20 SKIP / 기존 Starlette 경고 1 | 단위·ASGI·기존 로컬 TCP 포함; opt-in DB/EVM 등은 미실행 |
| D 분석 API 연결·소비 | 45 PASS | ASGI·SQLite·합성 Registry·mock. 새 API 2개 포함 |
| 키 없는 clean archive 관련 검사 | 174 PASS | 검증 코드 커밋 archive에서 규칙/평가 안전장치/API·소비 재현 |
| Ruff 전체·git diff 공백 | PASS | 공유 타입/Schema/OpenAPI/ABI 변경 없음 |

첫 전체 실행은 sandbox TCP 바인딩 차단과 역사적 후보를 현재 소스와 동일시한 검사로 2건 실패했습니다. 로컬 TCP 허용 환경에서 재실행하고 후보/현재 버전을 분리한 뒤 위 전체 결과를 얻었습니다. SKIP 20개는 opt-in DB/EVM 미설정 등 19개와 Foundry cast 미설정 1개이며 통과로 계산하지 않았습니다.

재현 명령(저장소 루트, 잠금 환경 설치 후):

```bash
env -u OPENAI_API_KEY LLM_PROVIDER=mock uv run pytest -q
env -u OPENAI_API_KEY LLM_PROVIDER=mock PYTHONPATH=apps/api/tests:fixtures/finals \
  uv run pytest -q services/analyzer/tests/test_phishing.py \
  services/analyzer/tests/test_live_evaluation.py \
  fixtures/finals/v5_d_analysis_integration_qa.py fixtures/finals/v5_analysis_consumer_qa.py
uv run ruff check .
```

실행 JUnit은 `originproof-d-k10-full-20261102.xml`, `originproof-d-k10-api-20261102.xml`, `originproof-d-k10-clean-20261102.xml`로 로컬 보관했습니다. PR CI 결과는 해당 PR의 checks에서 별도로 확인합니다.

## 남은 확인

- C의 수정 코드 리뷰와 최종 RC 통합 후 실제 웹 경로 확인은 별도입니다. 기술 수정·검사 통과를 사람 승인·최종 수용 완료로 쓰지 않습니다.
- `하고` 뒤의 제한된 요청형에 대한 규칙 수정입니다. 모든 한국어 연결 어미·간접 요청·긴 문맥·유니코드 우회를 포괄하지 않습니다. NO_CLEAR_INDICATORS는 안전 판정이 아닙니다.
- 다른 실제 장비·공개 RPC·실제 OpenAI·전체 리허설은 이번 검사에 포함하지 않았습니다. 기존 G07 상태·실패/기여 이력은 유지했습니다.
