from http import HTTPStatus

from exceptions.base import BaseError


class DocumentTooLargeError(BaseError):
    def __init__(
        self,
        message: str = "Document too large",
        status_code: HTTPStatus = HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
    ):
        super().__init__(message=message, status_code=status_code)


class DocumentNotSupportedError(BaseError):
    def __init__(
        self,
        message: str = "Document not supported",
        status_code: HTTPStatus = HTTPStatus.NOT_ACCEPTABLE,
    ):
        super().__init__(message=message, status_code=status_code)


class DocumentNotFoundError(BaseError):
    def __init__(
        self,
        message: str = "Document not found",
        status_code: HTTPStatus = HTTPStatus.NOT_FOUND,
    ):
        super().__init__(message=message, status_code=status_code)
