"""Synthetic lifecycle checks through the same operator-gated admin proxy."""
import http.cookiejar
import json
import urllib.request
import urllib.error
import uuid
import time
from pathlib import Path
from datetime import datetime,timezone,timedelta
BASE='http://127.0.0.1:8768'
jar=http.cookiejar.CookieJar()
client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
cases=[]
def call(prefix,path,body=None,expected=200):
 headers={'Content-Type':'application/json','Origin':BASE}
 if body is not None and 'auth/login' not in path and not path.endswith('/verify') and prefix!='/admin-analyzer':
  headers['X-CSRF-Token']=call(prefix,'/v1/auth/me')['csrf_token']
 time.sleep(.9)
 req=urllib.request.Request(BASE+prefix+path,None if body is None else json.dumps(body).encode(),headers)
 try:
  with client.open(req,timeout=60) as r:code=r.status;data=json.load(r)
 except urllib.error.HTTPError as e:
  code=e.code;raw=e.read()
  try:data=json.loads(raw)
  except ValueError:data={'detail':'Local proxy or rate limit rejection'}
 assert code==expected,f'{path}: expected {expected}, got {code}: {data}'
 return data

def record(name,fn):
 try:fn();cases.append({'name':name,'group':'8768 관리자 · 실제 PostgreSQL/Anvil','status':'passed','detail':''})
 except Exception as e:cases.append({'name':name,'group':'8768 관리자 · 실제 PostgreSQL/Anvil','status':'failure','detail':str(e)});raise

def mutation(**kw):return dict(request_id='req_'+uuid.uuid4().hex,**kw)
def stamp(days=1):return (datetime.now(timezone.utc)+timedelta(days=days)).replace(microsecond=0).isoformat()
def verify(id,role='recipient',candidate=None):
 result=None
 for attempt in range(4):
  result=call('/test-api/'+role,f'/v2/proofs/{id}/verify',dict(request_id='req_'+uuid.uuid4().hex,**({} if candidate is None else {'candidate':candidate})))
  if result['verification_status']!='INCONCLUSIVE' or 'DEPENDENCY_UNAVAILABLE' not in result['reason_codes']:return result
 return result
accounts=json.loads((Path.home()/'.local/share/originproof-web-test/accounts.json').read_text())
op=next(a for a in accounts if a['username']=='operator')
call('/api','/v1/auth/login',dict(username=op['username'],password=op['password']))
try:
 for role,label in [('bank','Origin Mock Bank'),('office','Origin Mock Office')]:
  prefix='/test-api/'+role
  app=call(prefix,'/v1/issuer-applications/mine')
  if not app:app=call(prefix,'/v1/issuer-applications',{'issuer_name':label},201)
  if app['status']=='SUSPENDED':call('/test-api/operator',f"/v1/operator/issuers/{app['issuer_id']}/reactivate",mutation(reason='Synthetic interrupted test recovery'))
  if app['status']=='PENDING_REVIEW':call('/test-api/operator',f"/v1/operator/issuer-applications/{app['application_id']}/decision",dict(decision='APPROVE',reason='Synthetic administrator QA'))
  if app['status'] in ['PENDING_REVIEW','APPROVED_PENDING_CHAIN']:
   activated=call('/test-api/operator',f"/v1/operator/issuer-applications/{app['application_id']}/activate",mutation(reason='Synthetic administrator QA'))
   assert activated['status']=='CONFIRMED',activated
  def state():assert call(prefix,'/v1/issuer/status')['status']=='ACTIVE'
  record(role+' 기관 승인·실제 Registry 활성화',state)
  keys=call(prefix,'/v1/issuer/keys')
  if not any(k['selected'] and k['status']=='ACTIVE' for k in keys):
   keyop=call(prefix,'/v1/issuer/keys',mutation(reason='Synthetic initial key',valid_from=stamp(-1),valid_until=stamp(30)))
   assert keyop['status']=='CONFIRMED',keyop
  def issue(content):
   recipient=call(prefix,'/v2/issuer/recipients')[0]['recipient_id']
   return call(prefix,'/v2/issuer/proofs',mutation(recipient_id=recipient,expires_at=stamp(),content=content))
  content=({'proof_type':'PAYMENT_REQUEST','amount_minor':85000,'currency':'KRW','target_ref':'SYNTHETIC-'+uuid.uuid4().hex} if role=='bank' else {'proof_type':'OFFICIAL_DOCUMENT','institution_code':'ORIGIN_MOCK_OFFICE','document_type':'SYNTHETIC_CERTIFICATE','document_number':'MOCK-'+uuid.uuid4().hex,'version':1})
  row=issue(content);id=row['proof_id']
  def registered():
   assert row['registration_status']=='CONFIRMED',row
   result=verify(id);assert result['verification_status']=='VERIFIED' and result['lifecycle_status']=='ACTIVE',result
   assert call(prefix,f'/v2/issuer/proofs/{id}/reconciliation')['registration_consistent'] is True
   alias=call(prefix,f'/v2/issuer/proofs/{id}/register',mutation())
   original=call(prefix,f"/v1/operations/{row['registration_operation_id']}")
   assert alias['status']=='CONFIRMED' and alias['tx_hash']==original['tx_hash']
  record(role+' 발행·등록·현재 검증·DB/체인 일치',registered)
  def compare():
   candidate={k:v for k,v in content.items() if k!='proof_type'}
   result=verify(id,candidate=candidate);assert result['verification_status']=='VERIFIED',result
   candidate['amount_minor' if role=='bank' else 'document_number']=85001 if role=='bank' else 'TAMPERED'
   result=verify(id,candidate=candidate);assert result['verification_status']=='TAMPERED',result
  record(role+' 정상·변조 내용 비교',compare)
  def ownership():call('/test-api/'+('office' if role=='bank' else 'bank'),f'/v2/issuer/proofs/{id}/revoke',mutation(reason='Cross issuer'),404)
  record(role+' 타 기관 폐기 거부',ownership)
  if role=='bank':
   def consume():
    call('/test-api/other-recipient',f'/v2/proofs/{id}/consume',mutation(),404)
    assert verify(id)['lifecycle_status']=='ACTIVE'
    op=call('/test-api/recipient',f'/v2/proofs/{id}/consume',mutation());assert op['status']=='CONFIRMED',op
    result=verify(id);assert result['lifecycle_status']=='CONSUMED',result
    call('/test-api/recipient',f'/v2/proofs/{id}/consume',mutation(),409)
   record('지정 수신자·조회 비소모·1회 사용·중복 사용 거부',consume)
  else:
   def document():call('/test-api/recipient',f'/v2/proofs/{id}/consume',mutation(),409)
   record('문서 consume 거부',document)
  revoke=issue(content);rid=revoke['proof_id']
  def revocation():
   op=call(prefix,f'/v2/issuer/proofs/{rid}/revoke',mutation(reason='Synthetic revocation'));assert op['status']=='CONFIRMED',op
   result=verify(rid);assert result['lifecycle_status']=='PROOF_REVOKED',result
   assert call(prefix,f"/v1/operations/{op['operation_id']}")['status']=='CONFIRMED'
  record(role+' Proof 폐기·Operation 조회',revocation)
  def key_rotation():
   old=next(k for k in call(prefix,'/v1/issuer/keys') if k['selected'])
   protected=issue(content)['proof_id']
   op=call(prefix,'/v1/issuer/keys/rotate',mutation(reason='Synthetic normal rotation',valid_from=stamp(-1),valid_until=stamp(30)));assert op['status']=='CONFIRMED',op
   assert verify(protected)['lifecycle_status']=='ACTIVE'
   op=call(prefix,f"/v1/issuer/keys/{old['key_id']}/revoke",mutation(reason='Synthetic compromised previous key'));assert op['status']=='CONFIRMED',op
   result=verify(protected);assert 'ISSUER_KEY_REVOKED' in result['reason_codes'],result
  record(role+' 정상 키 교체·이전 Proof 유지·유출 키 폐기 반영',key_rotation)
  def suspension():
   issuer='iss_origin_mock_'+role
   op=call('/test-api/operator',f'/v1/operator/issuers/{issuer}/suspend',mutation(reason='Synthetic suspension'));assert op['status']=='CONFIRMED'
   assert call(prefix,'/v1/issuer/status')['status']=='SUSPENDED'
   op=call('/test-api/operator',f'/v1/operator/issuers/{issuer}/reactivate',mutation(reason='Synthetic reactivate'));assert op['status']=='CONFIRMED'
   assert call(prefix,'/v1/issuer/status')['status']=='ACTIVE'
  record(role+' 기관 중지·재활성화',suspension)
 def recovery():
  # Hold mining only in this dedicated synthetic EVM, then recover the same tx.
  def rpc(method,params):
   req=urllib.request.Request('http://127.0.0.1:18546',json.dumps(dict(jsonrpc='2.0',id=1,method=method,params=params)).encode(),{'Content-Type':'application/json'})
   with urllib.request.urlopen(req,timeout=10) as response:result=json.load(response)
   assert 'error' not in result,result.get('error');return result['result']
  prefix='/test-api/bank';content={'proof_type':'PAYMENT_REQUEST','amount_minor':85000,'currency':'KRW','target_ref':'SYNTHETIC-RECOVERY-'+uuid.uuid4().hex}
  recipient=call(prefix,'/v2/issuer/recipients')[0]['recipient_id']
  proof=call(prefix,'/v2/issuer/proofs',mutation(recipient_id=recipient,expires_at=stamp(),content=content))
  rpc('evm_setAutomine',[False]);rpc('evm_setIntervalMining',[0])
  try:
   op=call(prefix,f"/v2/issuer/proofs/{proof['proof_id']}/revoke",mutation(reason='Synthetic receipt recovery'))
   assert op['status'] in ['UNKNOWN','SUBMITTED'],op
   assert op['recovery_required'] is True
   rpc('evm_mine',[])
   recovered=call(prefix,f"/v1/operations/{op['operation_id']}/recover",{})
   assert recovered['status']=='CONFIRMED' and recovered['tx_hash']==op['tx_hash'],recovered
   assert verify(proof['proof_id'])['lifecycle_status']=='PROOF_REVOKED'
  finally:rpc('evm_setAutomine',[True]);rpc('evm_setIntervalMining',[1])
 record('거래 receipt 미확인·같은 tx 복구·중복 재전송 방지',recovery)
 def sync():
  result=call('/test-api/operator','/v1/chain-sync');assert result['authority']=='HISTORICAL_EVENTS_ONLY' and result['status']!='DISABLED',result
 record('체인 동기화 읽기·최종 권위 분리',sync)
 def ai():
  assert call('/admin-analyzer','/v1/capabilities')['provider']=='mock'
  candidate=call('/admin-analyzer','/v1/analyze/card-payment-notice',{'text':'issuer: Origin Mock Bank\ncard: ****1234\namount: 85,000원\nmerchant: Synthetic Shop\napproved_at: 2026-10-03T09:00:00+09:00\ntransaction_id: SYNTHETIC-001'})
  assert candidate['amount_minor']==85000,candidate
 record('기존 AI 후보 추출 mock·금액 추출',ai)
finally:
 report={'sha':'3ef1fd40943914c1450e8bc05047119ab7eabbc0','title':'최신 관리자 기능 · 실제 API/체인 · mock AI','status':'passed' if cases and all(c['status']=='passed' for c in cases) else 'failed','cases':cases,'finished_at':datetime.now(timezone.utc).isoformat()}
 Path('/tmp/originproof-admin-lifecycle.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
 print(json.dumps(report,ensure_ascii=False))
