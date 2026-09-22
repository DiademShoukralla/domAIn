import hashlib
import hmac
import secrets
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from uuid import UUID

from domain.config import get_settings


class OAuthStateError(ValueError):
    """Raised when an OAuth state parameter fails verification."""


def _state_secret() -> bytes:
    key = get_settings().token_encryption_key
    if not key:
        raise RuntimeError("TOKEN_ENCRYPTION_KEY is not configured")
    return key.encode()


def create_oauth_state(user_id: UUID, ttl_seconds: int = 600) -> str:
    nonce = secrets.token_urlsafe(16)
    expires_at = int(time.time()) + ttl_seconds
    payload = f"{user_id}:{nonce}:{expires_at}"
    signature = hmac.new(_state_secret(), payload.encode(), hashlib.sha256).hexdigest()
    raw = f"{payload}:{signature}"
    return urlsafe_b64encode(raw.encode()).decode()


def verify_oauth_state(state: str) -> UUID:
    try:
        decoded = urlsafe_b64decode(state.encode()).decode()
        payload, signature = decoded.rsplit(":", 1)
    except (ValueError, UnicodeDecodeError) as exc:
        raise OAuthStateError("Malformed OAuth state") from exc

    expected = hmac.new(_state_secret(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise OAuthStateError("Invalid OAuth state signature")

    try:
        user_id_str, _nonce, expires_at_str = payload.split(":", 2)
        expires_at = int(expires_at_str)
    except ValueError as exc:
        raise OAuthStateError("Malformed OAuth state payload") from exc

    if expires_at < int(time.time()):
        raise OAuthStateError("Expired OAuth state")

    return UUID(user_id_str)
