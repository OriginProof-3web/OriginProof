import {afterEach,expect,test,vi} from 'vitest';
import {api,errorInfo,verifyRead} from '../official/api-client.js';
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

test('rate limit displays a wait message without retrying a request',async()=>{
 const fetch=vi.fn().mockResolvedValue({ok:false,status:429,json:async()=>{throw new Error('local proxy HTML');}});vi.stubGlobal('fetch',fetch);
 await expect(verifyRead('/v2/proofs/prf_test/verify',{request_id:'req_test'},'/api')).rejects.toThrow('429 · 요청이 많습니다. 잠시 후 다시 시도해 주세요.');
 expect(fetch).toHaveBeenCalledTimes(1);
});

test('read-only verification failure never warns about a submitted mutation',async()=>{
 vi.stubGlobal('fetch',vi.fn().mockRejectedValue(new TypeError('offline')));
 const error=await api('/v2/proofs/prf_test/verify',{request_id:'req_test'},'/api').catch(error=>error);
 expect(error.uncertain).toBe(false);expect(errorInfo(error).retryRead).toBe(true);
});
test('failed mutation preserves uncertainty and is never automatically resent',async()=>{
 const fetch=vi.fn().mockResolvedValueOnce({ok:true,json:async()=>({csrf_token:'test'})}).mockRejectedValue(new TypeError('offline'));vi.stubGlobal('fetch',fetch);
 const error=await api('/v2/proofs/prf_test/consume',{request_id:'req_test'},'/api').catch(error=>error);
 expect(error.uncertain).toBe(true);expect(fetch).toHaveBeenCalledTimes(2);expect(errorInfo(error).message).toContain('처리됐을 수');
});
test('plain input errors do not offer a network retry',()=>expect(errorInfo(new Error('입력값 확인')).retryRead).toBe(false));
