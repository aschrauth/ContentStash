"""
Regression check for ContentStash's long-lived personal-device sessions.
"""
from datetime import datetime, timezone
import os

from jose import jwt

os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017/contentstash_test")
os.environ.setdefault("JWT_SECRET", "test-secret-for-token-lifetime-check")

from app.config import settings
from app.utils.auth import create_access_token


def test_default_token_lifetime_is_at_least_one_year():
    token = create_access_token("test-user")
    payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])

    issued_at = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
    expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    lifetime_seconds = int((expires_at - issued_at).total_seconds())

    assert settings.jwt_expires_in >= 365 * 24 * 60 * 60
    assert lifetime_seconds >= 365 * 24 * 60 * 60


if __name__ == "__main__":
    test_default_token_lifetime_is_at_least_one_year()
    print("Auth token lifetime is at least one year.")
