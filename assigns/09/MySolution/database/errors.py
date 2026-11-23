class ApiError(Exception):
    def __init__(self, status, code, message, **details):
        super().__init__(message)
        self.status = status
        self.body = {"error": {"code": code, "message": message, **details}}


def invalid(message):
    return ApiError(400, "invalid_request", message)
