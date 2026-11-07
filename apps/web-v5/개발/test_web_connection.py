"""Real loopback web proxy + persisted PostgreSQL + Anvil integration, synthetic accounts only."""
import json
from datetime import UTC,datetime,timedelta
from pathlib import Path
from uuid import uuid4
import httpx
import pytest

ORIGIN='http://127.0.0.1:8768'
@pytest.fixture(scope='module')
def clients():
    accounts=json.loads((Path.home()/'.local/share/originproof-web-test/accounts.json').read_text())
    created={}
    for name in ('bank','office','recipient','other-recipient','operator'):
        account=next(a for a in accounts if a['username']==name)
        client=httpx.Client(base_url=ORIGIN,headers={'Origin':ORIGIN},timeout=45,trust_env=False)
        response=client.post('/api/v1/auth/login',json={'username':name,'password':account['password']})
        assert response.status_code==200
        client.headers['X-CSRF-Token']=response.json()['csrf_token']
        created[name]=client
    yield created
    for client in created.values():client.close()

@pytest.fixture(scope='module')
def issued(clients):
    records={}
    for name,kind in [('bank','PAYMENT_REQUEST'),('office','OFFICIAL_DOCUMENT')]:
        client=clients[name]
        assert client.get('/api/v1/issuer/status').json()['status']=='ACTIVE'
        keys=client.get('/api/v1/issuer/keys').json()
        if not any(k['selected'] and k['status']=='ACTIVE' for k in keys):
            now=datetime.now(UTC).replace(microsecond=0)
            response=client.post('/api/v1/issuer/keys',json={'request_id':'req_'+uuid4().hex,'reason':'isolated synthetic web test','valid_from':now.isoformat(),'valid_until':(now+timedelta(days=30)).isoformat()})
            assert response.status_code==200 and response.json()['status']=='CONFIRMED'
        content=({'proof_type':kind,'amount_minor':85000,'currency':'KRW','target_ref':'SYNTHETIC-WEB-E2E'} if name=='bank' else {'proof_type':kind,'institution_code':'ORIGIN_MOCK_OFFICE','document_type':'SYNTHETIC_CERTIFICATE','document_number':'SYNTHETIC-WEB-E2E','version':1})
        body={'request_id':'req_'+uuid4().hex,'recipient_id':'acct_web_recipient','expires_at':(datetime.now(UTC)+timedelta(days=1)).replace(microsecond=0).isoformat(),'content':content}
        response=client.post('/api/v2/issuer/proofs',json=body)
        assert response.status_code==200
        records[name]=(response.json(),body)
    return records

def verify(client,id,candidate=None):
    body={'request_id':'req_'+uuid4().hex}
    if candidate is not None:body['candidate']=candidate
    return client.post(f'/api/v2/proofs/{id}/verify',json=body)

def test_real_session_cookie_and_role(clients):
    me=clients['bank'].get('/api/v1/auth/me')
    assert me.json()['role']=='issuer' and me.json()['issuer_id']=='iss_origin_mock_bank'
    assert clients['recipient'].get('/api/v1/issuer/keys').status_code==403
    assert clients['bank'].get('/api/v1/operator/issuer-applications').status_code==403

def test_wrong_password_and_no_session():
    with httpx.Client(base_url=ORIGIN,headers={'Origin':ORIGIN},trust_env=False) as client:
        assert client.post('/api/v1/auth/login',json={'username':'bank','password':'wrong'}).status_code==401
        assert client.get('/api/v1/auth/me').status_code==401

def test_csrf_required(clients):
    client=clients['bank'];token=client.headers.pop('X-CSRF-Token')
    try:
        response=client.post('/api/v1/issuer/keys/key_unknown/revoke',json={'request_id':'req_'+uuid4().hex,'reason':'synthetic test'})
        assert response.status_code==403
    finally:client.headers['X-CSRF-Token']=token

@pytest.mark.parametrize('name',['bank','office'])
def test_idempotent_issuance_and_conflict(clients,issued,name):
    row,body=issued[name];client=clients[name]
    response=client.post('/api/v2/issuer/proofs',json=body)
    assert response.status_code==200 and response.json()['proof_id']==row['proof_id']
    changed=body|{'expires_at':(datetime.now(UTC)+timedelta(days=2)).replace(microsecond=0).isoformat()}
    assert client.post('/api/v2/issuer/proofs',json=changed).status_code==409

@pytest.mark.parametrize('name',['bank','office'])
def test_public_read_does_not_reveal_content(issued,name):
    row,_=issued[name]
    with httpx.Client(base_url=ORIGIN,headers={'Origin':ORIGIN},trust_env=False) as client:
        response=client.get('/api/v2/proofs/'+row['proof_id'])
        assert response.status_code==200 and 'payload' not in response.json()
        result=verify(client,row['proof_id']).json()
        assert result['verification_status']=='VERIFIED' and result['scope']=='PROOF_ONLY'
        assert result['lifecycle_status'] is None and result['checks']['proof_status']=='NOT_RUN'
        assert client.get('/api/v2/proofs/'+row['proof_id']+'/content').status_code==401

@pytest.mark.parametrize('name',['bank','office'])
def test_recipient_normal_and_tampered_comparison(clients,issued,name):
    row,body=issued[name];candidate={k:v for k,v in body['content'].items() if k!='proof_type'}
    normal=verify(clients['recipient'],row['proof_id'],candidate).json()
    assert normal['verification_status']=='VERIFIED' and normal['scope']=='FULL_COMPARISON'
    changed=candidate|({'amount_minor':85001} if name=='bank' else {'document_number':'SYNTHETIC-CHANGED'})
    tampered=verify(clients['recipient'],row['proof_id'],changed).json()
    assert tampered['verification_status']=='TAMPERED'
    assert ('AMOUNT_MISMATCH' if name=='bank' else 'FIELD_MISMATCH') in tampered['reason_codes']

@pytest.mark.parametrize('name',['bank','office'])
def test_other_recipient_cannot_read_or_compare(clients,issued,name):
    row,body=issued[name];client=clients['other-recipient']
    assert client.get('/api/v2/proofs/'+row['proof_id']+'/content').status_code==404
    assert verify(client,row['proof_id'],{}).status_code==404

def test_issuer_lists_and_keys_are_separate(clients,issued):
    bank=clients['bank'].get('/api/v2/issuer/proofs').json();office=clients['office'].get('/api/v2/issuer/proofs').json()
    assert all(p['issuer_id']=='iss_origin_mock_bank' for p in bank)
    assert all(p['issuer_id']=='iss_origin_mock_office' for p in office)
    key=clients['bank'].get('/api/v1/issuer/keys').json()[0]['key_id']
    assert clients['office'].get('/api/v1/issuer/keys/'+key).status_code==404

def test_partial_comparison_is_inconclusive(clients,issued):
    result=verify(clients['recipient'],issued['bank'][0]['proof_id'],{'currency':'KRW'}).json()
    assert result['scope']=='PARTIAL_COMPARISON' and result['verification_status']=='INCONCLUSIVE'

def test_missing_proof_is_not_faked(clients):
    assert clients['recipient'].get('/api/v2/proofs/prf_missing_web_test').status_code==404
