from cryptography.fernet import Fernet, InvalidToken

from domain.config import get_settings


def _get_fernet() -> Fernet:
    key = get_settings().token_encryption_key
    if not key:
        raise RuntimeError("TOKEN_ENCRYPTION_KEY is not configured")
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_token(value: str) -> str:
    return _get_fernet().encrypt(value.encode()).decode()


def decrypt_token(value: str) -> str:
    try:
        return _get_fernet().decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Failed to decrypt token") from exc
