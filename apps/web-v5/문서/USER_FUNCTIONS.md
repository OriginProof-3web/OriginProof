# 일반 사용자 기능

현재 실제 연결·검사 기준은 [웹 연결 검사 기록](WEB_CONNECTION_TESTS.md)입니다. 기존 합성 예시 미리보기를 실제 API 데이터로 교체했습니다.

개인 로그인 후 Proof ID/검증 링크를 조회하고, 권한 있는 수신자는 지급 요청 또는 공식 문서의 내용을 비교할 수 있습니다. ID 조회의 PROOF_ONLY와 필드 비교 결과를 구분합니다. 요청 사용은 필요한 backend API가 없어 비활성화되어 있습니다. 검증 내역은 현재 탭 메모리 요약이며 새로고침 뒤 초기화됩니다.

`협업 테스트 시작.command`로 서버를 실행하세요. 입력 없이 로그인하면 디자인 미리보기만 열리며 실제 인증은 되지 않습니다.

소스: `components/user/UserWorkspace.tsx`, `api-client.js`. 수정 후 `npm run build:sidebar`로 번들을 갱신합니다.
