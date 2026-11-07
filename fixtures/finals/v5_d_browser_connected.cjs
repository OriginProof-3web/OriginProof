const fs = require('node:fs');
const { createRequire } = require('node:module');
const path = require('node:path');
const { chromium } = createRequire(path.resolve('apps/web/package.json'))('@playwright/test');
(async()=>{
 const cfg=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
 const password=JSON.parse(fs.readFileSync(cfg.credentials,'utf8')).password;
 const browser=await chromium.launch({headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  const statuses=[],errors=[];
  page.on('pageerror',e=>errors.push(e.name));
  page.on('response',r=>{const p=new URL(r.url()).pathname;if(p.startsWith('/api/'))statuses.push({path:p,status:r.status()});});
  await page.goto(cfg.web+'/login.html?next=business.html');
  await page.locator('#username').fill('d_recipient');
  await page.locator('#password').fill(password);
  await page.locator('#submit').click();
  await page.waitForURL('**/business.html');
  await page.goto(cfg.web+'/business.html?mode=api');
  await page.waitForFunction(()=>window.Hk?.auth?.state?.checked===true);
  await page.locator('#chatInput').fill('합성 안내: 인증번호를 알려주세요.');
  const jobResponse=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/v3/analyses'&&r.request().method()==='POST');
  await page.locator('#chatInput').press('Enter');
  const job=(await (await jobResponse).json()).analysis_id;
  await page.waitForFunction(()=>document.querySelectorAll('#chatThread .msg-ai .op-report').length>0,{},{timeout:45000});
  const state=await page.evaluate(async id=>{const r=await fetch('/api/v3/analyses/'+id);return r.json();},job);
  if(state.status!=='COMPLETED'||state.report?.risk_level!=='HIGH')throw new Error('server analysis did not complete HIGH');
  const body=await page.locator('#chatThread').innerText();
  if(!body.includes('블록체인 결정')||!body.includes('AI 위험 설명'))throw new Error('four-axis report absent');
  if(cfg.live&&state.report.limitations.some(x=>x.startsWith('LLM_ANALYSIS_UNAVAILABLE:')))throw new Error('live provider fell back');
  await page.screenshot({path:cfg.screenshot,fullPage:true});
  fs.writeFileSync(cfg.result,JSON.stringify({mode:cfg.live?'ACTUAL_OPENAI':'RULE_FALLBACK_MOCK',status:state.status,risk:state.report.risk_level,evidence:state.report.evidence.map(x=>({source:x.source,start:x.start_offset,end:x.end_offset})),limitations:state.report.limitations,request_statuses:statuses,page_errors:errors,actual_api_proxy:true,synthetic_data:true},null,2));
  console.log(JSON.stringify({mode:cfg.live?'ACTUAL_OPENAI':'MOCK',status:state.status,risk:state.report.risk_level,page_errors:errors.length}));
 } finally {await browser.close();}
})().catch(e=>{console.error(e.name+': '+e.message);process.exitCode=1;});
