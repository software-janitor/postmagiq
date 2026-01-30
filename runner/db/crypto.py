"""Database-level encryption using PostgreSQL pgcrypto.

Provides functions to encrypt/decrypt sensitive data using pgp_sym_encrypt/decrypt.
The encryption key is read from SOCIAL_ENCRYPTION_KEY environment variable.
"""

import os
from typing import Optional

from sqlalchemy import text
from sqlmodel import Session

# Encryption key for social tokens - MUST be set in production
SOCIAL_ENCRYPTION_KEY = os.getenv("SOCIAL_ENCRYPTION_KEY", "dev-key-change-in-production")


def encrypt_token(session: Session, plaintext: str) -> bytes:
    """Encrypt a token using pgcrypto.

    Args:
        session: Database session
        plaintext: Token to encrypt

    Returns:
        Encrypted bytes
    """
    result = session.execute(
        text("SELECT pgp_sym_encrypt(:plaintext, :key)"),
        {"plaintext": plaintext, "key": SOCIAL_ENCRYPTION_KEY},
    )
    return result.scalar()


def decrypt_token(session: Session, ciphertext: bytes) -> Optional[str]:
    """Decrypt a token using pgcrypto.

    Args:
        session: Database session
        ciphertext: Encrypted token bytes

    Returns:
        Decrypted token string, or None if ciphertext is None
    """
    if ciphertext is None:
        return None

    result = session.execute(
        text("SELECT pgp_sym_decrypt(:ciphertext, :key)"),
        {"ciphertext": ciphertext, "key": SOCIAL_ENCRYPTION_KEY},
    )
    decrypted = result.scalar()
    return decrypted.decode() if isinstance(decrypted, bytes) else decrypted
