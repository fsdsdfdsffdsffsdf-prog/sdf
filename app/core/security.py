"""Security, cryptographic operations, Argon2id hashing, and CSRF protection."""

import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from jose import JWTError, jwt
from app.config import get_settings

settings = get_settings()

# Initialize Argon2id password hasher with production parameters
pwd_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MB RAM
    parallelism=4,
    hash_len=32,
    salt_len=16,
)

ALGORITHM = "HS256"
SESSION_COOKIE_NAME = "antigraffiti_session"
CSRF_COOKIE_NAME = "antigraffiti_csrf"


def hash_password(password: str) -> str:
    """Hashes a plain password string using Argon2id."""
    return pwd_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against an Argon2id hash."""
    try:
        return pwd_hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError):
        return False


def verify_secret_token(received_token: Optional[str], expected_token: str) -> bool:
    """Constant-time token verification to prevent timing attacks."""
    if not received_token:
        return False
    return secrets.compare_digest(received_token.strip(), expected_token.strip())


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Creates a signed JWT token with expiration timestamp in UTC."""
    to_encode = data.copy()
    now_utc = datetime.now(timezone.utc)
    if expires_delta:
        expire = now_utc + expires_delta
    else:
        expire = now_utc + timedelta(hours=12)

    to_encode.update({"exp": expire, "iat": now_utc})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodes and validates a JWT token. Returns payload or None if invalid/expired."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def generate_csrf_token() -> str:
    """Generates a cryptographically strong random CSRF token."""
    return secrets.token_urlsafe(32)


def validate_csrf_token(header_token: Optional[str], cookie_token: Optional[str]) -> bool:
    """Validates double-submit CSRF token."""
    if not header_token or not cookie_token:
        return False
    return secrets.compare_digest(header_token, cookie_token)


def sanitize_filename(filename: str) -> str:
    """Removes path traversal components and normalizes filename."""
    base_name = os.path.basename(filename)
    clean_name = "".join(c for c in base_name if c.isalnum() or c in (".", "_", "-"))
    return clean_name or "file.bin"


def is_safe_path(base_dir: Path, target_path: Path) -> bool:
    """Ensures target path does not escape base directory (Path Traversal protection)."""
    try:
        resolved_base = base_dir.resolve()
        resolved_target = target_path.resolve()
        return resolved_base in resolved_target.parents or resolved_base == resolved_target
    except Exception:
        return False
