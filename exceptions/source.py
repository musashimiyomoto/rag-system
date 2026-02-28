from http import HTTPStatus

from exceptions.base import BaseError


class SourceTooLargeError(BaseError):
    def __init__(
        self,
        message: str = "Source too large",
        status_code: HTTPStatus = HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
    ):
        super().__init__(message=message, status_code=status_code)


class SourceNotSupportedError(BaseError):
    def __init__(
        self,
        message: str = "Source not supported",
        status_code: HTTPStatus = HTTPStatus.NOT_ACCEPTABLE,
    ):
        super().__init__(message=message, status_code=status_code)


class SourceNotFoundError(BaseError):
    def __init__(
        self,
        message: str = "Source not found",
        status_code: HTTPStatus = HTTPStatus.NOT_FOUND,
    ):
        super().__init__(message=message, status_code=status_code)


class SourceConflictError(BaseError):
    def __init__(
        self,
        message: str = "Source conflict",
        status_code: HTTPStatus = HTTPStatus.CONFLICT,
    ):
        super().__init__(message=message, status_code=status_code)


class SourceValidationError(BaseError):
    def __init__(
        self,
        message: str = "Source validation failed",
        status_code: HTTPStatus = HTTPStatus.BAD_REQUEST,
    ):
        super().__init__(message=message, status_code=status_code)


class SourceConnectionError(BaseError):
    def __init__(
        self,
        message: str = "Source connection failed",
        status_code: HTTPStatus = HTTPStatus.BAD_GATEWAY,
    ):
        super().__init__(message=message, status_code=status_code)


class SourceDbConnectorError(BaseError):
    def __init__(
        self,
        message: str = "Source DB connector error",
        status_code: HTTPStatus = HTTPStatus.BAD_GATEWAY,
    ):
        super().__init__(message=message, status_code=status_code)
