import {afterEach,expect,test,vi} from 'vitest';
import {verifyRead} from '../official/api-client.js';
afterEach(()=>vi.unstubAllGlobals());
function responses(values:unknown[]){const fetch=vi.fn();for(const value of values)fetch.mockResolvedValueOnce({ok:true,json:async()=>value});vi.stubGlobal('fetch',fetch);return fetch;}
test('admin verification retries only an unavailable moving snapshot',async()=>{
 const unavailable={verification_status:'INCONCLUSIVE',reason_codes:['DEPENDENCY_UNAVAILABLE'],lifecycle_status:null};
 const verified={verification_status:'VERIFIED',reason_codes:[],lifecycle_status:'ACTIVE'};
 const fetch=responses([unavailable,verified]);const body={request_id:'req_test'};
 expect(await verifyRead('/v2/proofs/prf_test/verify',body,'/test-api/recipient')).toEqual(verified);
 expect(fetch).toHaveBeenCalledTimes(2);expect(fetch.mock.calls.every(([url,args])=>url.endsWith('/verify')&&args.body===JSON.stringify(body))).toBe(true);
});
test('persistent snapshot failure remains inconclusive after four reads',async()=>{
 const value={verification_status:'INCONCLUSIVE',reason_codes:['DEPENDENCY_UNAVAILABLE'],lifecycle_status:null};const fetch=responses([value,value,value,value]);
 expect(await verifyRead('/v2/proofs/prf_test/verify',{request_id:'req_test'},'/test-api/recipient')).toEqual(value);expect(fetch).toHaveBeenCalledTimes(4);
});
test('tampered comparison is never retried into success',async()=>{
 const value={verification_status:'TAMPERED',reason_codes:['AMOUNT_MISMATCH']};const fetch=responses([value]);
 expect(await verifyRead('/v2/proofs/prf_test/verify',{request_id:'req_test'},'/test-api/recipient')).toEqual(value);expect(fetch).toHaveBeenCalledTimes(1);
});
test('HTTP failure is shown without automatic request repetition',async()=>{
 const fetch=vi.fn().mockResolvedValue({ok:false,status:503,json:async()=>({detail:'CHAIN_UNAVAILABLE'})});vi.stubGlobal('fetch',fetch);
 await expect(verifyRead('/v2/proofs/prf_test/verify',{request_id:'req_test'},'/test-api/recipient')).rejects.toThrow('503');expect(fetch).toHaveBeenCalledTimes(1);
});
