# D 이미지 의존성 보안 보완 — 2026-10-21

- 작업: V5-W5-D·V5-W6-D의 입력 처리 의존성/보안 QA, 계획서5.1·공유 계약0.2.
- 작업 브랜치: `codex/v5-w5-d-dependency-security`, 시작 `phase/W5@15c5588f9e96e2f530bb0e891c76af79b22a123c`.
- 실행 코드 SHA: `781b96ea9654a2bf277fa3adf38f9f4269bf46e1`. 이후 문서 커밋과 구분합니다.
- 담당: D 사용자 지시로 Codex가 원인 분석·최소 의존성 갱신·검사를 수행했습니다. 공유 lockfile은 C 재리뷰 대상이며 사람의 승인/기여 비율을 추정하지 않았습니다.

## 문제와 수정

D QA의 새 CI에서 stage/consumer/Python/contracts는 통과했으나 [c-recovery](https://github.com/OriginProof-3web/OriginProof/actions/runs/39565680934/job/119107254902)는 `make security`에서 중단됐습니다. 보안 감사가 Pillow12.3.0의8건과 certifi2026.7.22의1건, 총9건을 보고했습니다. 실제 프로세스 복구 검사는 이 실패 뒤 실행되지 않았습니다. 같은 lockfile의 로컬 감사로 재현했습니다.

| 패키지 | 이전 lock | 수정 lock | 변경 |
| --- | --- | --- | --- |
| Pillow | 12.3.0 | 13.0.0 | D analyzer의 범위를 `>=13.0,<14`로 조정 |
| certifi | 2026.7.22 | 2026.10.19 | 기존 전이 의존성의 lock만 갱신 |

`uv lock --upgrade-package pillow --upgrade-package certifi`로 재생성했고 TOML을 비교하여 두 버전만 바뀌었음을 확인했습니다. 새 라이브러리·공유 모델·API·서명·입력 지원은 추가하지 않았습니다. 기존 v1 이미지 입력의 MIME/signature/크기/손상/폭탄 검사를 유지합니다. Pillow는 major 갱신이므로 기존 입력 회귀를 실행했으며 실제 모델/외부 TLS 연결 검증으로 확대하지 않습니다.

근거: [Pillow13 공식 변경·보안 기록](https://pillow.readthedocs.io/en/stable/releasenotes/13.0.0.html), [certifi 공식 보안 권고](https://github.com/certifi/python-certifi/security/advisories/GHSA-6q48-6c7w-9gw2). certifi 권고의 수정 릴리스 표기와 감사 도구의 제시값 차이는 숨기지 않고, 현재 배포된 `2026.10.19` lock에서 실제 재감사0건을 기준으로 기록합니다.

## 실제 검사

- 고정 pip-audit2.10.1의 `make security`: 이전9건/2패키지 → 수정 후 **0건**, exit0. 검사 시점 advisory 기준이며 미래 취약점 부재를 보장하지 않습니다.
- 같은 phase 기반 `make test`: **600 PASS / 10 SKIP**, 기존 Starlette warning1. 기존 이미지 parser·SDK mock·API/core/indexer 회귀입니다. 실제 체인/PostgreSQL/프로세스 복구 opt-in은 미실행입니다.
- Python3.13.7·pytest9.1.1·FastAPI0.142.2·Pillow13.0.0·certifi2026.10.19.
- 첫 로컬 감사 도구 설치는 이전 임시 uv 캐시의 METADATA 누락으로 실패했습니다. 새 격리 캐시로 같은 명령을 재시도했고 기존 lock의9건과 수정 lock의0건을 확인했습니다. 보안 결과를 skip/ignore하지 않았습니다.

## 인계

C가 공유 lockfile·기존 TLS 소비 영향을 재리뷰해야 합니다. CI에서 실제 c-recovery가 다시 실행된 결과와 D 분석기 stack의 회귀는 별도 확인합니다. 이 보안 수정으로 G07·실제 지갑/브라우저·선정 입력·모델 품질·단계 완료를 해결 처리하지 않습니다. 유료 모델 호출·운영 배포·원격 병합은 하지 않았습니다.
