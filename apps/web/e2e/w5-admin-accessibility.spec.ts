import {test,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import {readFileSync} from 'node:fs';
test.use({trace:'off',video:'off',screenshot:'off'});
test.skip(!process.env.ORIGINPROOF_TEST_ACCOUNTS||process.env.ORIGINPROOF_WEB_BASE_URL!=='http://127.0.0.1:8768','Requires the existing local administrator console.');
test('same administrator page: keyboard navigation, WCAG AA and narrow viewport',async({page})=>{
 const account=JSON.parse(readFileSync(process.env.ORIGINPROOF_TEST_ACCOUNTS!,'utf8')).find((a:{username:string})=>a.username==='operator');
 await page.goto('/user-login.html');await page.getByLabel('계정 이름').fill(account.username);await page.getByLabel('비밀번호',{exact:true}).fill(account.password);await page.getByLabel('비밀번호',{exact:true}).press('Enter');
 await expect(page).toHaveURL(/admin.html/);await expect(page.getByRole('heading',{name:'기관 상태',exact:true})).toBeVisible();
 for(const section of ['기업 기능','개인 기능','기관 승인']){
  const button=page.getByRole('navigation',{name:'관리자 테스트 메뉴'}).getByRole('button',{name:section,exact:true});await button.focus();await page.keyboard.press('Enter');await expect(button).toHaveAttribute('aria-pressed','true');
  await expect(page.locator('.uw-shell [role=status]').filter({hasText:'확인 중'})).toHaveCount(0);
  await page.waitForTimeout(800);
  const result=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
  expect(result.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))})),section).toEqual([]);
 }
 const resultsButton=page.getByRole('navigation',{name:'관리자 테스트 메뉴'}).getByRole('button',{name:'검사 결과',exact:true});await resultsButton.focus();await page.keyboard.press('Enter');
 await expect(page.getByRole('heading',{name:/W5 A 최종 자체 검사/})).toBeVisible();await expect(page.getByRole('heading',{name:/W5 API 후보 재검사.*17 통과\/1 실패/})).toBeVisible();await expect(page.getByRole('heading',{name:/W5 단계 완료 조건/})).toBeVisible();
 await page.getByRole('button',{name:'사이드바 접기',exact:true}).focus();await page.keyboard.press('Enter');await expect.poll(async()=>(await page.locator('#sidebar-root').boundingBox())!.width).toBeLessThan(100);await page.setViewportSize({width:390,height:844});expect(await page.locator('body').evaluate(b=>b.scrollWidth)).toBeLessThanOrEqual(390);
});
