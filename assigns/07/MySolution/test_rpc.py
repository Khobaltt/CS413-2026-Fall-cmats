"""HTTP tests with the real supplied LAMBDA3 backend; run from assigns/07."""
import json
import multiprocessing as mp
from pathlib import Path
import time
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from jsonschema import Draft202012Validator
from app import create_app
from errors import RpcError
from service import LambdaService, MAX_SOURCE_BYTES, load_backend, run_interpretation

FACTORIAL = ('let fact : sint -> sint = fix fact(n: sint): sint => '
             'if n <= 1 then 1 else n * fact(n - 1) in fact(6) end')
ROOT = Path(__file__).resolve().parent
SCHEMA = json.loads((ROOT / 'rpc-schema.json').read_text())
RESPONSE_SCHEMA = {**SCHEMA, 'oneOf': [{'$ref': '#/$defs/responsePayload'}]}

def hanging_worker(result_path, source):
    """Failure injection only: prove an actual running child is stopped."""
    Path(source).write_text("started")
    while True:
        time.sleep(0.01)

class RpcTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def post(self, method='service.health', params=None, request_id='request'):
        return self.client.post('/rpc', json={'jsonrpc': '2.0', 'id': request_id,
                                            'method': method, 'params': {} if params is None else params})

    def error(self, response, code, request_id='request'):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'application/json')
        body = response.get_json()
        Draft202012Validator(RESPONSE_SCHEMA).validate(body)
        self.assertEqual(body['id'], request_id)
        self.assertEqual(body['error']['code'], code)
        self.assertNotIn('result', body)
        self.assertNotIn('Traceback', response.text)
        return body

    def test_health_and_id_types(self):
        for request_id in ('abc', 7, 1.25, None, 10**400):
            response = self.post(request_id=request_id)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get_json(), {'jsonrpc': '2.0', 'id': request_id,
                                                  'result': {'status': 'ok', 'version': '1.0'}})
            Draft202012Validator(RESPONSE_SCHEMA).validate(response.get_json())

    def test_json_parse_errors(self):
        for body in (b'{', b'', b'null trailing', b'NaN', b'Infinity', b'\xff'):
            self.error(self.client.post('/rpc', data=body, content_type='application/json'), -32700, None)

    def test_invalid_envelopes(self):
        for payload in (None, True, 5, 'text', {}, {'method': 2},
                        {'jsonrpc': '1.0', 'method': 'service.health', 'id': 9},
                        *({'jsonrpc': '2.0', 'method': 'service.health', 'id': value}
                          for value in (True, [], {}))):
            expected = 9 if isinstance(payload, dict) and payload.get('id') == 9 else None
            self.error(self.client.post('/rpc', data=json.dumps(payload), content_type='application/json'), -32600, expected)

    def test_unknown_method(self):
        for method in ('unknown', 'Service.health', 'lambda.lint', ''):
            self.error(self.post(method), -32601)

    def test_missing_and_wrong_params(self):
        for method in ('service.health', 'lambda.typecheck', 'lambda.interpret', 'lambda.compile'):
            for value in (None, [], 'bad', 1, True):
                self.error(self.client.post('/rpc', json={'jsonrpc': '2.0', 'id': 'request',
                                                         'method': method, 'params': value}), -32602)
            self.error(self.client.post('/rpc', json={'jsonrpc': '2.0', 'id': 'request', 'method': method}), -32602)
        self.error(self.post(params={'extra': 1}), -32602)

    def test_bad_sources(self):
        for method in ('lambda.typecheck', 'lambda.interpret', 'lambda.compile'):
            for source in ('', ' \t\n', None, 42, True, [], '\ud800', '1' * (MAX_SOURCE_BYTES + 1), 'é' * 8193):
                params = {'source': source, **({'target': 'python'} if method == 'lambda.compile' else {})}
                self.error(self.post(method, params), -32602)
        self.error(self.post('lambda.typecheck', {'source': '1', 'extra': 0}), -32602)

    def test_compile_target_validation(self):
        for target in ('Python', 'rust', None, 3, [], {}):
            self.error(self.post('lambda.compile', {'source': '1', 'target': target}), -32602)
        self.error(self.post('lambda.compile', {'source': '1'}), -32602)

    def test_source_size_boundary(self):
        response = self.post('lambda.typecheck', {'source': '1' + ' ' * (MAX_SOURCE_BYTES - 1)})
        self.assertEqual(response.get_json()['result'], {'type': 'sint'})

    def test_transport_status(self):
        self.assertEqual(self.client.post('/rpc', data='{}', content_type='text/plain').status_code, 415)
        self.assertEqual(self.client.get('/rpc').status_code, 405)
        self.assertEqual(self.client.post('/missing', json={}).status_code, 404)
        self.assertEqual(self.client.post('/rpc', data=b' ' * 1_048_577, content_type='application/json').status_code, 413)
        self.assertEqual(self.client.post('/rpc', data='{}', content_type='application/json; charset=utf-8').status_code, 200)

    def test_single_notifications(self):
        for method, params in (('service.health', {}), ('missing', {}), ('lambda.typecheck', {'source': ''})):
            response = self.client.post('/rpc', json={'jsonrpc': '2.0', 'method': method, 'params': params})
            self.assertEqual((response.status_code, response.data), (204, b''))

    def test_batch_mixed(self):
        payload = [{'jsonrpc': '2.0', 'id': 'b', 'method': 'service.health', 'params': {}},
                   {'jsonrpc': '2.0', 'method': 'service.health', 'params': {}},
                   {'jsonrpc': '2.0', 'id': 2, 'method': 'lambda.typecheck', 'params': {'source': 'true'}},
                   17, {'jsonrpc': '2.0', 'method': 'service.health', 'id': False},
                   {'jsonrpc': '2.0', 'id': None, 'method': 'missing', 'params': {}}]
        response = self.client.post('/rpc', json=payload)
        self.assertEqual(response.status_code, 200)
        bodies = response.get_json()
        Draft202012Validator(RESPONSE_SCHEMA).validate(bodies)
        self.assertEqual(len(bodies), 5)
        by_id = {x['id']: x for x in bodies if x['id'] is not None}
        self.assertEqual(by_id['b']['result']['status'], 'ok')
        self.assertEqual(by_id[2]['result']['type'], 'bool')
        self.assertEqual(sum(x.get('error', {}).get('code') == -32600 for x in bodies), 2)
        self.assertEqual(sum(x.get('error', {}).get('code') == -32601 for x in bodies), 1)

    def test_notification_batch(self):
        payload = [{'jsonrpc': '2.0', 'method': method, 'params': {}} for method in ('service.health', 'missing')]
        response = self.client.post('/rpc', json=payload)
        self.assertEqual((response.status_code, response.data), (204, b''))

    def test_empty_batch(self):
        self.assertIsInstance(self.error(self.client.post('/rpc', json=[]), -32600, None), dict)

    def test_single_call_batch_stays_array(self):
        response = self.client.post('/rpc', json=[{'jsonrpc': '2.0', 'id': 1, 'method': 'service.health', 'params': {}}])
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.get_json(), list)

    def test_unexpected_failure_is_logged_and_redacted(self):
        with patch.object(LambdaService, 'call', side_effect=RuntimeError('/private/backend.py secret')):
            with self.assertLogs('dispatcher', level='ERROR'):
                response = self.post()
        self.error(response, -32603)
        for fragment in ('/private', 'secret', 'RuntimeError'):
            self.assertNotIn(fragment, response.text)

    def test_timeout_rpc_mapping(self):
        failure = RpcError(-32012, 'Execution timeout', {'kind': 'timeout', 'limit_seconds': 2.0})
        with patch('service.run_interpretation', side_effect=failure):
            self.error(self.post('lambda.interpret', {'source': '42'}), -32012)

    def test_actual_deadline_terminates_worker(self):
        before = {child.pid for child in mp.active_children()}
        started = time.monotonic()
        with TemporaryDirectory() as directory:
            ready = Path(directory) / 'ready'
            with self.assertRaises(RpcError) as failure:
                run_interpretation(str(ready), seconds=1.0, worker=hanging_worker)
            self.assertTrue(ready.exists(), 'Worker must actually start before timeout')
        self.assertEqual(failure.exception.code, -32012)
        self.assertLess(time.monotonic() - started, 3.0)
        self.assertEqual({child.pid for child in mp.active_children()}, before)

    def test_actual_timeout_over_http(self):
        client = create_app(LambdaService(seconds=0.000001)).test_client()
        self.error(client.post('/rpc', json={'jsonrpc': '2.0', 'id': 'request', 'method': 'lambda.interpret', 'params': {'source': '42'}}), -32012)

    def test_schema_rejects_invalid_response(self):
        Draft202012Validator.check_schema(SCHEMA)
        validator = Draft202012Validator(RESPONSE_SCHEMA)
        for body in ({'jsonrpc': '2.0', 'id': 1},
                     {'jsonrpc': '2.0', 'id': 1, 'result': {}, 'error': {'code': 0, 'message': 'bad'}},
                     {'jsonrpc': '2.0', 'id': True, 'result': {}}):
            self.assertFalse(validator.is_valid(body))

    def test_typecheck_real_programs(self):
        for source, typ in (('42', 'sint'), ('true', 'bool'), ('lam(x: sint) => x', 'sint -> sint')):
            response = self.post('lambda.typecheck', {'source': source})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get_json()['result'], {'type': typ})

    def test_interpret_real_programs(self):
        for source, typ, value in (('6 * 7', 'sint', '42'), (FACTORIAL, 'sint', '720'),
                                   ('(42, true)', '(sint, bool)', '(42, true)'),
                                   ('list_cons(1, list_cons(2, list_nil()))', 'List[sint]', '[1, 2]')):
            with self.subTest(source=source):
                response = self.post('lambda.interpret', {'source': source})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.get_json()['result'], {'type': typ, 'value': value})

    def test_compile_both_targets_unchanged(self):
        backend = load_backend()
        expression, _ = backend.d0exp_parse_and_typecheck(FACTORIAL)
        for target, compiler in (('python', backend.d0exp_compile), ('javascript', backend.d0exp_compile_js)):
            response = self.post('lambda.compile', {'source': FACTORIAL, 'target': target})
            self.assertEqual(response.status_code, 200)
            result = response.get_json()['result']
            self.assertEqual(result['target'], target)
            self.assertTrue(result['code'].strip())
            self.assertEqual(result['code'], compiler(expression))

    def test_syntax_and_type_errors_all_source_methods(self):
        for method in ('lambda.typecheck', 'lambda.interpret', 'lambda.compile'):
            for source, code, kind in (('@', -32010, 'syntax'), ('1 + true', -32011, 'type')):
                params = {'source': source, **({'target': 'python'} if method == 'lambda.compile' else {})}
                body = self.error(self.post(method, params), code)
                self.assertEqual(body['error']['data']['kind'], kind)
                self.assertTrue(body['error']['data']['detail'])
                self.assertNotIn('<lambda>', json.dumps(body))

    def test_unbound_variable_rejected(self):
        body = self.error(self.post('lambda.typecheck', {'source': 'missing'}), -32011)
        self.assertIn('unbound variable', body['error']['data']['detail'])

    def test_closures_are_formatted(self):
        for source, value in (('lam(x: sint) => x', '<lam>'), ('fix f(x: sint): sint => x', '<fix>')):
            response = self.post('lambda.interpret', {'source': source})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get_json()['result'], {'type': 'sint -> sint', 'value': value})
            self.assertNotIn('ENV', response.text)

    def test_large_formatted_result(self):
        response = self.post('lambda.interpret', {'source': 'a1sz_make_ncpy(40000, 1)'})
        self.assertEqual(response.status_code, 200)
        result = response.get_json()['result']
        self.assertEqual(result['type'], 'A1sz[sint]')
        self.assertEqual(result['value'], '[' + ', '.join(['1'] * 40000) + ']')

    def test_real_runtime_failure_redacted(self):
        self.error(self.post('lambda.interpret', {'source': '1 / 0'}), -32603)

if __name__ == '__main__':
    unittest.main()
