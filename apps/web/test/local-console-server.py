"""Local, fixed-SHA PR test runner. No production API or personal .env access."""
import hashlib
import http.client
import json
import os
import subprocess
import tarfile
import tempfile
import threading
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(os.environ.get('ORIGINPROOF_CONSOLE_ROOT', Path(__file__).resolve().parents[1] / 'official'))
WEB_SOURCE = Path(os.environ.get('ORIGINPROOF_WEB_SOURCE', Path(__file__).resolve().parents[1]))
PORT = 8768
SUITES = {
    '35': {'sha': '17c24a36a46c6b2a823a3b7fac20c97c6faee98f', 'title': 'C · W3 발행·조회·내용 비교', 'path': 'apps/api/tests'},
    'web': {'sha': '85e152cd5550f24874abb267122a5d8ece29e3b9', 'title': '웹 프록시·사용자·기업 실제 API 연결', 'path': str(ROOT / 'test_web_connection.py')},
    '36': {'sha': '85e152cd5550f24874abb267122a5d8ece29e3b9', 'title': 'C · 실제 PostgreSQL·Anvil 연결 및 키 교체', 'path': 'apps/api/tests'},
    '40': {'sha': '92e0e94cba8e7799f709060afc9f4e02d220d142', 'title': 'B · W3 체인 조회·서명 경계', 'path': 'services/indexer/tests'},
}
SUITES['38']={'sha':'3ef1fd40943914c1450e8bc05047119ab7eabbc0','title':'C W6 최신 · API/Adapter/Analyzer 회귀','path':['apps/api/tests','services/indexer/tests','services/analyzer/tests']}
SUITES['admin']={'sha':'3ef1fd40943914c1450e8bc05047119ab7eabbc0','title':'최신 관리자 기능 · 실제 API/체인 · mock AI','path':'test/admin-lifecycle-check.py'}
SUITES['49']={'sha':'f2e9774003badb692fb4de6b89de640a155c1fa6','title':'D W4 최신 · 정책 QA (실제 DB/체인 opt-in·D3 브라우저 제외)','path':'fixtures/finals/test_w4_lifecycle_qa.py'}
REPORT = ROOT / 'collaboration-results.json'
LOCK = threading.Lock()
BUSY = set()
TEST_SESSIONS = {}
ACCOUNT_FILE = Path.home()/'.local/share/originproof-web-test/accounts.json'
SUITES['w3'] = {'sha':'76533198a4130a81d33917f6af08c7b6fa6188ff','title':'현재 웹 · 기업/개인/관리자 · QR · 실제 연결','path':'e2e'}


def save_result(key, result):
    with LOCK:
        data = json.loads(REPORT.read_text()) if REPORT.exists() else {}
        data[key] = result
        temporary = REPORT.with_suffix('.tmp')
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        temporary.replace(REPORT)
        snapshot = ROOT / 'collaboration-results.js'
        snapshot_temp = snapshot.with_suffix('.tmp')
        snapshot_temp.write_text('window.collaborationSavedResults = ' + json.dumps(data, ensure_ascii=True) + ';\n')
        snapshot_temp.replace(snapshot)


def run_suite(key):
    suite = SUITES[key]
    result = {**suite, 'status': 'running', 'cases': [], 'started_at': datetime.now(timezone.utc).isoformat()}
    save_result(key, result)
    env = os.environ.copy()
    for name in list(env):
        if name.startswith(('M4_LIVE_', 'API_LIVE_', 'FINALS_LIVE_', 'OPENAI_', 'TEST_DATABASE_', 'TEST_CHAIN_', 'SEED_DATABASE_')):
            env.pop(name)
    env.update(UV_PROJECT_ENVIRONMENT='.uv-venv', PYTHONPATH='apps/api/src:packages/python:services/analyzer/src', LLM_PROVIDER='mock')
    checkout = Path(tempfile.gettempdir()) / f'originproof-collaboration-{suite["sha"]}'
    if key == '36':
        env.update(TEST_DATABASE_URL='postgresql+asyncpg://originproof:originproof@127.0.0.1:55432/originproof', TEST_CHAIN_RPC_URL='http://127.0.0.1:18545', TEST_CHAIN_MANIFEST='/tmp/originproof-web-c36/packages/contracts/deployments/31337.local.json')
    if key == 'web':
        result['web_fingerprint'] = hashlib.sha256(b''.join((ROOT / path).read_bytes() for path in ('api-client.js','auth.js','components/user/UserWorkspace.tsx','components/business/BusinessWorkspace.tsx','test_web_connection.py'))).hexdigest()
    logs = []
    try:
        if key == 'admin':
            process=subprocess.run(['python3',str(WEB_SOURCE/'test/admin-lifecycle-check.py')],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=300)
            report=Path('/tmp/originproof-admin-lifecycle.json')
            if report.exists():result.update(json.loads(report.read_text()))
            result['status']='passed' if process.returncode==0 else 'failed'
            result['command']='python3 test/admin-lifecycle-check.py (8768 admin proxy)'
            logs.append(process.stdout);return
        if key == 'w3':
            run_web_suite(result, logs)
            return
        if not checkout.exists():
            with tempfile.TemporaryDirectory() as temporary:
                archive = Path(temporary) / 'source.tar.gz'
                with archive.open('wb') as stream:
                    subprocess.run(['gh', 'api', f'repos/OriginProof-3web/OriginProof/tarball/{suite["sha"]}'], stdout=stream, stderr=subprocess.PIPE, check=True, timeout=90)
                with tarfile.open(archive) as bundle:
                    bundle.extractall(temporary, filter='data')
                source = next(path for path in Path(temporary).iterdir() if path.is_dir())
                source.rename(checkout)
        sync = subprocess.run(['uv', 'sync', '--frozen', '--all-packages', '--all-groups'], cwd=checkout, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
        logs.append(sync.stdout)
        if sync.returncode:
            raise RuntimeError('고정 lockfile 환경 준비 실패')
        junit = checkout / 'collaboration-junit.xml'
        junit.unlink(missing_ok=True)
        command = ['uv', 'run', '--all-packages', '--all-groups', 'pytest', '-q', '--tb=short', *(suite['path'] if isinstance(suite['path'],list) else [suite['path']]), f'--junitxml={junit}']
        result['command'] = ' '.join(command)
        process = subprocess.run(command, cwd=checkout, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
        logs.append(process.stdout)
        result['exit_code'] = process.returncode
        if junit.exists():
            for case in ET.parse(junit).iter('testcase'):
                status = 'passed'
                detail = ''
                for tag in ('skipped', 'failure', 'error'):
                    element = case.find(tag)
                    if element is not None:
                        status = tag
                        detail = element.get('message', '')
                        break
                result['cases'].append({'name': case.get('name'), 'group': case.get('classname'), 'status': status, 'detail': detail})
        result['status'] = 'passed' if process.returncode == 0 else 'failed'
    except Exception as error:
        result['status'] = 'error'
        logs.append(str(error))
    finally:
        result['output'] = '\n'.join(logs)
        result['finished_at'] = datetime.now(timezone.utc).isoformat()
        save_result(key, result)
        with LOCK:
            BUSY.discard(key)


def run_web_suite(result, logs):
    import re
    env = {k:v for k,v in os.environ.items() if not k.startswith(('OPENAI_', 'API_', 'TEST_', 'ORIGINPROOF_'))}
    env.update(ORIGINPROOF_WEB_BASE_URL='http://127.0.0.1:8768', ORIGINPROOF_TEST_ACCOUNTS=str(ACCOUNT_FILE), PLAYWRIGHT_JUNIT_OUTPUT_FILE=str(ROOT/'w3-junit.xml'))
    decoder=Path('/tmp/originproof-qrdecode')
    if decoder.exists():env['ORIGINPROOF_QR_DECODER']=str(decoder)
    fingerprint=hashlib.sha256()
    for p in sorted(ROOT.rglob('*')):
        if p.is_file() and 'node_modules' not in p.parts and p.suffix in ('.tsx','.css','.html','.js') and not p.name.startswith('collaboration-results'):
            fingerprint.update(str(p.relative_to(ROOT)).encode()+b'\0'+p.read_bytes()+b'\0')
    result['web_fingerprint']=fingerprint.hexdigest()
    result['sha']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=WEB_SOURCE,text=True).strip()
    result['worktree_modified']=bool(subprocess.check_output(['git','status','--porcelain','--','apps/web'],cwd=WEB_SOURCE.parent.parent,text=True).strip())
    (ROOT/'w3-junit.xml').unlink(missing_ok=True)
    (ROOT/'w3-components.xml').unlink(missing_ok=True)
    commands=[['python3','test/test_admin_runtime.py','-v'],['pnpm','lint'],['pnpm','typecheck'],['pnpm','test','--reporter=default','--reporter=junit',f'--outputFile={ROOT / "w3-components.xml"}'],['pnpm','exec','playwright','test','--workers=1','--reporter=line,junit']]
    for command in commands:
        process=subprocess.run(command,cwd=WEB_SOURCE,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=600)
        label=' '.join(command)
        # Live tests disable trace/screenshots; redact ANSI for readable local reports.
        logs.append(re.sub(r'\x1b\[[0-9;]*m','',process.stdout))
        result['cases'].append({'group':'현재 GitHub 웹 소스','name':label,'status':'passed' if process.returncode==0 else 'failure','detail':''})
        if command[0]=='python3':
            for name,group in re.findall(r'^(test_\w+) \(([^)]+)\) \.\.\. ok$',process.stdout,re.M):
                result['cases'].append({'group':group,'name':name,'status':'passed','detail':''})
        if process.returncode:break
    for report in (ROOT/'w3-components.xml',ROOT/'w3-junit.xml'):
      if report.exists():
        for case in ET.parse(report).iter('testcase'):
            failure=case.find('failure'); skipped=case.find('skipped')
            result['cases'].append({'group':case.get('classname'),'name':case.get('name'),'status':'failure' if failure is not None else 'skipped' if skipped is not None else 'passed','detail':failure.get('message','') if failure is not None else ''})
    result['command']=' → '.join(' '.join(c) for c in commands)
    result['status']='passed' if process.returncode==0 else 'failed'


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def proxy(self):
        # Fixed loopback API only; no caller-provided upstream or arbitrary target.
        if self.headers.get('Host') != f'127.0.0.1:{PORT}':
            self.send_error(403); return
        if self.command == 'POST' and self.headers.get('Origin') != f'http://127.0.0.1:{PORT}':
            self.send_error(403); return
        try:size = int(self.headers.get('Content-Length', '0'))
        except ValueError:self.send_error(400);return
        if size < 0 or size > 65536:
            self.send_error(413); return
        body = self.rfile.read(size) if size else None
        headers = {k: v for k, v in self.headers.items() if k.lower() in ('cookie','content-type','x-csrf-token','x-request-id')}
        connection = http.client.HTTPConnection('127.0.0.1', 8780, timeout=45)
        try:
            connection.request(self.command, self.path[4:], body, headers)
            upstream = connection.getresponse()
            output = upstream.read()
            self.send_response(upstream.status)
            for key, value in upstream.getheaders():
                if key.lower() in ('content-type','set-cookie','x-request-id'):
                    self.send_header(key,value)
            self.send_header('Content-Length', str(len(output)))
            self.end_headers(); self.wfile.write(output)
        except (OSError, http.client.HTTPException):
            self.send_error(503, 'Local API unavailable')
        finally:
            connection.close()

    def local_operator(self):
        self.operator_error=403
        if self.headers.get('Host') != f'127.0.0.1:{PORT}':return False
        connection=http.client.HTTPConnection('127.0.0.1',8780,timeout=10)
        try:
            connection.request('GET','/v1/auth/me',headers={'Cookie':self.headers.get('Cookie','')})
            response=connection.getresponse()
            if response.status in (429,503):self.operator_error=response.status
            return response.status==200 and json.loads(response.read()).get('role')=='operator'
        except (OSError,ValueError,http.client.HTTPException):
            self.operator_error=503
            return False
        finally:connection.close()

    def test_proxy(self):
        from http.cookies import SimpleCookie
        if not self.local_operator():self.send_error(self.operator_error);return
        if self.command=='POST' and self.headers.get('Origin')!=f'http://127.0.0.1:{PORT}':self.send_error(403);return
        parts=self.path.split('/',3)
        role=parts[2] if len(parts)>3 else ''
        path='/'+parts[3] if len(parts)>3 else ''
        if role not in ('bank','office','recipient','other-recipient','operator') or not path.startswith(('/v1/','/v2/')) or '/auth/login' in path or '/auth/logout' in path:
            self.send_error(404);return
        try:size=int(self.headers.get('Content-Length','0'))
        except ValueError:self.send_error(400);return
        if size<0 or size>65536:self.send_error(413);return
        body=self.rfile.read(size) if size else None
        key=(hashlib.sha256(self.headers.get('Cookie','').encode()).hexdigest(),role)
        connection=http.client.HTTPConnection('127.0.0.1',8780,timeout=45)
        try:
            with LOCK:cookie=TEST_SESSIONS.get(key)
            if not cookie:
                account=next(row for row in json.loads((Path.home()/'.local/share/originproof-admin-test/accounts.json').read_text()) if row['username']==role)
                connection.request('POST','/v1/auth/login',json.dumps({'username':role,'password':account['password']}),{'Content-Type':'application/json'})
                response=connection.getresponse();response.read()
                if response.status!=200:self.send_error(503);return
                jar=SimpleCookie()
                for name,value in response.getheaders():
                    if name.lower()=='set-cookie':jar.load(value)
                cookie='; '.join(f'{name}={value.value}' for name,value in jar.items())
                with LOCK:
                    if len(TEST_SESSIONS)>128:TEST_SESSIONS.clear()
                    TEST_SESSIONS[key]=cookie
            headers={k:v for k,v in self.headers.items() if k.lower() in ('content-type','x-csrf-token','x-request-id')}
            headers['Cookie']=cookie
            connection.request(self.command,path,body,headers)
            response=connection.getresponse();output=response.read()
            if response.status==401:
                with LOCK:TEST_SESSIONS.pop(key,None)
            self.send_response(response.status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(output)));self.end_headers();self.wfile.write(output)
        except (OSError,ValueError,StopIteration,http.client.HTTPException):self.send_error(503,'Synthetic test session unavailable')
        finally:connection.close()

    def analyzer_proxy(self):
        if not self.local_operator():self.send_error(self.operator_error);return
        if self.command=='POST' and self.headers.get('Origin')!=f'http://127.0.0.1:{PORT}':self.send_error(403);return
        path=self.path.removeprefix('/admin-analyzer')
        if (self.command,path) not in [('GET','/v1/capabilities'),('POST','/v1/analyze/card-payment-notice')]:self.send_error(404);return
        try:size=int(self.headers.get('Content-Length','0'))
        except ValueError:self.send_error(400);return
        if not 0<=size<=65536:self.send_error(413);return
        body=self.rfile.read(size) if size else None
        connection=http.client.HTTPConnection('127.0.0.1',8781,timeout=45)
        try:
            connection.request(self.command,path,body,{'Content-Type':'application/json'})
            response=connection.getresponse();output=response.read()
            self.send_response(response.status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(output)));self.end_headers();self.wfile.write(output)
        except (OSError,http.client.HTTPException):self.send_error(503)
        finally:connection.close()

    def translate_path(self, path):
        from urllib.parse import urlsplit, unquote
        route = unquote(urlsplit(path).path)
        if route in ('/mvp', '/finals', '/finals/keys'):
            return str(WEB_SOURCE / '.next/server/app' / (route[1:] + '.html'))
        if route.startswith('/_next/static/'):
            root = (WEB_SOURCE / '.next/static').resolve()
            candidate = (root / route.removeprefix('/_next/static/')).resolve()
            if candidate.is_relative_to(root):return str(candidate)
            return str(root / '__missing__')
        return super().translate_path(path)

    def do_GET(self):
        if self.path=='/':
            self.send_response(302);self.send_header('Location','/index.html');self.end_headers();return
        if self.path.split('?')[0] in ('/collaboration-results.json','/collaboration-results.js','/w3-junit.xml','/w3-components.xml') and not self.local_operator():self.send_error(self.operator_error);return
        if self.path.startswith("/admin-analyzer/"):self.analyzer_proxy();return
        if self.path.startswith("/test-api/"):self.test_proxy();return
        if self.path.startswith('/api/v1/') or self.path.startswith('/api/v2/') or self.path.startswith('/api/health/'):
            self.proxy(); return
        if any(part.startswith('.') for part in self.path.split('/')):
            self.send_error(404); return
        super().do_GET()

    def do_POST(self):
        if self.path.startswith("/admin-analyzer/"):self.analyzer_proxy();return
        if self.path.startswith("/test-api/"):self.test_proxy();return
        if self.path.startswith('/api/v1/') or self.path.startswith('/api/v2/'):
            self.proxy(); return
        if self.headers.get('Host') != f'127.0.0.1:{PORT}' or self.headers.get('Origin') != f'http://127.0.0.1:{PORT}' or self.headers.get('Content-Type') != 'application/json':
            self.send_error(403)
            return
        key = self.path.removeprefix('/run-pr/')
        if self.path != f'/run-pr/{key}' or key not in SUITES:
            self.send_error(404)
            return
        if not self.local_operator():self.send_error(self.operator_error);return
        with LOCK:
            if key in BUSY or (key in ('admin','w3') and BUSY.intersection(('admin','w3'))):
                self.send_error(409, 'Shared synthetic environment test already running')
                return
            BUSY.add(key)
        threading.Thread(target=run_suite, args=(key,), daemon=True).start()
        self.send_response(202)
        self.end_headers()


if __name__ == '__main__':
    import sys
    if '--run-tests' in sys.argv:
        for key in SUITES:
            run_suite(key)
    else:
        print(f'협업 테스트: http://127.0.0.1:{PORT}/user-login.html', flush=True)
        ThreadingHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
