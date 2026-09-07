# Historical audit — superseded by ../HANDOFF.md

# M2 GitHub 기준 정합성 점검 및 시작 조건 Handoff

점검일: 2026-09-07 (Asia/Seoul)

## 현재 상태

**공통 시작 조건 미충족. 기존 M2 기능의 팀 저장소 이식은 아직 시작하지 않았다.**

- 원격: https://github.com/OriginProof-3web/OriginProof
- 검사 checkout: `/Users/home/Workspace/OriginProof-team`
- 현재 브랜치: `main`
- 검사 SHA: `4ee98f3c3f343adba566354d5f3d9460ddab5d2e` (Bootstrap PR #4 병합 커밋)
- Bootstrap 브랜치 tip: `5c94040a76428bbf569654162b1b5fb42d5031fc`
- 위 두 커밋의 tracked tree는 동일하지만 SHA는 다르다. 팀원 모두 사용할 SHA는 통합 담당자가 확인해야 한다.
- 기존 단독 구현: `/Users/home/Workspace/OriginProof` (수정하지 않음)
- 다른 세 명의 SHA/fingerprint와 clean-clone 재현 결과는 제공되지 않았다.
- `AGENTS.md` 5A와 `START_HERE.md`에 따라 `mvp/ai` 생성과 기능 이식을 보류했다.
- 이번 점검에서는 이 문서 외 tracked 소스, lockfile, Schema, Compose를 변경하지 않았다.

적용 지침: 루트 `AGENTS.md`, `START_HERE.md`, `services/analyzer/AGENTS.md`,
`fixtures/AGENTS.md`, `prompts/02_mvp_ai.md`. Bootstrap 실행 방법은
`docs/runbooks/bootstrap.md`를 참고했다.

## 실제 실행 결과

실패 후에도 나머지 진단을 수행하기 위해 여러 Make target은 `make -k`로 실행했다.
아래 통과 항목은 GitHub Bootstrap 코드에 대한 결과이며 기존 M2의 60개 테스트 결과와 다르다.

| 명령 | 실제 결과 |
| --- | --- |
| `git rev-parse HEAD` | 위 Bootstrap 병합 SHA 확인 |
| `make bootstrap` | 통과. Python 3.13.7 환경 및 선언된 의존성 설치; lockfile 변경 없음 |
| `uv run python scripts/ci/validate_structure.py` | 통과: mvp-v1 |
| `make env-check` | 실패: `docker`, `forge` 없음 |
| `make mvp-up` | 실패: Docker 실행 파일 없음 |
| `make seed` | 통과: `build/seed_manifest.json` 생성. 현재 seed는 DB 적재가 아니라 manifest 생성 |
| `make smoke` | 실패: 127.0.0.1:8000 연결 불가. 컨테이너 서비스 미기동 |
| `make env-fingerprint` | JSON 생성 성공. 환경 일치 검증의 통과를 의미하지 않음 |
| `make test-analyzer` | 통과: health 테스트 1개. 필드 추출 완료를 의미하지 않음 |
| `make mvp-test` | 실패: Contract 테스트에 필요한 forge 없음. API 1개 및 integration health 2개는 통과 |
| `uv run pytest` | Bootstrap Python 테스트 전체 6개 통과 |
| `make lint` | 통과 |
| `make typecheck` | 통과. 현재 target은 compileall 문법 검사이며 정적 타입 분석이 아님 |
| `git diff --check` | 통과 |

`.env`는 Bootstrap 명령이 합성 개발 설정으로 생성했으며 Git 추적 대상이 아니다.
OpenAI 유료 호출, Git commit/push, PR 작성, Docker reset은 수행하지 않았다.
조회한 Git 이력에서 private-key header와 OpenAI/GitHub token 패턴 검사는 일치 항목이 없었다.
이는 모든 형태의 비밀정보나 개인정보가 없다는 완전한 보증이 아니다.
팀 Golden Fixture 두 개의 데이터는 `source=synthetic`, `Origin Mock Bank`임을 확인했다.

## 요청 1: 공통 환경 확정 및 fingerprint 보완

- 담당: 통합 담당자 김형준, 공통 Bootstrap 담당자; ABI는 M3/M4와 조율
- 요청 파일/인터페이스: `.tool-versions`, `.python-version`,
  `scripts/ci/env_check.py`, `scripts/ci/environment_fingerprint.py`,
  `packages/contracts/abi`, 각 팀원의 `build/environment_fingerprint.json`
- 요청 변경/확인:
  1. 팀에 공지한 정확한 Bootstrap SHA와 네 명의 comparable 결과를 확인한다.
  2. Docker/Compose 및 Foundry를 설치하고 승인된 런타임 버전을 맞춘다.
  3. `.tool-versions`의 Python 3.13.0/Node 22.14.0과 현재 Python 3.13.7/Node 24.8.0 차이를 해소한다.
     `.python-version`이 `3.13`이라 Bootstrap은 정확한 patch 버전을 강제하지 않는다.
     uv는 0.8.17, pnpm은 11.19.0으로 확인했다.
  4. Schema fingerprint 대상에서 `__pycache__`/`.pyc` 등 생성물을 제외한다.
  5. 초기 ABI 산출물과 Solidity compiler 버전을 fingerprint에서 실제로 검사하도록 확정한다.
     현재 `abi_tree`는 `MISSING`이며 compiler 버전 항목 자체가 없다.
- 이유/재현:
  - 소스와 lockfile 변경 없이 테스트/compileall 전후로 fingerprint를 생성했다.
  - 이전 schema_tree: `abbbdf3ebc9d7dc077db40d88aa1390145646d51a118357f0b14a1c9ef0561c9`
  - 이후 schema_tree: `febfbf0145d0b4d6a9071112e60705c52698b2a603859d950c376d3f7641db32`
  - `tree_digest()`가 공통 Python 모델 디렉터리 아래의 모든 파일을 포함하므로
    테스트에서 생기는 bytecode도 해시에 들어간다. 마지막 실행 결과는 build의 JSON에 있다.
- 기대 출력: 테스트 실행 전후 Schema 해시가 동일하고 ABI/필수 도구가 누락되지 않은 fingerprint.
- 필수 재검증: bootstrap-check, env-check, mvp-up, seed, smoke, env-fingerprint;
  네 명 comparable 비교 및 clean-clone 재현.
- 기한/요청 기준: M2 기능 작업 시작 전; 현재 `main@4ee98f3`.

## 요청 2: Candidate 계약 동결 상태 확인

- 담당: M1 (공통 모델 소유자), 최종 확인/병합은 김형준
- 요청 인터페이스: `packages/python/originproof_core/models.py::CardPaymentNoticeCandidate`
- 현황: main은 9개 필드다. 조회한 `mvp/backend@bbaa4f9a7e206c0234c91e10479ce50de19cef91`은
  `transaction_id: str | None`를 추가해 10개 필드다. 해당 브랜치는 이 checkout에 병합하지 않았다.
- 요청: 통합 기준 Schema와 `transaction_id` 추출 필요 여부를 서면으로 확정한다.
  원본에 없는 transaction_id를 Proof ID나 Golden Fixture에서 만들어 넣지 않는다.
- 현재 main 기준 입력/기대 출력:

```text
[Origin Mock Bank]
카드 승인
카드 ****1234
154,000원
ORIGIN CAFE
2026-09-03 12:14
Proof ID: prf_demo_001
```

```json
{
  "issuer_name": "Origin Mock Bank",
  "masked_card": "1234",
  "amount_minor": 154000,
  "currency": "KRW",
  "merchant": "ORIGIN CAFE",
  "approved_at": "2026-09-03T03:14:00Z",
  "proof_id": "prf_demo_001",
  "confidence": 0.98,
  "missing_fields": []
}
```

위 confidence는 Mock 예시값이며 실제 모델 평가값이나 보정된 확률이 아니다.
금액 변경 입력에서는 `amount_minor=1540000`이어야 한다.
AI 출력에는 Verification/Lifecycle Status 또는 Reason Code를 추가하지 않는다.

- 필수 재검증: 공통 모델 직렬화/JSON Schema 일치, 정상/변경 Fixture 비교,
  누락 필드 null 처리, 금액 양수 검증, M1 소비자와의 계약 테스트.
- 기한/요청 기준: M2 기능 작업 시작 전; 현재 `main@4ee98f3`.

## 요청 3: Analyzer 의존성 및 Docker Fixture 전달 승인

- 담당: M2, 공유 lockfile/인프라 변경 승인은 통합 담당자
- 요청 파일: `services/analyzer/pyproject.toml`, `uv.lock`,
  필요 시 `infra/docker/analyzer.Dockerfile` 또는 `docker-compose.yml`
- 요청 변경: OpenAI SDK와 Pillow 추가 및 팀 lockfile 갱신 승인.
  현재 팀 lockfile에는 두 패키지가 없으므로 기존 Adapter를 그대로 복사하면 실행되지 않는다.
- 이유: Responses API + Pydantic Structured Outputs, 이미지 실제 디코딩/형식/프레임/크기 검증이 필요하다.
  FastAPI/uvicorn 등 팀의 기존 버전은 단독 프로젝트 버전으로 교체하지 않는다.
- Docker 전달 계약: 현재 Analyzer 이미지는 `fixtures/mvp`를 복사하지 않는다.
  Mock 이미지 replay를 Docker에서도 검사하려면 승인된 Fixture 전달 방식이 필요하다.
  알려진 합성 이미지의 hash-based replay를 실제 OCR/모델 성능으로 표시하지 않는다.
- 기대 출력: frozen install 및 Docker build 성공; API key 없는 Mock 기본 테스트 통과;
  live OpenAI 실행은 별도 opt-in.
- 필수 재검증: `uv sync --all-packages --all-groups --locked`,
  `make test-analyzer`, `make mvp-test`, `make smoke`, lint, typecheck, 이미지 보안/오류 회귀 테스트.
- 기한/요청 기준: M2 구현 및 공유 파일 수정 전; 현재 `main@4ee98f3`.

## 승인 후 M2 이식 범위

1. 팀 `originproof_core.CardPaymentNoticeCandidate`를 직접 사용한다.
   단독 프로젝트의 별도 Candidate 모델/Schema를 복사하지 않는다.
2. 기존 `originproof_analyzer.main:app`과 `/health/live` 응답을 보존한다.
3. `services/analyzer` 안에 Provider, 설정, 입력 검증, 필드 추출 서비스,
   prompt, 오류 처리, Mock/SDK transport 테스트, 평가 코드를 이식한다.
4. `fixtures/mvp`의 기존 두 Golden JSON은 변경하지 않고 합성 Text/이미지 평가 자산을 추가한다.
   Fixture 출처/목적/Schema 버전/기대 결과를 명시하고 변경은 M1 리뷰를 받는다.
5. Provider timeout/refusal/incomplete/rate-limit/schema mismatch 및 낮은 confidence를 처리한다.
   원본 입력, API Key, 무제한 모델 응답은 로그/오류 응답에 노출하지 않는다.
6. Provider/모델/prompt 버전 메타데이터를 기록하되 Backend로는 승인된 Candidate 계약만 반환한다.
7. 루트 Makefile/Compose/공통 모델을 단독 구현 버전으로 덮어쓰지 않는다.

이 문서는 로컬 Handoff 초안이다. 담당자에게 발송하거나 승인을 받았다고 간주하지 않는다.
