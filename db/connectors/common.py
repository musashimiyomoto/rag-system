from constants import IDENTIFIER_PATTERN
from exceptions import SourceDbConnectorError


def validate_identifier(value: str, field_name: str) -> str:
    """Validate SQL identifier format.

    Args:
        value: Identifier value to validate.
        field_name: Field name used in validation error message.

    Returns:
        Original identifier value if validation succeeds.

    Raises:
        SourceDbConnectorError: If identifier contains unsafe characters.

    """
    if not IDENTIFIER_PATTERN.fullmatch(value):
        msg = f"Invalid {field_name}: {value}"
        raise SourceDbConnectorError(msg)
    return value
