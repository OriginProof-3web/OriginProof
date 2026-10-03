import {cleanup,render,screen,waitFor} from '@testing-library/react';
import {afterEach,beforeEach,expect,test,vi} from 'vitest';
import ProofQr from '../official/components/business/ProofQr';
const {encode}=vi.hoisted(()=>({encode:vi.fn<(text:string,options?:object)=>Promise<string>>() }));
vi.mock('../official/node_modules/qrcode',()=>({default:{toDataURL:encode}}));
beforeEach(()=>{encode.mockReset();encode.mockResolvedValue('data:image/png;base64,example');});
afterEach(cleanup);
test('QR encodes only public ID link and offers PNG download',async()=>{
 render(<ProofQr proofId="prf_example"/>);
 expect(await screen.findByRole('img',{name:'공개 Proof 조회 화면으로 이동하는 QR 코드'})).toBeVisible();
 const url=new URL(encode.mock.calls[0][0] as string);
 expect([...url.searchParams.keys()]).toEqual(['proof_id']);expect(url.searchParams.get('proof_id')).toBe('prf_example');expect(url.hash).toBe('#user');
 expect(screen.getByRole('link',{name:'QR PNG 저장'})).toHaveAttribute('download','proof-prf_example.png');
 expect(encode.mock.calls[0][1]).toEqual(expect.objectContaining({margin:4,width:256}));
});
test('generation failure exposes error and no broken image',async()=>{
 encode.mockRejectedValue(new Error('encoder failure'));render(<ProofQr proofId="prf_example"/>);
 expect(await screen.findByRole('alert')).toHaveTextContent('QR 생성에 실패');expect(screen.queryByRole('img')).not.toBeInTheDocument();
});
test('late response for an old Proof cannot replace the current QR',async()=>{
 let finish:(value:string)=>void=()=>{};
 encode.mockImplementationOnce(()=>new Promise<string>(resolve=>{finish=resolve;}));
 const view=render(<ProofQr proofId="prf_old"/>);view.rerender(<ProofQr proofId="prf_new"/>);
 await screen.findByRole('img');finish('data:image/png;base64,old');
 await waitFor(()=>expect(screen.getByRole('img')).toHaveAttribute('src','data:image/png;base64,example'));
});
