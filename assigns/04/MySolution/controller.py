"""Coordinates model transitions and backend calls; no view dependency."""
from pathlib import Path
from threading import Thread
from model import Model, Result, StateError, MAX_BYTES
from backend import Backend, LambdaBackend

class Controller:
    def __init__(self, model=None, backend: Backend | None = None):
        self.model = model or Model()
        self.backend = backend or LambdaBackend()

    def request(self, command, data):
        m = self.model
        with m.lock:
            try:
                if command == 'edit':
                    m.edit(data['text'])
                elif command == 'apply':
                    m.apply()
                elif command == 'discard':
                    m.discard()
                elif command == 'manual':
                    m.manual()
                elif command == 'load':
                    m.clean()
                    choice = data['choice']
                    if choice not in ('factorial', 'fibonacci'):
                        raise StateError('Unknown example.')
                    text = (Path(__file__).parent / 'samples' / f'{choice}.lambda').read_text()
                    m.replace(text, choice.title())
                elif command == 'upload':
                    m.clean()
                    import base64
                    try:
                        raw = base64.b64decode(data['bytes'], validate=True)
                    except ValueError as exc:
                        raise StateError('Invalid upload encoding.') from exc
                    if len(raw) > MAX_BYTES:
                        # Keep valid textual rejected uploads editable.
                        try:
                            m.draft, m.draft_name = raw.decode('utf-8'), data['name']
                        except UnicodeError:
                            pass
                        raise StateError(f'Source exceeds {MAX_BYTES} UTF-8 bytes.')
                    try:
                        text = raw.decode('utf-8')
                    except UnicodeError as exc:
                        raise StateError('Upload is not valid UTF-8; choose a UTF-8 text file.') from exc
                    m.replace(text, data['name'])
                elif command == 'action':
                    operation = data['operation']
                    if operation not in ('lint', 'interpret', 'typecheck', 'compile', 'execute'):
                        raise StateError('Unknown operation.')
                    m.begin(operation)
                    Thread(target=self.work, args=(operation, m.source, m.revision, m.artifact), daemon=True).start()
                else:
                    raise StateError('Unknown command.')
            except (StateError, KeyError, TypeError) as exc:
                m.notice = str(exc)
            return m.snapshot()

    def work(self, operation, source, revision, artifact):
        try:
            method = getattr(self.backend, operation)
            result = method(artifact) if operation == 'execute' else method(source, revision)
            if not isinstance(result, Result) or result.operation != operation or result.revision != revision:
                raise ValueError('Backend result violates the operation/revision contract.')
        except Exception as exc:
            result = Result(operation, revision, 'backend_failure', f'{type(exc).__name__}: {exc}')
        with self.model.lock:
            self.model.finish(result)

    def state(self):
        with self.model.lock:
            return self.model.snapshot()
