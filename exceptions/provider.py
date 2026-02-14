from http import HTTPStatus

from exceptions.base import BaseError


class ProviderNotFoundError(BaseError):
    def __init__(
        self,
        message: str = "Provider not found",
        status_code: HTTPStatus = HTTPStatus.NOT_FOUND,
    ):
        super().__init__(message=message, status_code=status_code)


class ProviderConflictError(BaseError):
    def __init__(
        self,
        message: str = "Provider conflict",
        status_code: HTTPStatus = HTTPStatus.CONFLICT,
    ):
        super().__init__(message=message, status_code=status_code)


class ProviderValidationError(BaseError):
    def __init__(
        self,
        message: str = "Provider validation error",
        status_code: HTTPStatus = HTTPStatus.UNPROCESSABLE_ENTITY,
    ):
        super().__init__(message=message, status_code=status_code)


class ProviderUpstreamError(BaseError):
    def __init__(
        self,
        message: str = "Provider upstream error",
        status_code: HTTPStatus = HTTPStatus.BAD_GATEWAY,
    ):
        super().__init__(message=message, status_code=status_code)


class ProviderConfigError(BaseError):
    def __init__(
        self,
        message: str = "Provider config error",
        status_code: HTTPStatus = HTTPStatus.INTERNAL_SERVER_ERROR,
    ):
        super().__init__(message=message, status_code=status_code)
