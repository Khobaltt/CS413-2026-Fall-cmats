# LAMBDA3 JSON-RPC service

## Setup, tests, and startup

Run these commands from the repository's `assigns/07/` directory:

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install Flask==3.1.3 jsonschema==4.26.0
python3 -m unittest discover -s MySolution -p 'test_*.py' -v
python3 MySolution/app.py
```

Endpoint: `http://127.0.0.1:5000/rpc`. This is a local development server.
Use another terminal for the requests below. Stop with Ctrl+C. 

## Curl demonstrations

## Limits, contract, and architecture