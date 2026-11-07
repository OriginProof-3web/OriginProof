# 기업 메인 기능

현재 실제 연결·검사 기준은 [웹 연결 검사 기록](WEB_CONNECTION_TESTS.md)입니다. API 기준은 C PR #36 고정 SHA입니다.

실제 기관 로그인 세션으로 자기 기관 상태·키·신청 현황을 조회하고, 키 등록/교체/폐기, 지급 요청·공식 문서 발행, 발행 목록/상세, 수신자 선택, 감사 이력 및 Operation 재조회/허용된 복구를 실행합니다. 화면에서 임의 기관으로 바꾸지 못합니다. Proof 폐기·consume·QR 생성은 미연결입니다.

기관 추가 신청 입력은 현재 API의 issuer_name만 저장합니다. 미지원 기업 정보는 비활성화했고 공개 개인 회원가입은 서버 미구현으로 안내합니다.

`협업 테스트 시작.command`로 서버를 실행하세요. 입력 없이 로그인하면 디자인 이동만 하며 보호 API는 인증을 요구합니다.

소스: `components/business/BusinessWorkspace.tsx`, `business-entry.tsx`, `api-client.js`. 수정 후 `npm run build:business`로 번들을 갱신합니다. 공통 SidebarNav/GlideMenu 디자인은 유지합니다.
