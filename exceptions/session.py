from http import HTTPStatus

from exceptions.base import BaseError


class SessionNotFoundError(BaseError):
    def __init__(
        self,
        message: str = "Session not found",
        status_code: HTTPStatus = HTTPStatus.NOT_FOUND,
    ):
        super().__init__(message=message, status_code=status_code)


class SessionValidationError(BaseError):
    def __init__(
        self,
        message: str = "Invalid session request",
        status_code: HTTPStatus = HTTPStatus.BAD_REQUEST,
    ):
        super().__init__(message=message, status_code=status_code)


class SessionConflictError(BaseError):
    def __init__(
        self,
        message: str = "Session conflict",
        status_code: HTTPStatus = HTTPStatus.CONFLICT,
    ):
        super().__init__(message=message, status_code=status_code)
