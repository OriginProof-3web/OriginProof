import {test,expect} from '@playwright/test';

test('official landing and direct navigation preserve supplied design',async({page})=>{
 await page.goto('/');await expect(page).toHaveURL(/index\.html$/);
 await expect(page.locator('#landing')).toBeVisible();
 await page.locator('#quick-nav summary').click();
 await page.getByRole('link',{name:'개인 로그인'}).click();await expect(page).toHaveURL(/user-login\.html$/);
 await expect(page.getByRole('heading',{name:'Individual Sign In'})).toBeVisible();
});
test('mobile quick navigation opens by keyboard and Escape restores focus',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.goto('/index.html');
 const menu=page.locator('#quick-nav');
 const toggle=menu.locator('summary');
 await toggle.focus();await toggle.press('Enter');
 await expect(menu).toHaveAttribute('open','');
 const link=menu.getByRole('link',{name:'개인 로그인'});
 await expect(link).toBeVisible();
 const box=await link.boundingBox();
 expect(box!.x).toBeGreaterThanOrEqual(0);expect(box!.x+box!.width).toBeLessThanOrEqual(390);
 await link.focus();await link.press('Escape');
 await expect(menu).not.toHaveAttribute('open','');await expect(toggle).toBeFocused();
 await toggle.press('Enter');await link.click();
 await expect(page).toHaveURL(/user-login\.html$/);
});
test('anonymous Proof lookup is separated from restricted comparison',async({page})=>{
 const proof={proof_id:'prf_browser',issuer_id:'iss_origin_mock_bank',proof_type:'PAYMENT_REQUEST',issued_at:'2026-10-02T00:00:00Z',expires_at:'2026-12-01T00:00:00Z'};
 await page.route('**/api/v2/proofs/prf_browser',route=>route.fulfill({json:proof}));
 await page.route('**/api/v2/proofs/prf_browser/content',route=>route.fulfill({status:404,json:{detail:'CONTENT_NOT_FOUND'}}));
 await page.route('**/api/v2/proofs/prf_browser/verify',async route=>{
  expect(route.request().postDataJSON()).not.toHaveProperty('candidate');
  await route.fulfill({json:{verification_status:'VERIFIED',scope:'PROOF_ONLY',lifecycle_status:null,checks:{signature:'PASS',proof_status:'NOT_RUN'},reason_codes:[]}});
 });
 await page.goto('/index.html?proof_id=prf_browser#user');
 await expect(page.getByText('PROOF_ONLY',{exact:true})).toBeVisible();
 await expect(page.getByText('ID 조회로 받은 자료의 내용 일치를 확인할 수는 없습니다.')).toBeVisible();
 await page.getByText('검사 근거',{exact:true}).click();await expect(page.getByText('NOT_RUN',{exact:true})).toBeVisible();
 const main=await page.locator('.main').boundingBox();const dock=await page.locator('#user-dock').boundingBox();
 expect(Math.abs((dock!.x+dock!.width/2)-(main!.x+main!.width/2))).toBeLessThan(2);
});
test('sidebar collapse keeps dock centered and mobile viewport scrollable',async({page})=>{
 await page.goto('/index.html#user');
 await page.getByRole('button',{name:'사이드바 접기',exact:true}).click();
 await expect.poll(async()=> (await page.locator('#sidebar-root').boundingBox())!.width).toBeLessThan(100);
 await expect(page.locator('#user-dock')).toBeVisible();
 await page.setViewportSize({width:390,height:844});
 await expect(page.getByLabel('Proof ID / 검증 링크')).toBeVisible();
 expect(await page.locator('body').evaluate(body=>body.scrollWidth)).toBeLessThanOrEqual(390);
});
