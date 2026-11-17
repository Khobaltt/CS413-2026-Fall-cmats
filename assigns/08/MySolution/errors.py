"""Public errors shared by the stream service and RPC envelope handler."""

"""Documented application errors."""
class RpcError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code, self.message = code, message

    def json(self):
        return {'code': self.code, 'message': self.message}
