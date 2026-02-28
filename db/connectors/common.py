from constants import IDENTIFIER_PATTERN
from exceptions import SourceDbConnectorError


def validate_identifier(value: str, field_name: str) -> str:
    """Validate SQL identifier and return it."""
    if not IDENTIFIER_PATTERN.fullmatch(value):
        msg = f"Invalid {field_name}: {value}"
        raise SourceDbConnectorError(msg)
    return value
