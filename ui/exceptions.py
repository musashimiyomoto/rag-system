class ApiClientError(Exception):
    """Raised when chat streaming API call fails."""

    def __init__(self, status_code: int, detail: str):
        """Initialize API client error.

        Args:
            status_code: HTTP status code, or 0 for transport errors.
            detail: Error detail text.

        """
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"{status_code}: {detail}")
