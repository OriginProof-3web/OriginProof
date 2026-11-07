# OriginProof — 다른 장비 재현 및 최종 리허설 안내

작성일: 2026-10-31  
대상: 다른 실제 노트북에서 재현을 담당할 팀원, C 통합 담당, D 검증 담당

이 문서는 실행 절차입니다. 실제 검사·리허설을 완료했다는 기록이 아닙니다. **C가 최종 RC의 40자리 커밋 SHA와 실행 묶음을 확정한 뒤 진행합니다.**

## 1. 목표와 역할

다른 실제 노트북에서 동일한 최종 코드를 새로 받아 직접 실행하고, 그 버전으로 전체 리허설을 3회 진행합니다. 서버까지 해당 장비에서 구동해 재현합니다. 기존 PC 서버에 브라우저로 접속한 검사는 브라우저 호환성 확인으로 별도 기록합니다.

| 담당 | 할 일 |
| --- | --- |
| C | 최종 RC SHA·환경설정 예시·실행 명령·계정 준비 방법·체인/배포 정보를 인계 |
| 재현 담당 팀원 | 다른 실제 노트북에서 설치·자동 검사·실제 화면 검증·결과 기록 |
| A/B/C | 자기 영역의 실패 원인 확인과 필요한 수정·설정 인계 |
| D | SHA와 환경·실행 증거·실패/미실행 항목을 대조하고 수용표에 반영 |

같은 PC의 별도 폴더·새 clone·가상환경·CI 통과는 별도의 유용한 근거로 보존하되, 실제 두 번째 노트북 검증으로 표시하지 않습니다.

## 2. 시작 전에 C에게 받을 것

- [ ] 최종 RC의 전체 40자리 커밋 SHA
- [ ] 환경설정 예시와 필요한 값의 준비 방법
- [ ] DB migration·합성 계정 seed·웹/API/DB/체인의 실행 및 종료 명령
- [ ] 테스트할 화면 주소와 역할별 합성 계정 준비 방법
- [ ] 사용할 네트워크·chain ID·Registry 주소·배포 manifest
- [ ] 현재 지원 범위·정상 기대 결과·알려진 한계
- [ ] 발표 시간·제출 파일 형식·용량·제출 채널 등 실제 행사 조건

최종 RC가 없으면 먼저 설치 준비와 개발용 재현까지만 진행하고, 최종 RC 수용 완료로 표시하지 않습니다. 비밀키·API 키·계정 비밀번호는 문서·Git·단체 채팅에 넣지 않습니다.

## 3. 다른 노트북의 도구 준비

아래는 작성 시점 저장소 CI의 기준입니다. 실제 RC에서 버전이 바뀌었다면 해당 RC의 설정과 lockfile을 따릅니다.

| 도구 | 기준 |
| --- | --- |
| Git | 저장소 접근이 가능한 계정 |
| Python | 3.13 계열 |
| uv | CI 기준 0.8.17 |
| Node.js | CI 기준 22.18.0 |
| pnpm | CI 기준 11.19.0 |
| Docker | 엔진 실행 상태, Docker Compose 사용 가능 |
| Foundry | 1.4.4, `forge`·`anvil`·`cast`를 PATH에서 실행 가능 |

아래 명령은 Mac/Linux의 Bash 또는 Zsh 기준입니다. Windows에서는 WSL2/Ubuntu와 Docker의 WSL 연동을 준비하고 그 터미널에서 실행합니다.

```bash
git --version
uv --version
node --version
pnpm --version
docker --version
docker compose version
docker info
forge --version
anvil --version
```

도구가 없거나 Docker가 실행되지 않으면 먼저 준비합니다. 준비 실패도 환경 오류로 기록합니다.

## 4. 새 폴더에 최종 RC 받기

기존 작업 폴더를 덮어쓰지 않고 새 폴더를 사용합니다. 아래 SHA 자리에는 C가 확정한 실제 값을 넣습니다.

```bash
git clone https://github.com/OriginProof-3web/OriginProof.git OriginProof-rc-check
cd OriginProof-rc-check
git fetch origin

OP_RC_SHA="C가_확정한_40자리_SHA"
git switch --detach "$OP_RC_SHA"
git rev-parse HEAD
git status --short
```

`git rev-parse HEAD` 출력이 전달받은 SHA와 같고, `git status --short`에 예상하지 못한 변경이 없어야 합니다. 다른 branch의 최신 코드를 임의로 섞지 않습니다.

## 5. 의존성 설치와 자동 검사

기본 재현은 mock 공급자로 진행합니다. 실제 OpenAI 호출은 이 절차의 승인이 아니며 별도로 합의한 실행 범위에서만 진행합니다. 기존 개인 `.env`나 키를 다른 노트북에 복사하지 않습니다.

한 줄씩 실행하고 실패하면 해당 명령과 결과를 남깁니다.

```bash
export UV_PROJECT_ENVIRONMENT=.uv-venv
export LLM_PROVIDER=mock
unset OPENAI_API_KEY

uv sync --all-packages --all-groups --locked
pnpm install --frozen-lockfile
mkdir -p build/other-device

git rev-parse HEAD > build/other-device/commit.txt
make env-fingerprint
make test
make lint
make typecheck
make generate
git diff --exit-code
```

환경 정보는 `build/environment_fingerprint.json`에 생성됩니다. 환경 확인용 `make env-check`에는 로컬 `.env`가 필요하므로, 실행하려면 C의 RC 설정 예시로 별도 준비합니다.

이어서 계약과 실제 DB/API 복구 검사를 실행합니다. 아래 live 검사는 테스트용 일회용 자원을 사용하며 기존 Compose DB를 초기화하는 절차가 아닙니다.

```bash
# 고정된 계약 라이브러리 준비
FOUNDRY_BIN_DIR="$(dirname "$(command -v forge)")" make bootstrap-contracts
forge test --root packages/contracts

# 실제 복구 검사에 필요한 로컬 PostgreSQL 이미지
docker pull postgres:16.4-alpine
make test-w6-c-live
make test-v5-c-live
```

### 자동 검사 판정

- 실패·오류가 없어야 합니다. 실제 통과 개수는 출력 그대로 기록합니다.
- `SKIP`은 통과로 세지 않고 이름·이유·별도 실행 여부를 기록합니다.
- 생성물 재생성 후 예상하지 못한 Git diff가 없어야 합니다.
- Python `make typecheck`는 현재 compileall 구문 검사입니다.
- 자동 검사 통과만으로 전체 웹 동선·이미지 인식·최종 수용 완료를 선언하지 않습니다.
- `make reset`·`make demo-reset`은 사용하지 않습니다. 데이터 삭제가 필요하면 C가 지정한 폐기 가능한 검사 환경인지 먼저 확인합니다.

## 6. 실제 웹·API·DB·체인 확인

C가 인계한 **해당 RC의 실행 명령**으로 서비스를 띄웁니다. 일반 MVP 기동 성공을 새 v5 기능 전체 완료로 대신하지 않습니다. 문서 이미지 정상 처리가 실제 모델을 필요로 하면 별도 승인된 범위에서 확인하고, mock 실패 처리를 정상 판독으로 표시하지 않습니다.

| 흐름 | 확인할 내용 | 결과 |
| --- | --- | --- |
| 기관 준비 | 신청·내부 확인·키 보유 증명·서로 다른 2-of-3 승인 | 미실행 |
| 발행·검증 | 문서 발행·정상 원본·금액/계좌/링크 변조·비교 범위 | 미실행 |
| 버전·상태 | 다음 버전·과거 버전·철회·정지/키 교체 영향 | 미실행 |
| 분석 | 선정 텍스트·문서 이미지의 정상/실패 처리·근거·한계 표시 | 미실행 |
| 보관·권한 | 보관·조회·삭제·타인 접근 거부·늦은 결과 차단 | 미실행 |
| 장애·회귀 | API/RPC/분석 실패·복구·기존 v1/v2·권한/consume 회귀 | 미실행 |

화면 응답과 실제 API·DB·체인 상태가 일치하는지 확인합니다. `/health/live`는 프로세스 생존, `/health/ready`는 RC runbook의 준비 조건으로 판정하며 둘을 구분합니다.

## 7. 같은 RC로 전체 리허설 3회

세 번 모두 발표 전체 동선을 처음부터 끝까지 수행합니다. 한 기능만 세 번 실행한 결과는 전체 리허설 3회가 아닙니다. SHA·배포·데이터 기준을 기록하고, 장애 대체 설명·영상 전환·파일/링크 접근도 함께 확인합니다.

| 회차 | RC SHA·배포·장비 | 전체 동선 | 장애 대체·영상 전환 | 파일·링크 | 결과 |
| --- | --- | --- | --- | --- | --- |
| 1 | 미기록 | 미실행 | 미실행 | 미확인 | NOT_RUN |
| 2 | 미기록 | 미실행 | 미실행 | 미확인 | NOT_RUN |
| 3 | 미기록 | 미실행 | 미실행 | 미확인 | NOT_RUN |

실패는 그대로 남깁니다. 수정이 들어가면 새 RC를 확정하고 그 버전에 맞춰 검사와 리허설 기록을 갱신합니다. 이전 실패나 과거 버전의 결과를 삭제하지 않습니다.

## 8. 팀에 전달할 결과 양식

아래 내용을 D와 C에게 전달합니다. 장비는 “A의 Windows 노트북”, “B의 MacBook”처럼 실제 두 번째 장비임을 구분할 정도로 적고, 일련번호 등 불필요한 개인정보는 제외합니다.

```text
[다른 장비 재현 결과]
검사자 / 실행일:
실제 사용한 장비 / OS / CPU 구조:
RC 커밋 SHA:
체인 / chain ID / Registry 주소 / manifest:
Python / uv / Node / pnpm / Docker / Foundry 버전:

설치 및 생성물 검사:
Python 검사 결과 / SKIP 이유:
계약 검사 결과:
실제 DB/API 복구 검사 결과:
실제 웹 동선 확인 결과:
AI 공급자 및 실제 유료 호출 여부:

전체 리허설 1회:
전체 리허설 2회:
전체 리허설 3회:

실패 / 미실행 / 알려진 한계:
로그·영상·제출 파일 링크:
환경 정보: build/environment_fingerprint.json
코드 정보: build/other-device/commit.txt
```

테스트 로그·JUnit XML·화면/영상이 있다면 함께 인계합니다. 공유 전에 키·token·비밀번호·실제 개인정보가 포함되지 않았는지 확인합니다.

## 9. 완료 처리 기준

- [ ] 실제 두 번째 노트북에서 실행했다.
- [ ] 최종 RC SHA와 검사한 코드 SHA가 같다.
- [ ] 환경·설치·검사 결과와 SKIP 이유가 기록됐다.
- [ ] 실제 웹/API/DB/체인 동선을 확인했다.
- [ ] 같은 RC로 전체 리허설 3회 결과가 남아 있다.
- [ ] 대체 영상과 제출 파일·링크 접근을 확인했다.
- [ ] D/C가 증거와 실패·미실행 항목을 대조했다.

절차 문서·체크리스트 작성은 준비 완료이며, 위 실제 실행과 결과 확인을 대신하지 않습니다.
