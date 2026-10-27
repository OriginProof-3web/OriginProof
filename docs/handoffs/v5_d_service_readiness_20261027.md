# D W6 후속 — 실제 최종 평가·이미지 평가 도구·연결 인계 (2026-10-27)

담당 D 여인준 @yijun0330, Codex 실행 보조. 작업 `V5-W5-D`, `V5-W6-D`, W7 인계 준비. 계획5.1 / 공통 계약v5-shared-0.2. 최신 `origin/phase/W6` **e29fa8ef6fbbe502cf248499167dbf74d75f8efc**에서 새 branch `codex/v5-w6-d-service-readiness`를 만들었습니다. 병합된 #94 branch와 기존 키·유료 journal·원본·기여 기록을 보존합니다. 기존 로컬 `a3f12d6`에는 미커밋 변경이 없었습니다. 공유/보존 phase는 수정하지 않습니다.

현재 입력은 **TEXT·DOCUMENT_IMAGE**, 음성/STT는 보류입니다. 모델은 사용자님의 **OpenAI gpt-6-luna** 선택을 유지합니다. #99의 Claude/RAG 제안은 사용자님의 기존 선택을 대체한 결정이 아니며 이번 변경에 추가하지 않습니다. Decisions API·회원가입·타인 경로 구현도 추가하지 않습니다.

## D가 이번에 완료한 독립 작업

1. 직접 승인 후 고정 최종 텍스트36개 한 번 실행: **33/36, macro-F1 0.9118421053, HIGH9/9**, grounding 거부0. 누적24+24+36=84회. 오분류 **C11→NO_CLEAR, C12→HIGH, C14→NO_CLEAR**를 보존하며 정답/분할/프롬프트/규칙을 수정·재실행하지 않았습니다. [전체 실측](../qa/v5-d-live-holdout-20261027.md). H01과 요청 문구를 공유하는 H11은 HIGH→HIGH로 별도 보고합니다. 검증 뒤 기대 근거 포함13/18·정확 경계0/18이며 모델/제품 최종 수용과 구분합니다.
2. 기존 이미지23개에 대한 `document_evaluation` 도구: 기존 check_pack·SemanticInput·prepare_conversion·analyze_conversion·CER·분류 지표를 재사용합니다. 기본 CLI는 **계획만** 만들고 callback·모델·키를 생성하지 않습니다. [실제 기본 계획](../qa/v5-d-document-evaluation-plan-20261027.json): 이미지23·미실행23, DP-U05 텍스트 전용 제외, 품질 점수null입니다.
3. 명시적 callback 평가에서는 변환기에는 이미지 bytes만, 분석기에는 변환 텍스트만 전달합니다. 라벨·원본 정답·기대 quote/ID를 전달하지 않습니다. 이미지 한 건의 변환+분석이 같은180초 이내 잔여 예산을 공유합니다. 손상·partial·잘못된 kind·timeout·취소를 검사하며 실패도 전체 분모에 남깁니다. 취소는 실패 결과로 삼키지 않습니다.
4. 이미지23개는 기존 개발 원본의 파생이며 새 독립 원본23개가 아닙니다. HIGH/CAUTION/NO_CLEAR 각6·UNDETERMINED5개로 불균형이고 텍스트 전용 U05는 제외합니다. 규칙/LLM 근거 수·모델 사용 불가·mock replay를 별도로 기록하여 fallback을 실제 모델 품질로 표시하지 않습니다. 픽셀/원본 offset과 변환 텍스트 근거를 구분합니다. 원본 quote 포함은 문자열 범위의 참고 수치이고 픽셀 정확도가 아닙니다. 원시 판독문·이미지 base64·예외 원문을 평가 결과에 쓰지 않습니다. callback의 실제 과금 횟수는 추정하지 않고null로 둡니다. 실제 사용 시 별도 승인/ledger를 연결해야 합니다.
5. 병합된 C의 `scripts/ci/test_v5_c_recovery.py`를 실제 일회용 PostgreSQL·별도 API 프로세스로 **7 PASS** 독립 재현했습니다. Registry와 분석기 응답은 합성 stub이며 실제 B Registry/모델 전체 연결 완료가 아닙니다. 기존 DB·체인을 초기화하지 않았습니다. 같은 실행의 보호 필드 검증100회는 p50 **15.0273ms**, p95 **16.1677ms**이며 로컬 HTTP/PostgreSQL+합성 Registry 구간입니다. 실제 RPC/모델·브라우저 지연이 아닙니다.
6. #99의 고정 **b0b77e26eaa93ee1a8b078e906a9130635e90f74**에 있는 A 작성 HTTP 기준선4개를 읽기 추출해 현재 W6 API·D 분석기에 대해 **4 PASS** 재현했습니다. 정상 Unicode 인용·D 보류·C quote/offset 거부를 검사합니다. ASGI in-process+SQLite·합성 인증이며 TCP/생산 lifespan·배포/브라우저 검사가 아닙니다. 원본 테스트는 복제 commit하지 않았고 타인 기여로 기록합니다.

## 실행 명령

```sh
export PATH=/Library/Developer/CommandLineTools/usr/bin:$PATH
export PYTHONPATH=services/analyzer/src:apps/api/src:packages/python:services/indexer/src:apps/api/tests:scripts/ci
.uv-venv/bin/python -m originproof_analyzer.document_evaluation
.uv-venv/bin/python -m pytest -q -o addopts= services/analyzer/tests/test_document_evaluation.py
.uv-venv/bin/python -m originproof_analyzer.review_packet --check
V5_C_LIVE_TEST=1 .uv-venv/bin/python -m pytest -q -o addopts= scripts/ci/test_v5_c_recovery.py
```

`--output NEW.json`은 기존 파일 덮어쓰기를 거부합니다. 이미지 평가 callback은 `async converter(SemanticInput) -> ConvertedText | dict`, `async processor(str) -> AnalysisReport`입니다. 실제 변환기의 `document_image_to_text`는 명시적으로 허용한 settings/client/enabled가 필요하고, 분석기는 기존 `PhishingAnalyzer`를 그대로 사용합니다. converter/client 자동 생성·환경 키 조회·유료 CLI 옵션은 만들지 않았습니다. 테스트에서는 네트워크를 차단한 기록 응답만 사용했습니다. 이미지 실제 평가로 표시하지 않습니다.

## C에게 요청할 구체적인 인계

| 우선순위 | 요청 | D가 제공한 것 / 연결 후 확인 |
| --- | --- | --- |
| 1 | 분석기 in-process 패키징 또는 별도 서비스 방식 확정. 현 구조에서는 **기존 callback의 in-process 주입을 최소안으로 제안**하며 C 소유 코드·배포 변경은 C가 결정 | `PhishingAnalyzer(settings=AnalyzerSettings(...))`의 기존 async text callback. 카드 추출 endpoint는 피싱 보고서 endpoint가 아니므로 재사용 금지. 새 wrapper/API가 필수라고 가정하지 않음 |
| 1 | 기본 API 엔트리포인트의 설정·시작/종료 주입. `API_WALLET_TEXT_INPUT_ENABLED`와 provider 설정을 별도로 연결. API Docker 이미지/의존성에 analyzer 포함 여부 확인 | 기본 API는 여전히 processor=None. 명시적 주입의 ASGI 기준선4개만 통과. 현재 AnalyzerSettings는 prefix 없음/env_file=None이며 API용 `API_` 설정·로컬 .env 읽기와 혼동하지 않음 |
| 1 | 이미지 업로드·receipt·소유권·크기/MIME·오류/보관/삭제/취소 계약. 변환 원문을 웹에 제공하는 방식과 근거 위치 계약 | 기존 PNG/JPEG/WebP 검증·단일 page1 변환·공통 텍스트 report+private segment 위치. C worker는 현재 TEXT UTF-8만 처리하므로 이미지 bytes를 문자열로 넘기지 않음. 공유 모델/생성물은 C가 원본에서 변경 |
| 2 | 실제 서버 URL(로컬 합성 환경), 같은 검증 SHA·환경·실행 명령·계정 준비 경로 인계 | 키·비밀번호는 문서/댓글/채팅으로 요청하지 않음. 생산 lifespan·재시작/취소·동시성/제한·PostgreSQL·실제 배포 패키징 후 D 재검증 |

## A·B·팀에게 요청할 것 (미발송)

| 담당 | 요청 |
| --- | --- |
| A | `apps/web`/제안된 `apps/web-v5` 중 시연 기준 확정, 같은 후보의 실행 명령. 이미지 업로드·판독문 확인·근거 강조·실패/보관·삭제 실제 연결. 코드 포인트 offset을 UTF-16 slice로 오해하지 않는지 확인 |
| A/C | 최종 오분류 C11/C12/C14와 근거 포함13/18의 수용/한계 검토. 기존 라벨·분할 재승인을 요청하는 것이 아님. 이미지23개가 텍스트 검토와 별개인 실제 판독 자료로 적절한지 검토 |
| B/C | #99 실제 배포/Adapter/RPC 전환·projection과 #96/#97 중복 관계 검토 및 동일 후보 SHA 인계. D가 타인 branch를 임의 병합하거나 #96/#97을 닫지 않음 |
| 팀 | 다른 실제 노트북/장비 재현 담당·환경, 최종 RC와 시연 동선·제출 조건 확정. 같은 RC로 전체 리허설3회 |

팀원에게 별도 메시지·리뷰 요청을 보내지 않았습니다. 표는 공유용 요청 초안이며 타인 승인/합의가 아닙니다.

## W1~W7 완료 조건과 남은 항목

- **W1**: 공통 계약·60개 A/C 정답/분할 확정과 텍스트 최종36 실행 완료. 모델/이미지 제품 수용 판정은 후속.
- **W2~W4**: 기존 독립 QA를 유지하고 실제 선택한 웹+API+Registry에서 공동승인·타 기관/자기 승인 거부·변조·QR 복사·동시 버전·철회·키 교체/사고·기존v1/v2/consume을 같은 후보로 재검사.
- **W5**: 텍스트 실제 서버 주입·문서 이미지 업로드/판독/분석·보관/삭제·AI/RPC 독립 실패·화면 근거까지 연결. 이미지 유료 범위는 미승인, 실제 이미지 호출0.
- **W6**: 같은 통합 후보의 V5-F01~20 수용표와 100회 일반 검증 지연·이미지 경로 지연·장애/복구·민감 로그·다른 장비·서비스 API 밖 독립 검증. 7개 실제 DB/API 복구도 Registry 합성임을 유지. Sepolia 결과는 #99의 타인 기록이며 D 독립 공개 체인 검증 완료로 올리지 않음.
- **W7**: 팀의 RC/배포·문서·제출 기준 고정 후 같은 후보 리허설3회·대체 장비·영상·제출 링크/파일 점검. 수정 시 새 후보로 재검증.

G07은 #91의 **RESOLVED_LOCAL_LEGACY**를 유지하고 신규 Registry 전체 복구 완료로 확대하지 않습니다. #84 소비 검토·A/C60개 검토·기존24회 승인을 다시 요청하지 않습니다. W6 branch 병합은 integration 승격·제품 단계 완료와 다릅니다. 이번 작업은 D 독립 구현/검사와 실제 텍스트 평가이며 전체 단계 완료가 아닙니다.
