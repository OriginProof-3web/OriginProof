import React from 'react';
import {render,screen,fireEvent,waitFor,cleanup} from '@testing-library/react';
import {afterEach,beforeEach,expect,test,vi} from 'vitest';
import BusinessWorkspace from '../official/components/business/BusinessWorkspace';
import UserWorkspace from '../official/components/user/UserWorkspace';
import {issueErrors,validationErrors,proofLink} from '../official/w3-input.js';
import {api} from '../official/api-client.js';
vi.mock('../official/api-client.js',async()=>({...await vi.importActual('../official/api-client.js'),api:vi.fn(),requestId:()=> 'req_component_001',seconds:(s:string)=>new Date(s).toISOString().replace(/\.\d{3}Z$/,'Z')}));
const bank='iss_origin_mock_bank';
const view={proof_id:'prf_example',issuer_id:bank,proof_type:'PAYMENT_REQUEST',issued_at:'2026-10-02T00:00:00Z',expires_at:'2026-12-01T00:00:00Z'};
const result={verification_status:'VERIFIED',lifecycle_status:null,scope:'PROOF_ONLY',checks:{signature:'PASS',proof_status:'NOT_RUN'},reason_codes:[]};
const mock=vi.mocked(api);
function defaults(path:string){
 if(path==='/v1/auth/me')return {role:'issuer',issuer_id:bank};
 if(path==='/v1/issuer/status')return {status:'ACTIVE',chain_id:31337};
 if(path==='/v1/issuer/keys')return [{key_id:'key_example',status:'ACTIVE',selected:true,valid_from:1,valid_until:1900000000}];
 if(path==='/v2/issuer/recipients')return [{recipient_id:'acct_example',label:'합성 수신자'}];
 if(path==='/v1/issuer-applications/mine')return null;
 if(path.endsWith('/content'))return {envelope:{proof_type:'PAYMENT_REQUEST',payload:{amount_minor:85000,currency:'KRW'}},target_ref:'SYNTHETIC-PAYMENT-001'};
 if(path.endsWith('/verify'))return result;
 if(path==='/v2/proofs/prf_example')return view;
 return [];
}
beforeEach(()=>{mock.mockReset();mock.mockImplementation(async(path)=>defaults(path));});
afterEach(()=>{cleanup();vi.unstubAllGlobals();});
async function issueScreen(){render(<BusinessWorkspace/>);await waitFor(()=>expect(mock).toHaveBeenCalledWith('/v2/issuer/recipients'));fireEvent(window,new CustomEvent('originproof-action',{detail:{key:'issue'}}));await screen.findByRole('button',{name:'합성 예시 채우기'});}
test('required fields, positive integer, currency and future expiry are explained',()=>{
 expect(issueErrors({amount_minor:'0',currency:'krw',target_ref:''},'','2000-01-01')).toEqual(expect.objectContaining({amount_minor:expect.any(String),currency:expect.any(String),target_ref:expect.any(String),recipient_id:expect.any(String),expires_at:expect.any(String)}));
 for(const amount of ['1.5','-1','NaN','9007199254740992'])expect(issueErrors({amount_minor:amount},'acct','2030-01-01').amount_minor).toBeTruthy();
 expect(issueErrors({version:'1',document_number:'DOC'},'acct','2030-01-01')).toEqual({});
});
test('FastAPI validation loc maps to a field, not an object string',()=>expect(validationErrors([{loc:['body','content','PAYMENT_REQUEST','amount_minor'],msg:'양의 정수'}])).toEqual({amount_minor:'양의 정수'}));
test('public verification link contains only Proof ID',()=>{const url=new URL(proofLink('prf_example','http://localhost:3000/business.html?token=secret'));expect([...url.searchParams.keys()]).toEqual(['proof_id']);expect(url.pathname).toBe('/index.html');expect(url.hash).toBe('#user');});
test('empty issue form shows field errors without sending a mutation',async()=>{
 await issueScreen();fireEvent.click(screen.getByRole('button',{name:'Proof 발행'}));
 expect(await screen.findByText('지정 수신자를 선택해 주세요.')).toBeVisible();
 expect(mock.mock.calls.filter(([,body])=>body)).toHaveLength(0);
});
test('duplicate click sends once; a retry keeps request ID and successful ID',async()=>{
 let release:(v:unknown)=>void=()=>{};let posts=0;const requestIds:string[]=[];
 mock.mockImplementation(async(path,body)=>{if(path==='/v2/issuer/proofs'&&body){posts++;requestIds.push(body.request_id);if(posts===1)return new Promise(resolve=>{release=resolve});return view;}return defaults(path);});
 await issueScreen();fireEvent.click(screen.getByRole('button',{name:'합성 예시 채우기'}));
 const button=screen.getByRole('button',{name:'Proof 발행'});fireEvent.click(button);fireEvent.click(button);
 await waitFor(()=>expect(posts).toBe(1));release(view);
 expect(await screen.findByText(/prf_example · 발행 저장 완료/)).toBeVisible();
 // Re-enter exactly the same body; server request id must match.
 fireEvent.click(screen.getByRole('button',{name:'합성 예시 채우기'}));fireEvent.click(button);
 await waitFor(()=>expect(posts).toBe(2));expect(requestIds[0]).toBe(requestIds[1]);
});
test('422 server error is shown beside amount field',async()=>{
 mock.mockImplementation(async(path,body)=>{if(path==='/v2/issuer/proofs'&&body)throw Object.assign(new Error('422 · 입력값을 확인해 주세요.'),{fieldErrors:{amount_minor:'금액 범위 오류'}});return defaults(path);});
 await issueScreen();fireEvent.click(screen.getByRole('button',{name:'합성 예시 채우기'}));fireEvent.click(screen.getByRole('button',{name:'Proof 발행'}));
 expect(await screen.findByText('금액 범위 오류')).toBeVisible();expect(screen.getByLabelText('금액 (최소 화폐 단위)')).toHaveAttribute('aria-invalid','true');
});
test('public lookup reports scope and NOT_RUN without claiming current use',async()=>{
 render(<UserWorkspace/>);fireEvent.change(screen.getByLabelText('Proof ID / 검증 링크'),{target:{value:'prf_example'}});fireEvent.click(screen.getByRole('button',{name:'조회'}));
 expect(await screen.findByText('PROOF_ONLY')).toBeVisible();expect(screen.getByText('미확인')).toBeVisible();expect(screen.getByText('NOT_RUN')).toBeInTheDocument();expect(screen.getByText('ID 조회로 받은 자료의 내용 일치를 확인할 수는 없습니다.')).toBeVisible();
 expect(mock.mock.calls.find(([p,b])=>p.endsWith('/verify')&&b)?.[1]).not.toHaveProperty('candidate');
});

test('issuer session expiry removes protected keys and provides login recovery',async()=>{
 render(<BusinessWorkspace/>);await screen.findByRole('button',{name:'기관 정보 다시 조회'});
 await waitFor(()=>expect(mock).toHaveBeenCalledWith('/v1/issuer/keys'));
 mock.mockImplementation(async()=>{throw Object.assign(new Error('401'),{status:401});});
 fireEvent.click(screen.getByRole('button',{name:'기관 정보 다시 조회'}));
 expect(await screen.findByRole('link',{name:'다시 로그인'})).toHaveAttribute('href','business-login.html');
 expect(screen.queryByText('key_example')).not.toBeInTheDocument();
});
test('expired restricted content clears prior candidate values and offers login',async()=>{
 render(<UserWorkspace/>);fireEvent.change(screen.getByLabelText('Proof ID / 검증 링크'),{target:{value:'prf_example'}});fireEvent.click(screen.getByRole('button',{name:'조회'}));
 await screen.findByText('PROOF_ONLY');
 mock.mockImplementation(async(path)=>{if(path.endsWith('/content'))throw Object.assign(new Error('401'),{status:401});return defaults(path);});
 fireEvent.click(screen.getByRole('button',{name:'조회'}));
 expect(await screen.findByRole('link',{name:'다시 로그인'})).toBeVisible();expect(screen.queryByText('PROOF_ONLY')).not.toBeInTheDocument();
});
test('pending application is not displayed as approved when the chain already has a seeded issuer',async()=>{
 mock.mockImplementation(async(path)=>path==='/v1/issuer-applications/mine'?{application_id:'app_test',issuer_id:bank,status:'PENDING_REVIEW'}:defaults(path));
 render(<BusinessWorkspace/>);
 await waitFor(()=>expect(screen.getByRole('combobox',{name:'기관 상태'})).toHaveValue('PENDING_REVIEW'));
 expect(screen.getByText('검토 대기',{exact:true})).toBeVisible();
 expect(screen.queryByText('승인',{exact:true})).not.toBeInTheDocument();
});
test('fresh application confirmation uses application ID rather than undefined',async()=>{
 mock.mockImplementation(async(path,body)=>path==='/v1/issuer-applications'&&body?{application_id:'app_test',status:'PENDING_REVIEW'}:defaults(path));
 render(<BusinessWorkspace lifecycleEnabled/>);
 fireEvent.click(await screen.findByRole('button',{name:'기관 신청 접수'}));
 expect(await screen.findByText('app_test · PENDING_REVIEW')).toBeVisible();
});
