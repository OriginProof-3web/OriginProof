import {test,expect, type Page, type Locator} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import {readFileSync} from 'node:fs';
test.use({trace:'off',video:'off',screenshot:'off'});
test.setTimeout(240000);
test.skip(!process.env.W5_ADMIN_ENV,'Requires run-w5-admin.py owned fresh PostgreSQL/Anvil fixture.');
async function enter(locator:Locator){await locator.focus();await locator.press('Enter');}
async function type(locator:Locator,value:string){await locator.focus();await locator.press('ControlOrMeta+A');await locator.pressSequentially(value);}
async function select(locator:Locator,index:number){
 const target=await locator.locator('option').nth(index).getAttribute('value');await locator.focus();
 // Chromium on macOS uses native select type-ahead; arrows open its popup.
 for(let i=0;await locator.inputValue()!==target&&i<3;i++)await locator.press('o');
 await expect(locator).toHaveValue(target!);await locator.press('Tab');
}
async function axe(page:Page){const result=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();expect(result.violations.map(v=>({id:v.id,targets:v.nodes.map(n=>n.target)}))).toEqual([]);}
test('fresh accounts only: keyboard application, approval, activation, keys, two types, compare and revoke',async({page,playwright})=>{
 const env=JSON.parse(readFileSync(process.env.W5_ADMIN_ENV!,'utf8'));
 const accounts=JSON.parse(readFileSync(env.accounts,'utf8'));
 const clients=new Map();let readFault=0;let faultResponses=0;
 try{
  for(const a of accounts){const client=await playwright.request.newContext({baseURL:env.api,extraHTTPHeaders:{Origin:'http://127.0.0.1:8768'}});expect((await client.post('/v1/auth/login',{data:{username:a.username,password:a.password}})).ok()).toBeTruthy();clients.set(a.username,client);}
  // Every response comes from the actual isolated API; no fabricated success.
  await page.route(/\/(?:api|test-api)\//,async route=>{
   const url=new URL(route.request().url());const match=url.pathname.match(/^\/(?:api|test-api(?:\/([^/]+))?)(\/.*)$/)!;
   if(match[1]==='recipient'&&url.pathname.endsWith('/verify')&&readFault){faultResponses++;await route.fulfill({status:readFault,contentType:'application/json',body:JSON.stringify({detail:'INJECTED_W5_BROWSER_FAILURE'})});return;}
   const client=clients.get(match[1]??'operator');const request=route.request();
   const headers:Record<string,string>={Origin:'http://127.0.0.1:8768'};
   if(request.headers()['x-csrf-token'])headers['X-CSRF-Token']=request.headers()['x-csrf-token'];
   if(request.headers()['content-type'])headers['Content-Type']=request.headers()['content-type'];
   const response=await client.fetch(match[2]+url.search,{method:request.method(),data:request.postDataBuffer()??undefined,headers});
   await route.fulfill({status:response.status(),body:await response.body(),headers:{'Content-Type':response.headers()['content-type']??'application/json'}});
  });
  await page.goto('/admin.html');await expect(page.getByRole('heading',{name:'기관 상태',exact:true})).toBeVisible();
  const nav=page.getByRole('navigation',{name:'관리자 테스트 메뉴'});
  const actions=page.getByRole('navigation',{name:'기능 메뉴'});
  const status=page.locator('.uw-shell .uw-notice[role=status]');
  for(const org of ['bank','office']){
   await enter(nav.getByRole('button',{name:'기업 기능',exact:true}));await select(page.getByLabel('테스트 기관',{exact:true}),org==='bank'?0:1);
   await expect(page.getByRole('button',{name:'기관 신청 접수'})).toBeVisible();await axe(page);
   await enter(page.getByRole('button',{name:'기관 신청 접수'}));await expect(page.getByRole('combobox',{name:'신청 상태',exact:true})).toHaveValue('PENDING_REVIEW');
   await enter(nav.getByRole('button',{name:'기관 승인',exact:true}));
   let card=page.locator('#operator-controls .test-card').filter({has:page.getByRole('heading',{name:org==='bank'?'Origin Mock Bank':'Origin Mock Office',exact:true})});
   await expect(card.getByRole('button',{name:'승인',exact:true})).toBeVisible();await type(card.getByRole('textbox'),'Synthetic W5 keyboard approval');await enter(card.getByRole('button',{name:'승인',exact:true}));
   await expect(card).toContainText('APPROVED_PENDING_CHAIN');await type(card.getByRole('textbox'),'Synthetic W5 activation');await enter(card.getByRole('button',{name:'체인 활성화',exact:true}));await expect(card).toContainText('ACTIVE');await axe(page);
   await enter(nav.getByRole('button',{name:'기업 기능',exact:true}));await expect(page.getByRole('combobox',{name:'신청 상태',exact:true})).toHaveValue('ACTIVE');
   await enter(actions.getByRole('button',{name:'공개키 관리',exact:true}));await type(page.getByLabel('작업 사유',{exact:true}),'Synthetic W5 initial key');await enter(page.getByRole('button',{name:'키 작업 실행',exact:true}));await expect(status).toContainText('CONFIRMED');
   await enter(actions.getByRole('button',{name:'Proof 발행',exact:true}));await enter(page.getByRole('button',{name:'합성 예시 채우기'}));await axe(page);await enter(page.getByRole('button',{name:'Proof 발행',exact:true}).last());await expect(status).toContainText('prf_');const id=(await status.innerText()).match(/prf_[A-Za-z0-9_-]+/)![0];
   await enter(nav.getByRole('button',{name:'개인 기능',exact:true}));await type(page.getByLabel('Proof ID / 검증 링크'),id);await enter(page.getByRole('button',{name:'조회',exact:true}));await expect(page.getByText('PROOF_ONLY',{exact:true})).toBeVisible();await axe(page);
   if(org==='bank'){
    readFault=503;await enter(page.getByRole('button',{name:'조회',exact:true}));await expect(page.getByRole('alert')).toContainText('상태 코드: 503');expect(faultResponses).toBe(1);await expect(page.getByText('PROOF_ONLY',{exact:true})).toHaveCount(0);readFault=0;await enter(page.getByRole('button',{name:'현재 상태 다시 조회'}));await expect(page.getByText('PROOF_ONLY',{exact:true})).toBeVisible();
   }
   await enter(actions.getByRole('button',{name:'내용 비교',exact:true}));await enter(page.getByRole('button',{name:'발행 값 채우기'}));await enter(page.getByRole('button',{name:'내용 비교',exact:true}).last());await expect(page.locator('.uw-comparison')).toContainText('VERIFIED · FULL_COMPARISON');await axe(page);
   await type(page.getByLabel(org==='bank'?'금액 (최소 화폐 단위)':'문서번호',{exact:true}),org==='bank'?'85001':'MODIFIED');await enter(page.getByRole('button',{name:'내용 비교',exact:true}).last());await expect(page.locator('.uw-comparison')).toContainText(org==='bank'?'AMOUNT_MISMATCH':'FIELD_MISMATCH');
   if(org==='bank'){
    await enter(nav.getByRole('button',{name:'기업 기능',exact:true}));await enter(actions.getByRole('button',{name:'공개키 관리',exact:true}));
    // Native Korean option selection is set through Playwright; activation,
    // consent and mutations use keyboard. D's manual native-select QA remains separate.
    await page.getByRole('combobox',{name:'작업',exact:true}).selectOption('rotate');await type(page.getByLabel('작업 사유',{exact:true}),'Synthetic W5 normal rotation');await page.getByRole('checkbox').focus();await page.keyboard.press('Space');await enter(page.getByRole('button',{name:'키 작업 실행',exact:true}));await expect(status).toContainText('CONFIRMED');
    await enter(nav.getByRole('button',{name:'개인 기능',exact:true}));await type(page.getByLabel('Proof ID / 검증 링크'),id);await enter(page.getByRole('button',{name:'조회',exact:true}));await expect(page.getByText('VERIFIED',{exact:true}).first()).toBeVisible();await expect(page.getByText('ACTIVE',{exact:true}).first()).toBeVisible();
    await enter(nav.getByRole('button',{name:'기업 기능',exact:true}));await enter(actions.getByRole('button',{name:'Proof 발행',exact:true}));await enter(page.getByRole('button',{name:'합성 예시 채우기'}));await enter(page.getByRole('button',{name:'Proof 발행',exact:true}).last());await expect(status).toContainText('prf_');const singleUse=(await status.innerText()).match(/prf_[A-Za-z0-9_-]+/)![0];
    await enter(nav.getByRole('button',{name:'개인 기능',exact:true}));await type(page.getByLabel('Proof ID / 검증 링크'),singleUse);await enter(page.getByRole('button',{name:'조회',exact:true}));await expect(page.getByText('PROOF_ONLY',{exact:true})).toBeVisible();await enter(actions.getByRole('button',{name:'요청 사용',exact:true}));await page.getByRole('checkbox').focus();await page.keyboard.press('Space');await enter(page.getByRole('button',{name:'1회 사용 요청 실행'}));await expect(page.getByText('CONSUMED',{exact:true})).toBeVisible();await expect(page.getByRole('button',{name:'1회 사용 요청 실행'})).toBeDisabled();
   }
   await enter(nav.getByRole('button',{name:'기업 기능',exact:true}));await enter(actions.getByRole('button',{name:'발행 목록',exact:true}));await enter(page.getByRole('button',{name:new RegExp(id)}));
   await type(page.getByLabel('작업 사유',{exact:true}),'Synthetic W5 proof revocation');await page.getByRole('checkbox').focus();await page.keyboard.press('Space');await enter(page.getByRole('button',{name:'확인한 관리 작업 실행',exact:true}));await expect(status).toContainText('CONFIRMED');
   await enter(nav.getByRole('button',{name:'개인 기능',exact:true}));await type(page.getByLabel('Proof ID / 검증 링크'),id);await enter(page.getByRole('button',{name:'조회',exact:true}));await expect(page.getByText('PROOF_REVOKED',{exact:true}).first()).toBeVisible();
  }
  await enter(page.getByRole('button',{name:'사이드바 접기',exact:true}));await expect.poll(async()=>(await page.locator('#sidebar-root').boundingBox())!.width).toBeLessThan(100);readFault=401;await enter(page.getByRole('button',{name:'조회',exact:true}));await expect(page.getByRole('link',{name:'다시 로그인'})).toBeVisible();await expect(page.getByText('PROOF_ONLY',{exact:true})).toHaveCount(0);await page.setViewportSize({width:390,height:844});expect(await page.locator('body').evaluate(b=>b.scrollWidth)).toBeLessThanOrEqual(390);await axe(page);
 }finally{for(const client of clients.values())await client.dispose();}
});
