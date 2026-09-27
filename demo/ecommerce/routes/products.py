"""
Demo E-Commerce Codebase — Product Routes
"""

from flask import Blueprint, jsonify, request
from services.inventory_service import check_stock, add_stock
from models.product import Product

products_bp = Blueprint("products", __name__)


@products_bp.route("/products", methods=["GET"])
def list_products():
    """GET /products — List all products."""
    products = Product.all()
    return jsonify({"products": products})


@products_bp.route("/products/<int:product_id>", methods=["GET"])
def get_product(product_id: int):
    """GET /products/<id> — Get a single product with stock level."""
    product = Product.find(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    stock = check_stock(product_id)
    return jsonify({"product": product, "stock": stock})


@products_bp.route("/products", methods=["POST"])
def create_product():
    """POST /products — Create a new product."""
    data = request.get_json() or {}
    product = Product.create(
        name=data.get("name"),
        price=data.get("price", 0.0),
        category_id=data.get("category_id"),
    )
    add_stock(product_id=product["id"], quantity=data.get("initial_stock", 0))
    return jsonify({"product": product}), 201
