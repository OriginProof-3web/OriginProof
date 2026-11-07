# D C-PR 재검토·충돌 정리·K10 확인 — 2026-10-31

D 여인준 `yijun0330`, 사용자 요청 “내가 할거는 다 해”에 따른 Codex 기술 검토·수정·검사 보조. 계획5.1 / v5-shared-0.2. 기존 [마무리 보고](v5-d-final-audit-20261030.md)와 [평가 사전 검토](v5-d-review-and-rc-prep-20261030.md)를 이어갑니다. 추가 유료0·누적133·운영 정책false입니다.

## 1. #106~#109 기술 승인

C가 #112를 #107에 반영하고 #108·#109 스택도 맞췄습니다. #112는 C 승인 후 병합됐습니다. #108/#109의 이전 검토 이후 diff는 검증된 #112의 `main.py`, `test_ai_connect_readiness.py`, `W6-D.md` 세 파일뿐임을 확인했습니다. #106 source는 기존 검토 때와 같습니다.

변경하지 않은 C #109 `a758cf3a51d564f6347a24d77fd7735439f05cfa`를 키/.env/.git 없는 git archive로 꺼내 AI 연결·이미지·보관·조회·가입 검사를 **53 PASS**로 재확인했습니다. SQLite/ASGI·합성 callback 검사이며 새 실제 모델·브라우저 수용이 아닙니다.

| PR | 검토한 HEAD | D 결정 |
| --- | --- | --- |
| #106 | `c180515893122ffe4b75dab1745c2502466d8b23` | [APPROVED](https://github.com/OriginProof-3web/OriginProof/pull/106#pullrequestreview-5714248840) |
| #107 | `2b2849e1698a8577837e85df376a086b116a67b2` | [APPROVED](https://github.com/OriginProof-3web/OriginProof/pull/107#pullrequestreview-5714249312), 기존 변경 요청 해소 |
| #108 | `5a4eb638945dc80107cac8c7486022f33746e68c` | [APPROVED](https://github.com/OriginProof-3web/OriginProof/pull/108#pullrequestreview-5714249844) |
| #109 | `a758cf3a51d564f6347a24d77fd7735439f05cfa` | [APPROVED](https://github.com/OriginProof-3web/OriginProof/pull/109#pullrequestreview-5714250316) |

D가 작성한 #112 한 줄 수정/검사는 C의 독립 리뷰·승인으로 확인했고, D가 자기 수정을 타인의 검토로 표시하지 않았습니다. 위 네 건은 D의 위임된 기술 리뷰이며 A 웹 리뷰·모델 품질·최종 RC 수용을 뜻하지 않습니다. 원격 PR 병합은 하지 않았습니다.

## 2. 최신 phase 반영과 기여 기록 충돌

이미 병합된 #103을 포함한 최신 `phase/W6` `f69f83e7170501e869c8944d55fff65b4ab444b0`만 D 작업 branch에 merge했습니다. merge 기록은 `907157a`입니다. 열린 C 스택을 D PR에 합치거나 과거 PR을 순서대로 다시 적용하지 않았습니다.

`W6-D.md`는 #112와 #113이 같은 맨 위에 기록을 추가해 충돌했습니다. D의 새 기록을 기존 첫 단락 다음으로 옮겨 두 변경의 삽입 위치를 분리했습니다. 공통 baseline5f7135b·#112 문서와의 3-way merge는 **exit0/충돌 marker0**, 두 기여 기록 모두 보존임을 확인했습니다. #112의 인계 자체를 삭제하거나 C의 미병합 코드를 중복 복사하지 않았습니다.

최신 phase 반영 후 D 지원 제어 검사105개와 stage43/consumer31=74개가 각각 통과했습니다. 두 실행의 모듈 범위를 구분하며 최종 제품 수용으로 합산하지 않습니다.

## 3. K10 — 붙여쓰기 누락은 현재 최소 사례에서 미재현

[C 제보](https://github.com/OriginProof-3web/OriginProof/issues/110#issuecomment-6524890158)는 “원격지원 앱(붙여 쓰기)을 놓침”입니다. 현재 규칙은 `원격\s*(?:제어|지원)`이므로 붙여쓰기와 띄어쓰기를 모두 허용합니다. 원문 전체가 공유되지 않아 실제 실패 경로는 확정하지 않습니다.

| 새 회귀 입력 | 기존 규칙 결과 |
| --- | --- |
| 원격지원 앱을 설치해 주세요. | HIGH / REMOTE_CONTROL_REQUEST |
| 원격 지원 앱을 설치해주세요. | HIGH / REMOTE_CONTROL_REQUEST |
| 보안 점검을 위해 원격지원 앱을 실행하십시오. | HIGH / REMOTE_CONTROL_REQUEST |
| 원격지원 앱을 설치하지 마세요. | 규칙 근거0 — 설치 금지문 |
| 원격 지원 앱 설치 안내입니다. | 규칙 근거0 — 행동 요구 없는 설명 |
| 피싱 교육 사례: ‘원격지원 앱을 설치해 주세요’는 사기 예시입니다. | 규칙 근거0 — 인용 예방 문맥 |

기존 parametrized 검사에 위6개를 추가했습니다. source 위치가 실제 quote와 일치하는 검사와 부정문·예방 문맥 검사를 재사용합니다. 관련 phishing/document/live-evaluation 검사 **116 PASS**, Ruff PASS입니다.

**분석 규칙·프롬프트·모델·정답·분할은 변경하지 않았습니다.** 동결 후보가 고정한 `phishing.py` SHA-256과 현재 파일이 동일합니다. 새 테스트 통과를 K10의 실제 제보 전체 해결로 선언하지 않습니다.

정확한 재현에 필요한 것은 **실패한 합성 입력 원문(공백·구두점 포함), 실행 SHA, LLM_PROVIDER 값, API의 status/risk_level/evidence/limitations**입니다. 키·token·비밀번호는 필요하지 않습니다. 정보가 인계되면 규칙·provider·서버 composition·화면 중 어느 경계의 문제인지 확인할 수 있습니다. 지금은 근거 없이 휴리스틱을 넓히거나 소진한 최종36/이미지23을 재실행하지 않습니다.

```sh
env -u OPENAI_API_KEY LLM_PROVIDER=mock \
  uv run --all-packages --all-groups --locked pytest -q \
  services/analyzer/tests/test_phishing.py \
  services/analyzer/tests/test_document_evaluation.py \
  services/analyzer/tests/test_live_evaluation.py
```

## 4. 남은 범위

C는 DP-C04를 현재 후보의 알려진 한계로 남기고 재평가하지 않는 데 동의했고, DP-U03도 “안전”으로 안내하지 않는 데 동의했습니다([C 확인](https://github.com/OriginProof-3web/OriginProof/pull/113#issuecomment-6524889279)). A 확인은 별도입니다. #113의 기존 C 승인은98ba8f4 기준이므로 이번 후속 변경의 재확인과 병합은 별도입니다.

현재 D가 가능한 PR 승인·최신 기준 반영·문서 충돌 정리·K10 최소 사례 조사/회귀는 수행했습니다. 실제 K10 실패 입력, A 웹 연결·공개 원본 export·최종 통합 RC가 필요합니다. 같은 최종 RC의 전체 수용·다른 실제 노트북·리허설3회·제출 확인은 아직 미완료입니다. 기존 실패·구버전 회귀·기여 기록을 보존하며 다른 사람 승인/리허설 결과를 만들지 않습니다.
