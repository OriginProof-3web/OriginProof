# D 평가 자료 점검 · clean 재현 · W2~W4 실패 사례

- 실행일: 2026-10-16 한국시간. 계획서 5.1 / 병합 기준 v5-shared-0.1.
- 작업 브랜치: `codex/v5-d-independent-qa`, 시작 `65ad8db90db46ff072b15408579f1ff5a65a1567`.
- 실행·검증 소스 SHA: **`40ab4da11c71d75d26b6b94145e53ee03e3d54a6`**. 이후 문서 커밋과 구분합니다.
- C 고정 소비 후보: #62 `eaa0d166269833cf7ee49675cfa777b0208c3725`의 Git archive. 이 후보의 v5-shared-0.2를 integration 기준으로 병합하지 않았습니다.
- 착수 fetch: origin/integration `33bc4f4e7456c5ef7c2df8c8bf09f8014e0169f8`, #56 MERGED, #62 OPEN/Draft·같은 SHA 확인. 원격 push/PR/병합 없음.
- [구조화 실제 결과](v5-d-readiness-results.json). 사람의 라벨/코드 리뷰·단계 완료는 대기입니다.

## 1. 합성 원본 60개 자체 점검

[원본](../../fixtures/synthetic/phishing_sources_v1.json)과 [사례별 D 자체 점검](../../fixtures/synthetic/phishing_sources_v1_review.json)을 연결했습니다. 원본 text·label·source_group·24/36 분할은 바꾸지 않았습니다. 60개 각각의 판단 근거와 A/C 리뷰 상태를 별도 파일에 기록했습니다. Codex의 자체 점검이며 사람/다른 작성자의 승인이 아닙니다.

- 형식 검사: 네 수준별 15개, 개발24/보류36, 인용30개 모두 원본 코드 포인트 범위와 일치. 동일 원문 및 NFC/공백 정리 후 동일 원문은 0개입니다. URL은 합성 example.invalid 하위만 사용합니다.
- 라벨 경계 리뷰 5개: **DP-H05·H07**은 독립 확인/연락 방해만으로 HIGH가 충분한지, **H08**은 정상 인증번호 입력과 기존 창구 회피 문맥의 결합, **C11**은 QR 로그인 설명만으로 판단 가능한지, **C14**는 암호화 첨부 자체를 과도하게 의심한 것인지 검토해야 합니다. H08의 기대 인용에 문맥을 더 포함할지도 확인합니다.
- 범위 표시 3개: **U05·U13·U15**는 판독/전사 실패를 설명하는 합성 문자열입니다. 실제 OCR/STT/이미지 실패 검사로 세지 않습니다.
- 분할 리뷰 3묶음: 인증번호 공유/예방 경고, 원격제어 설치/거절, 긴급 송금/예방 예시가 양쪽에 있습니다. 유사 문구라는 이유만으로 확정 누출로 처리하지 않았습니다. 고유 source_group ID만으로 독립 원본임을 입증할 수도 없으므로 A/C가 파생 관계를 확인한 뒤 분할을 고정해야 합니다.

`DRAFT_REVIEW_REQUIRED`, labels_human_reviewed=false, 입력 미정과 보류36개 모델 예측 NOT_RUN을 유지합니다. 보류 원문의 주석 점검만 수행했고 모델 예측·규칙 튜닝은 하지 않았습니다. OpenAI만 사용하는 방향은 선택됐지만 세부 모델·유료 전송/평가 범위는 미정입니다.

## 2. 새 clean clone 재현

사용자 checkout을 복사/초기화하지 않고 `git clone --no-hardlinks`로 새 clone을 만들었습니다. 최종 실행은 위 고정 SHA이며 Git dirty=false, Git alternates 없음입니다. 기존 `.uv-venv`·개인 `.env`는 가져오지 않았습니다. 새 venv에 고정 lock의 51개 패키지를 설치했고 링크 대신 복사 모드를 사용했습니다. 동일 Mac에서 수행한 새 clone/venv 재현이며 다른 장비/OS의 성공을 뜻하지 않습니다.

| 검사 | 실제 결과 | 범위 |
| --- | --- | --- |
| 전체 Python 회귀 | **292 PASS / 0 FAIL / 0 SKIP**, 기존 anyio deprecation warning 1 | 기존 API 단위/ASGI·코어·Analyzer·SDK mock·fixture. 임시 autouse guard가 socket connect/connect_ex를 거부하고 시도 자체도 실패 처리 |
| 개발24 규칙 기준선 재현 | 24개·보류17·오류0, macro-F1 **0.451863**, HIGH recall 1.0(6개) | 기존 결과와 사례별 예측·혼동행렬·근거 집계 동일. 실제 LLM 성능 아님 |
| `make generate` | PASS, Git diff 없음 | 원본 생성기로 Schema/TS/OpenAPI·v1/v5 Golden/예시 재생성 |
| `make bootstrap-check env-fingerprint` | PASS | 구조·필수 도구/설정 확인. 서비스 연결 검사 아님 |
| Ruff·compileall·Git diff | PASS | 새 D QA 세 파일 포함. compileall은 정적 타입 검사 아님 |

처음 uv가 sandbox의 macOS 시스템 설정 조회에서 panic을 냈으므로 동일 명령을 허용된 실행 환경에서 재시도했습니다. 오프라인 캐시에 wheel이 없어 lock hash가 고정된 패키지만 원래 배포처에서 설치했습니다. 새 의존성·lock 변경은 없습니다. 첫 bootstrap-check의 `.env` 누락은 개인 설정을 복사하지 않은 결과이며 clone의 `.env.example`로 폐기용 `.env`를 만들어 통과했습니다.

실제 환경은 Python 3.13.7 / uv 0.8.17 / pytest 8.4.2 / FastAPI 0.115.14 / OpenAI SDK 2.54.0입니다. 지정 Python 3.13.0과 차이가 있습니다. Node 24.8.0·pnpm 11.19.0·Docker 29.7.2·Compose 5.5.1이며 host forge는 없습니다. 전체 웹/Contract를 새로 검사한 결과로 확대하지 않습니다.

최소 재현은 다음과 같습니다. 고정 SHA는 로컬 D Git 객체에 있어야 하며 이 작업에서 원격 push는 하지 않았습니다.

```sh
OP_D_SOURCE=$(pwd)
OP_D_CLEAN=$(mktemp -d)
git clone --no-hardlinks --no-checkout "$OP_D_SOURCE" "$OP_D_CLEAN"
git -C "$OP_D_CLEAN" checkout --detach 40ab4da11c71d75d26b6b94145e53ee03e3d54a6
cd "$OP_D_CLEAN"
UV_PROJECT_ENVIRONMENT=.uv-venv UV_LINK_MODE=copy uv sync --frozen --all-packages --all-groups
cp .env.example .env
chmod 600 .env
mkdir -p build
cat > build/qa_network_guard.py <<'PY'
import socket
import pytest

@pytest.fixture(autouse=True)
def block_runtime_network(monkeypatch):
    attempts = []
    def denied(*args, **kwargs):
        attempts.append(True)
        raise AssertionError('clean QA forbids real socket connections')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket.socket, 'connect_ex', denied)
    yield
    assert not attempts, 'runtime network connection attempted during clean QA'
PY
env -u OPENAI_API_KEY LLM_PROVIDER=mock \
  PYTHONPATH=build:apps/api/src:packages/python:services/analyzer/src \
  .uv-venv/bin/python -m pytest -q -p no:cacheprovider -p qa_network_guard
```

## 3. W2~W4 D 독립 실패 사례

세 파일은 일반 pytest 자동 수집 경로 밖에 두고 C 후보를 명시적으로 소비합니다. C의 기존 `test_wallet_runtime` fixture·onboarding/signing/publication/revocation 준비 helper를 재사용했고 C 테스트를 D의 신규 구현으로 기록하지 않습니다. D는 별도 요청·변조·실패 단언과 plan ID 연결을 추가했습니다. 원문·서명 계산·SQLAlchemy/HTTP는 실행하지만 Registry 스냅샷·승인·상태 전이는 합성입니다. 네트워크와 실제 모델 호출을 차단합니다.

| D 검사 파일 | 실제 결과 | 검사한 경계 |
| --- | --- | --- |
| [W2 governance](../../fixtures/finals/v5_d_w2_governance_qa.py) | **12 PASS** | 자기/타 기관 승인·도메인/메일 코드 오류, 만료/nonce/기관/메타데이터 변경, 1명/서로 다른2명/중복 승인 소비, CONFIRMED receipt만 있고 승인 효과가 없는 UNKNOWN |
| [W3 content](../../fixtures/finals/v5_d_w3_content_qa.py) | **13 PASS** | 격리된 합성 Bank/Office와 두 템플릿, 금액·계좌·URL·제목의 단일 변조/원본 재검사, ID/부분 비교, DB bytes/content/metadata/name/version 변조, 원본 부재 |
| [W4 lifecycle](../../fixtures/finals/v5_d_w4_lifecycle_qa.py) | **5 PASS** | 최신 철회 뒤 구버전 자동 활성화 없음, 순차 경쟁 draft 예약, 정지 중 발행 거부/철회 허용, 정상 키 교체의 과거 서명 보존/구키 거부/유출 경고, deadline 경계 |

C 소비 환경은 Python 3.13.7 / pytest 9.1.1 / FastAPI 0.142.2 / Starlette 1.7.0이며 그 후보의 lock과 핵심 소스 hash를 JSON에 기록했습니다. D 기준 환경에 C 의존성을 혼합 설치하지 않았습니다.

총 **30 PASS / 0 FAIL / 0 SKIP**이며 기존 292개와 검사 계층이 다릅니다. 개수를 신규 본선 전체 수용 완료로 환산하지 않습니다. 두 기관은 각 테스트의 독립 fixture에서 확인했으며 두 기관의 동시 운영/격리·브라우저 성공은 별도입니다.

처음 26 PASS/4 FAIL은 D QA 준비 오류였습니다. 중복 승인 스냅샷은 생성 단계에서 이미 거부되어 유효 포트 객체 뒤 오염을 주입하는 방식으로 바꿨고, 공식 템플릿은 올바른 합성 기관에 연결했으며, 키 등록 블록은 관측 블록을 넘지 않게 고쳤습니다. 제품 코드·기대 보안 결과를 바꾸거나 skip/xfail로 숨기지 않았습니다. 수정 후 같은 C SHA에서 30개가 통과했습니다.

```sh
# OP_D_ROOT: 위 실행 SHA의 D clone, OP_C_ROOT: 아래 고정 C archive와 그 locked venv
# C archive 준비: git archive eaa0d166269833cf7ee49675cfa777b0208c3725 | tar -x -C "$OP_C_ROOT"
cd "$OP_C_ROOT"
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH="$OP_C_ROOT/packages/python:$OP_C_ROOT/apps/api/src:$OP_C_ROOT/apps/api/tests:$OP_C_ROOT/services/analyzer/src:$OP_C_ROOT/services/indexer/src" \
  .uv-venv/bin/python -m pytest -q -p no:cacheprovider \
  "$OP_D_ROOT/fixtures/finals/v5_d_w2_governance_qa.py" \
  "$OP_D_ROOT/fixtures/finals/v5_d_w3_content_qa.py" \
  "$OP_D_ROOT/fixtures/finals/v5_d_w4_lifecycle_qa.py"
```

## 남은 실제 연결과 인계

- W2: 신규 A/B/C 동일 후보의 기관 신청부터 2-of-3 승인·중복/만료·단독 정지/공동 복구를 실제 브라우저/체인에서 확인합니다.
- W3: 실제 신규 Registry/DB의 두 기관 동시 운영·서명/직접 제출·원본 바이트 비교·QR 전달 메시지·DB 상태 조작과 v1/v2 연결 회귀가 남습니다.
- W4: 실제 동시 제출 원자성·nonce 재전송·다른 체인/컨트랙트·키 사고 공동 복구·기존 consume은 이 합성/순차 검사로 충족하지 않습니다.
- **DG12는 C 수정 대기**, **G07은 B/C 원인/수정 인계 대기**입니다. 앞선 결과를 유지했고 이번 묶음에서는 두 문제를 재실행하거나 해결 처리하지 않았습니다.
- 입력·세부 모델·유료 범위 결정, A/C 라벨·분할 리뷰, 실제 모델/보류36개 평가, 다른 장비/신규 A/B/C 브라우저·공개 네트워크 검사는 미실행입니다. 새 의존성·공통 모델/생성기·제품 기능·원격 Git 변경은 없습니다.

이 작업은 D의 독립 자료 점검·재현·실패 사례 준비/합성 실행입니다. 단계 전체 완료나 사람 리뷰를 대신하지 않습니다. [W1-D](../portfolio/W1-D.md), [W2-D](../portfolio/W2-D.md), [W3-D](../portfolio/W3-D.md), [W4-D](../portfolio/W4-D.md)에 실제 기여를 연결합니다.
