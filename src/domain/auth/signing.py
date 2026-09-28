import hashlib
import hmac
import secrets
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode

from domain.config import get_settings


class SignedValueError(ValueError):
    """Raised when a signed value fails verification."""


def _signing_secret() -> bytes:
    secret = get_settings().session_secret
    if not secret:
        raise RuntimeError("SESSION_SECRET is not configured")
    return secret.encode()


def sign_payload(payload: str) -> str:
    signature = hmac.new(_signing_secret(), payload.encode(), hashlib.sha256).hexdigest()
    raw = f"{payload}:{signature}"
    return urlsafe_b64encode(raw.encode()).decode()


def verify_signed_payload(signed: str) -> str:
    try:
        decoded = urlsafe_b64decode(signed.encode()).decode()
        payload, signature = decoded.rsplit(":", 1)
    except (ValueError, UnicodeDecodeError) as exc:
        raise SignedValueError("Malformed signed value") from exc

    expected = hmac.new(_signing_secret(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise SignedValueError("Invalid signed value signature")
    return payload


def create_login_oauth_state(ttl_seconds: int = 600) -> str:
    nonce = secrets.token_urlsafe(16)
    expires_at = int(time.time()) + ttl_seconds
    return sign_payload(f"login:{nonce}:{expires_at}")


def verify_login_oauth_state(state: str) -> None:
    payload = verify_signed_payload(state)
    try:
        kind, _nonce, expires_at_str = payload.split(":", 2)
        expires_at = int(expires_at_str)
    except ValueError as exc:
        raise SignedValueError("Malformed login OAuth state") from exc
    if kind != "login":
        raise SignedValueError("Unexpected login OAuth state kind")
    if expires_at < int(time.time()):
        raise SignedValueError("Expired login OAuth state")


def create_auth_display_value(login: str, ttl_seconds: int = 300) -> str:
    expires_at = int(time.time()) + ttl_seconds
    return sign_payload(f"display:{login}:{expires_at}")


def verify_auth_display_value(signed: str) -> str:
    payload = verify_signed_payload(signed)
    try:
        kind, login, expires_at_str = payload.split(":", 2)
        expires_at = int(expires_at_str)
    except ValueError as exc:
        raise SignedValueError("Malformed auth display value") from exc
    if kind != "display":
        raise SignedValueError("Unexpected auth display value kind")
    if expires_at < int(time.time()):
        raise SignedValueError("Expired auth display value")
    return login
