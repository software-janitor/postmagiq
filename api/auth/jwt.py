"""JWT token utilities for authentication."""

import os
from datetime import datetime, timedelta
from uuid import uuid4

from jose import JWTError, jwt

# Configuration - JWT_SECRET is REQUIRED in all environments
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError(
        "JWT_SECRET environment variable is required. "
        "Set it to a secure random string (e.g., openssl rand -hex 32)"
    )
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Valid token types for API access
VALID_ACCESS_TOKEN_TYPES = ("access",)
VALID_PORTAL_TOKEN_TYPES = ("portal_access",)


def create_access_token(
    data: dict,
    token_type: str = "access",
) -> str:
    """Create a JWT access token.

    Args:
        data: Payload data (should include 'sub' for user_id)
        token_type: Token type (default "access", can be "portal_access" for portal tokens)

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update(
        {
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": token_type,
            "jti": str(uuid4()),
        }
    )
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token.

    Args:
        data: Payload data (should include 'sub' for user_id)

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update(
        {
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh",
            "jti": str(uuid4()),
        }
    )
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> dict | None:
    """Verify and decode a JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded payload dict if valid, None if invalid/expired
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None
