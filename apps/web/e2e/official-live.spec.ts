import {test,expect,type Page} from '@playwright/test';
import {readFileSync,mkdtempSync,writeFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {execFileSync} from 'node:child_process';
const credentials=process.env.ORIGINPROOF_TEST_ACCOUNTS;
test.use({trace:'off',video:'off',screenshot:'off'});
// Real suites share the unchanged API login/request rate limits.
test.setTimeout(120000);
test.beforeEach(async()=>{await new Promise(resolve=>setTimeout(resolve,61000));});
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
 test(`actual ${type}: issue, public QR, compare, tamper and lifecycle`,async({browser})=>{
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
  await page.getByRole('button',{name:'검증 QR 보기'}).click();
  const qr=page.getByRole('img',{name:'공개 Proof 조회 화면으로 이동하는 QR 코드'});await expect(qr).toBeVisible();
  if(process.env.ORIGINPROOF_QR_DECODER){
   const directory=mkdtempSync(join(tmpdir(),'originproof-live-qr-'));
   try{const path=join(directory,'qr.png');const source=await qr.getAttribute('src');writeFileSync(path,Buffer.from(source!.split(',')[1],'base64'));expect(execFileSync(process.env.ORIGINPROOF_QR_DECODER,[path],{encoding:'utf8'}).trim()).toBe(href);}finally{rmSync(directory,{recursive:true});}
  }
  const anonymous=await browser.newContext({reducedMotion:"reduce"});const publicPage=await anonymous.newPage();await publicPage.goto(href!);
  await expect(publicPage.getByText('PROOF_ONLY',{exact:true})).toBeVisible();await expect(publicPage.getByText('ACTIVE',{exact:true})).toBeVisible();
  await login(publicPage,'recipient');await publicPage.getByLabel('Proof ID / 검증 링크').fill(id);await publicPage.getByRole('button',{name:'조회',exact:true}).click();
  await expect(publicPage.getByText('PROOF_ONLY',{exact:true})).toBeVisible();await publicPage.getByRole('button',{name:'내용 비교',exact:true}).last().click();
  await publicPage.getByRole('button',{name:'발행 값 채우기'}).click();await publicPage.getByRole('button',{name:'내용 비교',exact:true}).last().click();
  await expect(publicPage.locator('.uw-comparison')).toContainText('VERIFIED · FULL_COMPARISON');
  await publicPage.getByLabel(type==='PAYMENT_REQUEST'?'금액 (최소 화폐 단위)':'문서번호',{exact:true}).fill(type==='PAYMENT_REQUEST'?'85001':'MOCK-TAMPERED');
  await publicPage.getByRole('button',{name:'내용 비교',exact:true}).last().click();await expect(publicPage.locator('.uw-comparison')).toContainText(mismatch);await expect(publicPage.locator('.uw-comparison')).toContainText('TAMPERED');
  const other=await browser.newContext({reducedMotion:"reduce"});const otherPage=await other.newPage();await login(otherPage,issuer==='bank'?'office':'bank');
  const list=await other.request.get('/api/v2/issuer/proofs');expect(list.ok()).toBeTruthy();expect((await list.json() as {proof_id:string}[]).some(row=>row.proof_id===id)).toBe(false);
  const denied=await other.request.get(`/api/v2/proofs/${id}/content`);expect(denied.status()).toBe(404);
  if(type==='PAYMENT_REQUEST'){
   await publicPage.getByLabel('금액 (최소 화폐 단위)',{exact:true}).fill('85000');
   await publicPage.getByRole('button',{name:'내용 비교',exact:true}).last().click();
   await publicPage.getByRole('tab',{name:/요청 사용$/}).click();
   await publicPage.getByRole('checkbox').check();
   await publicPage.getByRole('button',{name:'1회 사용 요청 실행'}).click();
   await expect(publicPage.getByText('CONSUMED',{exact:true})).toBeVisible();
   await expect(publicPage.getByRole('button',{name:'1회 사용 요청 실행'})).toBeDisabled();
   await publicPage.reload();await publicPage.getByLabel('Proof ID / 검증 링크').fill(id);await publicPage.getByRole('button',{name:'조회',exact:true}).click();
   await expect(publicPage.getByText('CONSUMED',{exact:true})).toBeVisible();
  }else{
   await page.getByLabel('작업 사유',{exact:true}).fill('Synthetic official browser revocation');
   await page.getByRole('checkbox').check();
   await page.getByRole('button',{name:'확인한 관리 작업 실행'}).click();
   await expect(page.locator('.uw-summary')).toContainText('PROOF_REVOKED');
   await publicPage.reload();await publicPage.getByLabel('Proof ID / 검증 링크').fill(id);await publicPage.getByRole('button',{name:'조회',exact:true}).click();
   await expect(publicPage.locator('.uw-status b').filter({hasText:/^PROOF_REVOKED$/})).toBeVisible();
  }
  await other.close();await anonymous.close();await context.close();
 });
}


test('actual business key rotation preserves previous key and records confirmed operation',async({browser})=>{
 const context=await browser.newContext({reducedMotion:'reduce'});
 try{
  const page=await context.newPage();await login(page,'bank');
  const before=await (await context.request.get('/api/v1/issuer/keys')).json() as {key_id:string;selected:boolean;status:string}[];
  const old=before.find(key=>key.selected)!;expect(old).toBeTruthy();
  await page.getByRole('button',{name:'공개키 관리',exact:true}).first().click();
  await page.getByRole('combobox',{name:'작업',exact:true}).selectOption('rotate');
  await page.getByLabel('작업 사유',{exact:true}).fill('Synthetic official browser normal key rotation');
  await page.getByRole('checkbox').check();await page.getByRole('button',{name:'키 작업 실행',exact:true}).click();
  await expect(page.locator('.uw-shell [role=status]')).toContainText('CONFIRMED');
  const after=await (await context.request.get('/api/v1/issuer/keys')).json() as {key_id:string;selected:boolean;status:string}[];
  expect(after.find(key=>key.selected)?.key_id).not.toBe(old.key_id);
  expect(after.find(key=>key.key_id===old.key_id)?.status).toBe('ACTIVE');
  await page.getByRole('button',{name:'작업 이력',exact:true}).first().click();
  await expect(page.locator('.uw-history').first()).toContainText('rotate_key');
 }finally{await context.close();}
});
