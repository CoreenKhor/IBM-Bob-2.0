"""
Demo E-Commerce — User Model

Represents the `users` table. Stores customer accounts used during checkout,
order placement, and payment processing.

Relationships:
  - User 1-to-many Orders (via orders.user_id)
  - User 1-to-many Payments (via payments.user_id)
  - User 1-to-many Addresses (via addresses.user_id)
"""

from __future__ import annotations
import hashlib
import hmac
from typing import Optional

# ---------------------------------------------------------------------------
# In-memory store — simulates a relational DB table (demo only)
# ---------------------------------------------------------------------------
_users: dict[int, dict] = {
    1: {
        "id": 1,
        "email": "alice@example.com",
        "hashed_password": hashlib.sha256(b"secret123").hexdigest(),
        "name": "Alice Johnson",
        "phone": "+1-555-0101",
        "is_active": True,
        "created_at": "2024-01-15T10:00:00Z",
    },
    2: {
        "id": 2,
        "email": "bob@example.com",
        "hashed_password": hashlib.sha256(b"password456").hexdigest(),
        "name": "Bob Smith",
        "phone": "+1-555-0102",
        "is_active": True,
        "created_at": "2024-02-20T14:30:00Z",
    },
    3: {
        "id": 3,
        "email": "carol@example.com",
        "hashed_password": hashlib.sha256(b"carol789").hexdigest(),
        "name": "Carol White",
        "phone": "+1-555-0103",
        "is_active": False,   # deactivated account — useful for edge-case tests
        "created_at": "2024-03-05T09:15:00Z",
    },
}

_addresses: dict[int, dict] = {
    1: {
        "id": 1,
        "user_id": 1,
        "line1": "123 Maple Street",
        "line2": "",
        "city": "Springfield",
        "state": "IL",
        "zip_code": "62701",
        "country": "US",
        "is_default": True,
    },
    2: {
        "id": 2,
        "user_id": 2,
        "line1": "456 Oak Avenue",
        "line2": "Apt 7B",
        "city": "Shelbyville",
        "state": "IL",
        "zip_code": "62565",
        "country": "US",
        "is_default": True,
    },
}

_next_user_id = 10
_next_address_id = 10


class User:
    """
    ORM-style model for the `users` table.

    Blast-radius note: changes to this model (e.g. adding a `loyalty_tier`
    field) will cascade to UserService, OrderService.get_order_summary(),
    PaymentService.process_payment(), the checkout frontend, and all auth tests.
    """

    @staticmethod
    def find(user_id: int) -> Optional[dict]:
        """SELECT * FROM users WHERE id = :user_id."""
        return _users.get(user_id)

    @staticmethod
    def find_by_email(email: str) -> Optional[dict]:
        """SELECT * FROM users WHERE email = :email LIMIT 1."""
        return next((u for u in _users.values() if u["email"] == email), None)

    @staticmethod
    def create(email: str, name: str, hashed_password: str, phone: str = "") -> dict:
        """INSERT INTO users (...) VALUES (...) RETURNING *."""
        global _next_user_id
        from datetime import datetime, timezone
        user: dict = {
            "id": _next_user_id,
            "email": email,
            "hashed_password": hashed_password,
            "name": name,
            "phone": phone,
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        _users[_next_user_id] = user
        _next_user_id += 1
        return user

    @staticmethod
    def update(user_id: int, **fields) -> Optional[dict]:
        """UPDATE users SET ... WHERE id = :user_id RETURNING *."""
        user = _users.get(user_id)
        if user is None:
            return None
        ALLOWED = {"name", "phone", "hashed_password", "is_active"}
        for key, val in fields.items():
            if key in ALLOWED:
                user[key] = val
        return user

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        """Constant-time password comparison."""
        return hmac.compare_digest(
            hashlib.sha256(plain.encode()).hexdigest(), hashed
        )

    @staticmethod
    def all(active_only: bool = False) -> list[dict]:
        """SELECT * FROM users [WHERE is_active = TRUE]."""
        rows = list(_users.values())
        return [u for u in rows if u["is_active"]] if active_only else rows


class Address:
    """ORM-style model for the `addresses` table."""

    @staticmethod
    def find(address_id: int) -> Optional[dict]:
        return _addresses.get(address_id)

    @staticmethod
    def find_by_user(user_id: int) -> list[dict]:
        """SELECT * FROM addresses WHERE user_id = :user_id."""
        return [a for a in _addresses.values() if a["user_id"] == user_id]

    @staticmethod
    def get_default(user_id: int) -> Optional[dict]:
        """Return the default shipping address for a user."""
        return next(
            (a for a in _addresses.values()
             if a["user_id"] == user_id and a["is_default"]),
            None,
        )

    @staticmethod
    def create(user_id: int, line1: str, city: str, state: str,
               zip_code: str, country: str = "US", line2: str = "",
               is_default: bool = False) -> dict:
        global _next_address_id
        addr: dict = {
            "id": _next_address_id,
            "user_id": user_id,
            "line1": line1,
            "line2": line2,
            "city": city,
            "state": state,
            "zip_code": zip_code,
            "country": country,
            "is_default": is_default,
        }
        _addresses[_next_address_id] = addr
        _next_address_id += 1
        return addr
