class ApiClientError(Exception):
    """Raised when chat streaming API call fails."""

    def __init__(self, status_code: int, detail: str):
        """Store status and detail for user-facing error rendering."""
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"{status_code}: {detail}")
