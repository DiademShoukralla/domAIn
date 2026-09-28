import os

os.environ.setdefault(
    "TOKEN_ENCRYPTION_KEY",
    "J1DKacOrXJ8dI6ByJL5wpw73UYWIjwpaQX6BFzxuBIw=",
)
os.environ.setdefault("BOOTSTRAP_API_KEY", "test-api-key")
os.environ.setdefault("SESSION_SECRET", "test-session-secret")
os.environ.setdefault("WS_ALLOWED_ORIGINS", "http://test")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://domain:domain@localhost:5432/domain",
)
