import base64
import hashlib

from cryptography.fernet import Fernet

from constants import UTF8
from settings import core_settings


def _build_fernet() -> Fernet:
    """Build fernet.

    Returns:
        Fernet instance derived from the master key.

    """
    return Fernet(
        key=base64.urlsafe_b64encode(
            hashlib.sha256(core_settings.master_key.encode(UTF8)).digest()
        )
    )


def encrypt(data: str) -> str:
    """Encrypt.

    Args:
        data: The data parameter.

    Returns:
        Encrypted value encoded as UTF-8 text.

    """
    return _build_fernet().encrypt(data.encode(UTF8)).decode(UTF8)


def decrypt(encrypted_data: str) -> str:
    """Decrypt.

    Args:
        encrypted_data: The encrypted_data parameter.

    Returns:
        Decrypted UTF-8 value.

    """
    return _build_fernet().decrypt(encrypted_data.encode(UTF8)).decode(UTF8)
