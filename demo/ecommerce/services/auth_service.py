"""
Demo E-Commerce Codebase — Auth Service

Handles user authentication, password hashing, and token management.
"""

import hashlib
import hmac
import time

# Fictional secret — demo only
_SECRET = "demo-secret-key-not-for-production"

# In-memory token store (demo only)
_tokens: dict[str, dict] = {}


def hash_password(password: str) -> str:
    """Return a SHA-256 hex digest of the password (demo only — use bcrypt in production)."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """Constant-time comparison of a plaintext password against its hash."""
    return hmac.compare_digest(hash_password(password), hashed)


def create_user(email: str, hashed_password: str) -> dict:
    """Create a new user record (demo stub — returns a fake dict)."""
    from models.user import User
    return User.create(email=email, hashed_password=hashed_password)


def authenticate_user(email: str, password: str) -> str | None:
    """
    Authenticate user by email + password.
    Returns a bearer token string on success, None on failure.
    """
    from models.user import User
    user = User.find_by_email(email)
    if not user:
        return None
    if not verify_password(password, user.get("hashed_password", "")):
        return None
    token = hash_password(f"{email}:{time.time()}")
    _tokens[token] = {"user_id": user["id"], "email": email}
    return token


def verify_token(token: str) -> dict | None:
    """Validate a bearer token and return its payload, or None if invalid."""
    return _tokens.get(token)
