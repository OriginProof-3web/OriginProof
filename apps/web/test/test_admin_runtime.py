"""Check that failed startup cannot overwrite the last EVM checkpoint."""
from pathlib import Path
from types import SimpleNamespace
import unittest
import ast
import json


class CheckpointGuardTest(unittest.TestCase):
    def test_failed_prepare_keeps_checkpoint(self):
        source = (Path(__file__).parent / 'admin-runtime.py').read_text()
        main = source[source.index("if __name__=='__main__':"):]
        calls = []
        def fail():
            raise RuntimeError('synthetic startup failure')
        namespace = dict(__name__='__main__', signal=SimpleNamespace(SIGTERM=15, signal=lambda *args: None), shutdown=lambda *args: None, os=SimpleNamespace(umask=lambda value: None), prepare=fail, checkpoint=lambda: calls.append('checkpoint'), CHILDREN=[])
        with self.assertRaises(RuntimeError):
            exec(main, namespace)
        self.assertEqual(calls, [])

    def test_restore_enables_automine_after_interval_configuration(self):
        # Anvil's interval setting disables automine; restore in the opposite order.
        source=(Path(__file__).parent/'admin-lifecycle-check.py').read_text()
        tree=ast.parse(source)
        recovery=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='recovery')
        guard=next(n for n in recovery.body if isinstance(n,ast.Try))
        calls=[]
        exec(compile(ast.Module(body=guard.finalbody,type_ignores=[]),'restore','exec'),{'rpc':lambda method,params:calls.append((method,params))})
        self.assertEqual(calls,[('evm_setIntervalMining',[0]),('evm_setAutomine',[True])])


class OperatorGateTest(unittest.TestCase):
    def check(self, status, role, expected):
        source=(Path(__file__).parent/'local-console-server.py').read_text()
        method=next(n for n in ast.walk(ast.parse(source)) if isinstance(n,ast.FunctionDef) and n.name=='local_operator')
        response=SimpleNamespace(status=status,read=lambda:json.dumps({'role':role}).encode())
        connection=SimpleNamespace(request=lambda *args,**kw:None,getresponse=lambda:response,close=lambda:None)
        namespace={'PORT':8768,'json':json,'http':SimpleNamespace(client=SimpleNamespace(HTTPConnection=lambda *args,**kw:connection,HTTPException=RuntimeError))}
        exec(compile(ast.Module(body=[method],type_ignores=[]),'operator-gate','exec'),namespace)
        handler=SimpleNamespace(headers={'Host':'127.0.0.1:8768','Cookie':'synthetic'})
        self.assertFalse(namespace['local_operator'](handler))
        self.assertEqual(handler.operator_error,expected)

    def test_rate_limit_does_not_look_like_permission_denial(self):
        self.check(429,'operator',429)

    def test_recipient_cannot_use_operator_proxy(self):
        self.check(200,'recipient',403)

    def test_unavailable_api_never_grants_operator_access(self):
        self.check(503,'operator',503)


if __name__ == '__main__':
    unittest.main()
