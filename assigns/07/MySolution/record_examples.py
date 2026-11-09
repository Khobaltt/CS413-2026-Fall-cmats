"""Reproduce the recorded demonstrations using Flask's HTTP test client."""
import json
from pathlib import Path
from app import create_app

FACTORIAL = ('let fact : sint -> sint = fix fact(n: sint): sint => '
             'if n <= 1 then 1 else n * fact(n - 1) in fact(6) end')

def record():
    destination = Path(__file__).resolve().parent / 'examples'
    destination.mkdir(exist_ok=True)
    client = create_app().test_client()
    calls = [
        ('factorial', 'lambda.interpret', {'source': FACTORIAL}),
        ('type-error', 'lambda.typecheck', {'source': 'missing'}),
        ('compile', 'lambda.compile', {'source': '42', 'target': 'python'}),
        ('compile-js', 'lambda.compile', {'source': '42', 'target': 'javascript'}),
    ]
    for name, method, params in calls:
        request_id = 3 if name == 'compile' else name
        payload = {'jsonrpc': '2.0', 'id': request_id, 'method': method, 'params': params}
        response = client.post('/rpc', json=payload)
        assert response.status_code == 200
        body = response.get_json()
        assert ('error' in body) == (name == 'type-error'), body
        for suffix, value in (('request', payload), ('response', body)):
            path = destination / f'{name}-{suffix}.json'
            path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
        print(f'{name}: HTTP {response.status_code}; ' +
              (f"error {body['error']['code']}" if 'error' in body else
               f"result fields {', '.join(body['result'])}"))

if __name__ == '__main__':
    record()
