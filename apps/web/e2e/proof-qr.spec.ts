import {test,expect} from '@playwright/test';
import {mkdtempSync,writeFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {execFileSync} from 'node:child_process';
const id='prf_qr_example';
test('issued Proof QR generates a public-only PNG and opens anonymous lookup',async({page,browser})=>{
 const proof={proof_id:id,issuer_id:'iss_origin_mock_bank',proof_type:'PAYMENT_REQUEST',issued_at:'2026-10-02T00:00:00Z',expires_at:'2030-01-01T00:00:00Z'};
 await page.route('**/api/**',async route=>{
  const path=new URL(route.request().url()).pathname.replace('/api','');let body:unknown=[];
  if(path==='/v1/auth/me')body={role:'issuer',issuer_id:'iss_origin_mock_bank'};
  if(path==='/v1/issuer/status')body={status:'ACTIVE',chain_id:31337};
  if(path==='/v1/issuer-applications/mine')body=null;
  if(path==='/v2/issuer/proofs')body=[proof];
  if(path===`/v2/proofs/${id}`)body=proof;
  if(path.endsWith('/content'))body={envelope:{proof_type:'PAYMENT_REQUEST',payload:{amount_minor:85000,currency:'KRW'}},target_ref:'SYNTHETIC-QR'};
  await route.fulfill({json:body});
 });
 await page.goto('/business.html');await page.getByRole('button',{name:'발행 목록',exact:true}).last().click();
 await page.getByRole('button').filter({hasText:id}).click();
 const link=await page.getByRole('link',{name:'사용자 조회 화면'}).getAttribute('href');
 await page.getByRole('button',{name:'검증 QR 보기'}).click();
 const image=page.getByRole('img',{name:'공개 Proof 조회 화면으로 이동하는 QR 코드'});
 await expect(image).toBeVisible();const source=await image.getAttribute('src');expect(source).toMatch(/^data:image\/png;base64,/);
 expect(await image.evaluate(node=>(node as HTMLImageElement).naturalWidth)).toBe(256);
 const downloadPromise=page.waitForEvent('download');await page.getByRole('link',{name:'QR PNG 저장'}).click();
 const download=await downloadPromise;expect(download.suggestedFilename()).toBe(`proof-${id}.png`);
 if(process.env.ORIGINPROOF_QR_DECODER){
  const directory=mkdtempSync(join(tmpdir(),'originproof-qr-'));
  try{const path=join(directory,'qr.png');writeFileSync(path,Buffer.from(source!.split(',')[1],'base64'));expect(execFileSync(process.env.ORIGINPROOF_QR_DECODER,[path],{encoding:'utf8'}).trim()).toBe(link);}finally{rmSync(directory,{recursive:true});}
 }
 const url=new URL(link!);expect([...url.searchParams.keys()]).toEqual(['proof_id']);expect(url.searchParams.get('proof_id')).toBe(id);
 const anonymous=await browser.newContext({reducedMotion:'reduce'});
 try{
  await anonymous.route('**/api/**',async route=>{
   const path=new URL(route.request().url()).pathname;
   if(path.endsWith('/auth/me')){await route.fulfill({status:401,json:{detail:'AUTH_REQUIRED'}});return;}
   await route.fulfill({json:path.endsWith('/verify')?{verification_status:'VERIFIED',lifecycle_status:null,scope:'PROOF_ONLY',checks:{signature:'PASS',proof_status:'NOT_RUN'},reason_codes:[]}:proof});
  });
  const publicPage=await anonymous.newPage();await publicPage.goto(link!);
  await expect(publicPage.getByText('PROOF_ONLY',{exact:true})).toBeVisible();
  await publicPage.getByText('검사 근거',{exact:true}).click();
  await expect(publicPage.getByText('NOT_RUN',{exact:true})).toBeVisible();
 }finally{await anonymous.close();}
});
