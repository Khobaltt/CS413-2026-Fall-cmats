"""Process-local stream ownership, bounded consumption, and cleanup."""

"""Stream state and inactivity policy."""
from dataclasses import dataclass
from threading import RLock
from time import monotonic
from uuid import uuid4
import solver
from errors import RpcError

@dataclass
class Cursor:
    stream: object
    touched: float

class QueensService:
    def __init__(self, clock=monotonic, lifetime=300, capacity=128):
        self.clock, self.lifetime, self.capacity = clock, lifetime, capacity
        self.active, self.completed = {}, {}
        self.lock = RLock()
        solver.program()  # Parse/type-check once before accepting requests.

    def cleanup(self):
        with self.lock:
            now = self.clock()
            for key, cursor in list(self.active.items()):
                if now - cursor.touched >= self.lifetime:
                    del self.active[key]
            for key, touched in list(self.completed.items()):
                if now - touched >= self.lifetime:
                    del self.completed[key]

    # Exact parameter validation before allocation
    @staticmethod
    def shape(params, keys):
        if not isinstance(params, dict) or set(params) != set(keys):
            raise RpcError(-32602, 'Invalid params')

    @staticmethod
    def integer(value, low, high):
        if type(value) is not int or not low <= value <= high:
            raise RpcError(-32602, 'Invalid params')

    def call(self, method, params):
        with self.lock:
            self.cleanup()
            if method == 'service.health':
                self.shape(params, ())
                return {'status': 'ok', 'version': '1.0'}
            if method == 'queens.open':
                self.shape(params, ('size',))
                size = params['size']
                self.integer(size, 4, 10)
                if len(self.active) >= self.capacity:
                    raise RpcError(-32002, 'Stream capacity reached')
                stream_id = str(uuid4())
                self.active[stream_id] = Cursor(solver.open_stream(size), self.clock())
                return {'stream_id': stream_id, 'size': size}
            if method not in ('queens.next', 'queens.close'):
                raise RpcError(-32601, 'Method not found')
            keys = ('stream_id', 'limit') if method == 'queens.next' else ('stream_id',)
            self.shape(params, keys)
            stream_id = params['stream_id']
            if not isinstance(stream_id, str) or not 1 <= len(stream_id) <= 128:
                raise RpcError(-32602, 'Invalid params')
            if method == 'queens.next':
                self.integer(params['limit'], 1, 32)
            if stream_id not in self.active and stream_id not in self.completed:
                raise RpcError(-32001, 'Stream unavailable')
            if method == 'queens.close':
                self.active.pop(stream_id, None)
                self.completed.pop(stream_id, None)
                return {'closed': True}
            if stream_id in self.completed:
                self.completed[stream_id] = self.clock()
                return {'events': [], 'done': True}
            # Atomic bounded cursor advancement 
            cursor = self.active[stream_id]
            events, done = [], False
            try:
                for _ in range(params['limit']):
                    node = solver.force(cursor.stream)
                    if not node.is_cons:
                        raise RuntimeError('Solver ended without done')
                    event = solver.event_json(node.head)
                    events.append(event)
                    cursor.stream = node.tail  # Reading a tail value does not force it.
                    if event['event'] == 'done':
                        done = True
                        del self.active[stream_id]
                        self.completed[stream_id] = self.clock()
                        if len(self.completed) > 1024:
                            oldest = min(self.completed, key=self.completed.get)
                            del self.completed[oldest]
                        break
                cursor.touched = self.clock()
            except Exception:
                # A partially consumed failing stream cannot safely be retried.
                self.active.pop(stream_id, None)
                raise
            return {'events': events, 'done': done}
