"""
Demo E-Commerce — Tests for UserService

Tests registration, authentication, profile management, and address operations.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from services.user_service import (
    register_user,
    authenticate_user,
    get_user_profile,
    update_user_profile,
    add_shipping_address,
    get_user_orders_summary,
    DuplicateEmailError,
    InvalidCredentialsError,
    InactiveAccountError,
    UserNotFoundError,
)


def test_register_user_success():
    user = register_user(
        email="dave@example.com", name="Dave", password="pass123"
    )
    assert user["email"] == "dave@example.com"
    assert "hashed_password" not in user


def test_register_duplicate_email_raises():
    with pytest.raises(DuplicateEmailError):
        register_user(email="alice@example.com", name="Alice2", password="x")


def test_register_missing_fields_raises():
    with pytest.raises(ValueError):
        register_user(email="", name="", password="")


def test_authenticate_valid_credentials():
    user = authenticate_user(email="alice@example.com", password="secret123")
    assert user["id"] == 1


def test_authenticate_wrong_password():
    with pytest.raises(InvalidCredentialsError):
        authenticate_user(email="alice@example.com", password="wrong")


def test_authenticate_nonexistent_user():
    with pytest.raises(InvalidCredentialsError):
        authenticate_user(email="nobody@example.com", password="x")


def test_authenticate_inactive_account():
    """Carol's account is marked inactive — login should fail."""
    with pytest.raises(InactiveAccountError):
        authenticate_user(email="carol@example.com", password="carol789")


def test_get_user_profile_includes_address():
    profile = get_user_profile(1)
    assert profile["id"] == 1
    assert "default_address" in profile
    assert "hashed_password" not in profile


def test_get_user_profile_not_found():
    with pytest.raises(UserNotFoundError):
        get_user_profile(99999)


def test_update_user_profile():
    user = update_user_profile(1, name="Alice Updated")
    assert user["name"] == "Alice Updated"


def test_add_shipping_address():
    address = add_shipping_address(
        user_id=1,
        line1="789 Pine Road",
        city="Capital City",
        state="IL",
        zip_code="62702",
    )
    assert address["user_id"] == 1
    assert address["line1"] == "789 Pine Road"


def test_get_user_orders_summary():
    summary = get_user_orders_summary(1)
    assert "user" in summary
    assert "order_count" in summary
    assert isinstance(summary["orders"], list)


if __name__ == "__main__":
    test_register_user_success()
    test_authenticate_valid_credentials()
    test_get_user_profile_includes_address()
    print("All user service tests passed.")
