"""
Demo E-Commerce — UserService

Handles user registration, authentication, profile management, and
address operations. Used by the checkout flow and order placement.

Blast-radius note: changes to `register_user` or `get_user_profile`
will cascade to:
  routes/users.py (direct callers)
  services/order_service.py.place_order() (reads user + address)
  Checkout frontend (uses profile for pre-fill)
  test_user_service.py, test_checkout.py
"""

from __future__ import annotations
import hashlib
from typing import Optional

from models.user import User, Address


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class UserNotFoundError(Exception):
    pass


class DuplicateEmailError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class InactiveAccountError(Exception):
    pass


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------

def register_user(email: str, name: str, password: str, phone: str = "") -> dict:
    """
    Register a new customer account.

    Validates that the email is not already in use, hashes the password,
    and persists the user record.

    Called by: routes/users.py → POST /users/register
    Calls:     User.find_by_email(), User.create()
    """
    if not email or not name or not password:
        raise ValueError("email, name, and password are required")

    existing = User.find_by_email(email)
    if existing:
        raise DuplicateEmailError(f"Email already registered: {email}")

    hashed = hashlib.sha256(password.encode()).hexdigest()
    user = User.create(email=email, name=name, hashed_password=hashed, phone=phone)
    return _safe_user(user)


def authenticate_user(email: str, password: str) -> dict:
    """
    Verify email + password and return the user record.

    Raises InvalidCredentialsError if credentials are wrong.
    Raises InactiveAccountError if the account is deactivated.

    Called by: routes/users.py → POST /users/login
    """
    user = User.find_by_email(email)
    if user is None or not User.verify_password(password, user["hashed_password"]):
        raise InvalidCredentialsError("Invalid email or password")

    if not user.get("is_active", True):
        raise InactiveAccountError("Account is deactivated")

    return _safe_user(user)


def get_user_profile(user_id: int) -> dict:
    """
    Return a user's profile with their default shipping address.

    Called by: routes/users.py → GET /users/<id>
               services/order_service.place_order() (reads shipping address)
               Checkout frontend (pre-fills address fields)
    """
    user = User.find(user_id)
    if user is None:
        raise UserNotFoundError(f"User {user_id} not found")

    profile = _safe_user(user)
    profile["default_address"] = Address.get_default(user_id)
    profile["addresses"] = Address.find_by_user(user_id)
    return profile


def update_user_profile(user_id: int, name: Optional[str] = None,
                         phone: Optional[str] = None) -> dict:
    """
    Update mutable profile fields for a user.

    Called by: routes/users.py → PATCH /users/<id>
    """
    user = User.find(user_id)
    if user is None:
        raise UserNotFoundError(f"User {user_id} not found")

    updates: dict = {}
    if name is not None:
        updates["name"] = name
    if phone is not None:
        updates["phone"] = phone

    updated = User.update(user_id, **updates)
    return _safe_user(updated)  # type: ignore[arg-type]


def add_shipping_address(user_id: int, line1: str, city: str, state: str,
                          zip_code: str, country: str = "US", line2: str = "",
                          is_default: bool = False) -> dict:
    """
    Add a new shipping address for a user.

    Called by: routes/users.py → POST /users/<id>/addresses
               Checkout frontend → "Add new address" flow
    """
    user = User.find(user_id)
    if user is None:
        raise UserNotFoundError(f"User {user_id} not found")

    return Address.create(
        user_id=user_id, line1=line1, city=city, state=state,
        zip_code=zip_code, country=country, line2=line2, is_default=is_default,
    )


def get_user_orders_summary(user_id: int) -> dict:
    """
    Return user profile plus a summary of their orders.

    Called by: routes/users.py → GET /users/<id>/orders
               OrderPage frontend (loads order history for the user)
    """
    from services.order_service import get_orders_for_user
    user = User.find(user_id)
    if user is None:
        raise UserNotFoundError(f"User {user_id} not found")

    orders = get_orders_for_user(user_id)
    return {
        "user": _safe_user(user),
        "order_count": len(orders),
        "orders": orders,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _safe_user(user: dict) -> dict:
    """Return user dict without the hashed_password field."""
    return {k: v for k, v in user.items() if k != "hashed_password"}
