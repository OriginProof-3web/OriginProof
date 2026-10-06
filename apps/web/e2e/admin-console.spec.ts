import {test,expect} from '@playwright/test';
import {readFileSync} from 'node:fs';
const accounts=process.env.ORIGINPROOF_TEST_ACCOUNTS;
test.use({trace:'off',video:'off',screenshot:'off'});
// Real suites share the unchanged API login/request rate limits.
test.setTimeout(180000);
test.beforeEach(async()=>{await new Promise(resolve=>setTimeout(resolve,61000));});
test.skip(!accounts||process.env.ORIGINPROOF_WEB_BASE_URL!=='http://127.0.0.1:8768','Local 8768 operator console only; no test role proxy in production.');
test('8768 administrator combines real issuer, recipient and operator tests',async({browser})=>{
 const context=await browser.newContext({reducedMotion:'reduce'});const page=await context.newPage();
 try{
  expect((await context.request.get('/test-api/bank/v1/auth/me')).status()).toBe(403);
  const row=(JSON.parse(readFileSync(accounts!,'utf8')) as {username:string,password:string}[]).find(a=>a.username==='operator')!;
  await page.goto('/user-login.html');await page.getByLabel('계정 이름').fill(row.username);await page.getByLabel('비밀번호',{exact:true}).fill(row.password);await page.getByRole('button',{name:'Sign In',exact:true}).click();
  await expect(page).toHaveURL(/admin.html/);await expect(page.getByRole('heading',{name:'기관 상태',exact:true})).toBeVisible();
  await page.getByLabel('테스트 기관',{exact:true}).selectOption('office');await expect(page.getByRole('heading',{name:'Origin Mock Office',exact:true})).toBeVisible();
  await page.getByLabel('테스트 기관',{exact:true}).selectOption('bank');await expect(page.getByRole('heading',{name:'Origin Mock Bank',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Proof 발행',exact:true}).first().click();await page.getByRole('button',{name:'합성 예시 채우기'}).click();await page.getByLabel('지정 수신자',{exact:true}).selectOption({label:'recipient'});await page.getByRole('button',{name:'Proof 발행',exact:true}).last().click();
  const status=page.locator('.uw-shell .uw-notice[role=status]');await expect(status).toContainText('prf_');const id=(await status.innerText()).match(/prf_[A-Za-z0-9_-]+/)![0];
  await page.getByRole('button',{name:'발행 목록',exact:true}).last().click();await page.getByRole('button',{name:'검증 QR 보기'}).click();await expect(page.getByRole('img',{name:'관리자 Proof 조회 화면으로 이동하는 QR 코드'})).toBeVisible();
  const nav=page.getByRole('navigation',{name:'관리자 테스트 메뉴'});
  await nav.getByRole('button',{name:'개인 기능',exact:true}).click();await page.getByLabel('Proof ID / 검증 링크').fill(id);await page.getByRole('button',{name:'조회',exact:true}).click();await expect(page.getByText('PROOF_ONLY',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'내용 비교',exact:true}).first().click();await page.getByRole('button',{name:'발행 값 채우기'}).click();await page.getByRole('button',{name:'내용 비교',exact:true}).last().click();await expect(page.locator('.uw-comparison')).toContainText('VERIFIED · FULL_COMPARISON');
  await page.getByLabel('금액 (최소 화폐 단위)',{exact:true}).fill('85001');await page.getByRole('button',{name:'내용 비교',exact:true}).last().click();await expect(page.locator('.uw-comparison')).toContainText('AMOUNT_MISMATCH');
  await page.getByRole('button',{name:'요청 사용',exact:true}).first().click();await page.getByRole('checkbox').check();await expect(page.getByRole('button',{name:'1회 사용 요청 실행'})).toBeEnabled();await page.getByRole('button',{name:'1회 사용 요청 실행'}).click();await expect(page.getByText('CONSUMED',{exact:true})).toBeVisible();await expect(page.getByRole('button',{name:'1회 사용 요청 실행'})).toBeDisabled();
  expect((await context.request.get('/api/v1/auth/me')).ok()).toBeTruthy();expect((await (await context.request.get('/api/v1/auth/me')).json()).role).toBe('operator');
  // Start the operator/Analyzer segment in a fresh rate-limit window.
  await new Promise(resolve=>setTimeout(resolve,61000));
  await nav.getByRole('button',{name:'기관 승인',exact:true}).click();await expect(page.getByRole('heading',{name:'기관 승인',exact:true})).toBeVisible();await page.getByRole('button',{name:'합성 텍스트 채우기'}).click();await page.getByRole('button',{name:'AI 후보 추출',exact:true}).click();await expect(page.locator('#operator-panel pre[role=status]')).toContainText('85000');
  await nav.getByRole('button',{name:'검사 결과',exact:true}).click();await expect(page.getByRole('heading',{name:'협업 테스트',exact:true})).toBeVisible();
  await expect(page.getByRole('heading',{name:'최신 GitHub · 김형준님 진행 상태',exact:true})).toBeVisible();
  await expect(page.getByRole('link',{name:/PR #52/})).toBeVisible();
  await expect(page.getByText(/mixed 장애 17 PASS\/1 FAIL/)).toBeVisible();
  await page.getByRole('button',{name:'사이드바 접기',exact:true}).click();await expect.poll(async()=>(await page.locator('#sidebar-root').boundingBox())!.width).toBeLessThan(100);
  await page.setViewportSize({width:390,height:844});await expect(page.getByRole('heading',{name:'협업 테스트',exact:true})).toBeVisible();expect(await page.locator('body').evaluate(body=>body.scrollWidth)).toBeLessThanOrEqual(390);
 }finally{await context.close();}
});

test('administrator shows latest GitHub progress without claiming team QA as local passes',async({browser})=>{
 const context=await browser.newContext({reducedMotion:'reduce'});
 try{
  const page=await context.newPage();const row=(JSON.parse(readFileSync(accounts!,'utf8')) as {username:string,password:string}[]).find(a=>a.username==='operator')!;
  await page.goto('/user-login.html');await page.getByLabel('계정 이름').fill(row.username);await page.getByLabel('비밀번호',{exact:true}).fill(row.password);await page.getByRole('button',{name:'Sign In',exact:true}).click();
  await expect(page).toHaveURL(/admin.html/);
  await page.getByRole('navigation',{name:'관리자 테스트 메뉴'}).getByRole('button',{name:'검사 결과',exact:true}).click();
  await expect(page.getByRole('heading',{name:'최신 GitHub · 김형준님 진행 상태',exact:true})).toBeVisible();
  await expect(page.getByRole('link',{name:/PR #52/})).toBeVisible();
  await expect(page.getByText(/mixed 장애 17 PASS\/1 FAIL/)).toBeVisible();
  await expect(page.getByText(/팀원 보고와 이 관리자 직접 검사 결과는 별도/)).toBeVisible();
 }finally{await context.close();}
});
