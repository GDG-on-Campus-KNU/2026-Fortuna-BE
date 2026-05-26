from datetime import datetime, timedelta, timezone
from typing import Optional, Any
import bcrypt
import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    """
    Hashes a plain text password using bcrypt.
    """
    # Encodes the password as bytes
    password_bytes = password.encode("utf-8")
    # Generates a random salt
    salt = bcrypt.gensalt()
    # Hashes the password with the salt
    hashed_password = bcrypt.hashpw(password_bytes, salt)
    # Decodes back to string for storage in database
    return hashed_password.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain text password against a bcrypt hashed password.
    """
    try:
        plain_bytes = plain_password.encode("utf-8")
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(plain_bytes, hashed_bytes)
    except Exception:
        return False


def create_access_token(
    data: dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    Generates a secure JSON Web Token (JWT).
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    # Store 'exp' as UTC Unix Timestamp
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    """
    Decodes and validates a JWT access token.
    Returns payload dict if valid, otherwise None.
    """
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.PyJWTError:
        return None
