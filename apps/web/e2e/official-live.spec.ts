import {test,expect,type Page} from '@playwright/test';
import {readFileSync} from 'node:fs';
const credentials=process.env.ORIGINPROOF_TEST_ACCOUNTS;
test.use({trace:'off',video:'off',screenshot:'off'});
test.skip(!credentials,'Explicit isolated local account file required; no credentials committed.');
async function login(page:Page,username:string){
 const rows=JSON.parse(readFileSync(credentials!,'utf8')) as {username:string,password:string}[];
 const account=rows.find(row=>row.username===username)!;
 await page.goto(username==='recipient'?'/user-login.html':'/business-login.html');
 await page.getByLabel('계정 이름').fill(account.username);await page.getByLabel('비밀번호',{exact:true}).fill(account.password);
 await page.getByRole('button',{name:'Sign In',exact:true}).click();
 await expect(page).toHaveURL(username==='recipient'?/index.html#user/:/business.html/);
}
for(const [issuer,type,mismatch] of [['bank','PAYMENT_REQUEST','AMOUNT_MISMATCH'],['office','OFFICIAL_DOCUMENT','FIELD_MISMATCH']] as const){
 test(`actual ${type}: issue, own list, anonymous lookup, recipient match and tamper`,async({browser})=>{
  const context=await browser.newContext({reducedMotion:"reduce"});const page=await context.newPage();
  await login(page,issuer);await page.getByRole('button',{name:'새 Proof 발행',exact:true}).click();
  await page.getByRole('button',{name:'합성 예시 채우기'}).click();
  await page.getByLabel('지정 수신자',{exact:true}).selectOption({label:'recipient'});
  await page.getByRole('button',{name:'Proof 발행',exact:true}).click();
  const response=page.getByRole('status');await expect(response).toContainText('prf_');
  const text=await response.innerText();const id=text.match(/prf_[A-Za-z0-9_-]+/)![0];
  await page.getByRole('button',{name:'발행 목록',exact:true}).last().click();
  await expect(page.getByRole('heading',{name:'Proof 상세'})).toBeVisible();
  const href=await page.getByRole('link',{name:'사용자 조회 화면'}).getAttribute('href');expect(new URL(href!,'http://127.0.0.1:3000').searchParams.get('proof_id')).toBe(id);
  const anonymous=await browser.newContext({reducedMotion:"reduce"});const publicPage=await anonymous.newPage();await publicPage.goto(href!);
  await expect(publicPage.getByText('PROOF_ONLY',{exact:true})).toBeVisible();await expect(publicPage.getByText('미확인',{exact:true})).toBeVisible();
  await login(publicPage,'recipient');await publicPage.getByLabel('Proof ID / 검증 링크').fill(id);await publicPage.getByRole('button',{name:'조회',exact:true}).click();
  await expect(publicPage.getByText('PROOF_ONLY',{exact:true})).toBeVisible();await publicPage.getByRole('button',{name:'내용 비교',exact:true}).last().click();
  await publicPage.getByRole('button',{name:'발행 값 채우기'}).click();await publicPage.getByRole('button',{name:'내용 비교',exact:true}).last().click();
  await expect(publicPage.locator('.uw-comparison')).toContainText('VERIFIED · FULL_COMPARISON');
  await publicPage.getByLabel(type==='PAYMENT_REQUEST'?'금액 (최소 화폐 단위)':'문서번호',{exact:true}).fill(type==='PAYMENT_REQUEST'?'85001':'MOCK-TAMPERED');
  await publicPage.getByRole('button',{name:'내용 비교',exact:true}).last().click();await expect(publicPage.locator('.uw-comparison')).toContainText(mismatch);await expect(publicPage.locator('.uw-comparison')).toContainText('TAMPERED');
  const other=await browser.newContext({reducedMotion:"reduce"});const otherPage=await other.newPage();await login(otherPage,issuer==='bank'?'office':'bank');
  const list=await other.request.get('/api/v2/issuer/proofs');expect(list.ok()).toBeTruthy();expect((await list.json() as {proof_id:string}[]).some(row=>row.proof_id===id)).toBe(false);
  const denied=await other.request.get(`/api/v2/proofs/${id}/content`);expect(denied.status()).toBe(404);
  await other.close();await anonymous.close();await context.close();
 });
}
