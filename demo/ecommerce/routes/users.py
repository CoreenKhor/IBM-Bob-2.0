"""
Demo E-Commerce — User Routes

HTTP surface for user registration, authentication, profile, and address management.
"""

from flask import Blueprint, request, jsonify
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

users_bp = Blueprint("users", __name__)


@users_bp.route("/users/register", methods=["POST"])
def register():
    """POST /users/register — Create a new customer account."""
    data = request.get_json(silent=True) or {}
    try:
        user = register_user(
            email=data.get("email", ""),
            name=data.get("name", ""),
            password=data.get("password", ""),
            phone=data.get("phone", ""),
        )
        return jsonify({"user": user, "message": "Account created"}), 201
    except DuplicateEmailError as exc:
        return jsonify({"error": str(exc), "code": "duplicate_email"}), 409
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@users_bp.route("/users/login", methods=["POST"])
def login():
    """POST /users/login — Authenticate and return user record."""
    data = request.get_json(silent=True) or {}
    try:
        user = authenticate_user(
            email=data.get("email", ""),
            password=data.get("password", ""),
        )
        return jsonify({"user": user, "message": "Login successful"}), 200
    except (InvalidCredentialsError, InactiveAccountError) as exc:
        return jsonify({"error": str(exc), "code": "auth_error"}), 401


@users_bp.route("/users/<int:user_id>", methods=["GET"])
def get_profile(user_id: int):
    """GET /users/<id> — Return user profile with default address."""
    try:
        profile = get_user_profile(user_id)
        return jsonify({"user": profile}), 200
    except UserNotFoundError as exc:
        return jsonify({"error": str(exc)}), 404


@users_bp.route("/users/<int:user_id>", methods=["PATCH"])
def update_profile(user_id: int):
    """PATCH /users/<id> — Update name or phone."""
    data = request.get_json(silent=True) or {}
    try:
        user = update_user_profile(
            user_id,
            name=data.get("name"),
            phone=data.get("phone"),
        )
        return jsonify({"user": user}), 200
    except UserNotFoundError as exc:
        return jsonify({"error": str(exc)}), 404


@users_bp.route("/users/<int:user_id>/addresses", methods=["POST"])
def add_address(user_id: int):
    """POST /users/<id>/addresses — Add a shipping address."""
    data = request.get_json(silent=True) or {}
    try:
        address = add_shipping_address(
            user_id=user_id,
            line1=data.get("line1", ""),
            city=data.get("city", ""),
            state=data.get("state", ""),
            zip_code=data.get("zip_code", ""),
            country=data.get("country", "US"),
            line2=data.get("line2", ""),
            is_default=data.get("is_default", False),
        )
        return jsonify({"address": address}), 201
    except (UserNotFoundError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400


@users_bp.route("/users/<int:user_id>/orders", methods=["GET"])
def user_orders(user_id: int):
    """GET /users/<id>/orders — Return order history summary for a user."""
    try:
        summary = get_user_orders_summary(user_id)
        return jsonify(summary), 200
    except UserNotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
