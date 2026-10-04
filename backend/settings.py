import os
import secrets


def jwt_secret() -> str:
    value = os.environ.get("JWT_SECRET", "")
    if len(value.encode()) >= 32 and value != "dev-insecure-secret-change-me-in-production-please":
        return value
    if os.environ.get("APP_ENV") == "test":
        return secrets.token_hex(32)
    raise RuntimeError("Set JWT_SECRET to a randomly generated secret of at least 32 bytes")


JWT_SECRET = jwt_secret()
MAX_SOURCE_BYTES = 128 * 1024
MAX_UPLOAD_BYTES = 8 * 1024 * 1024
