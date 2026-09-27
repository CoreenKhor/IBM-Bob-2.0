"""
Demo E-Commerce — Product & Category Models

Represents the `products` and `categories` tables.
"""

from __future__ import annotations
from typing import Optional

_categories: dict[int, dict] = {
    1: {"id": 1, "name": "Electronics",  "slug": "electronics"},
    2: {"id": 2, "name": "Accessories",  "slug": "accessories"},
    3: {"id": 3, "name": "Peripherals",  "slug": "peripherals"},
}

_products: dict[int, dict] = {
    101: {"id": 101, "name": "Wireless Headphones",  "price": 79.99,  "category_id": 1, "sku": "WH-1000", "stock": 50},
    102: {"id": 102, "name": "USB-C Hub",             "price": 34.99,  "category_id": 2, "sku": "UC-HUB4", "stock": 120},
    103: {"id": 103, "name": "Mechanical Keyboard",   "price": 119.99, "category_id": 3, "sku": "MK-TKL",  "stock": 30},
    104: {"id": 104, "name": "Laptop Stand",          "price": 49.99,  "category_id": 2, "sku": "LS-ADJ",  "stock": 75},
    105: {"id": 105, "name": "Webcam 1080p",          "price": 89.99,  "category_id": 1, "sku": "WC-1080", "stock": 40},
}

_next_product_id = 200


class Product:
    """ORM-style model for the `products` table."""

    @staticmethod
    def find(product_id: int) -> Optional[dict]:
        return _products.get(product_id)

    @staticmethod
    def find_by_sku(sku: str) -> Optional[dict]:
        return next((p for p in _products.values() if p["sku"] == sku), None)

    @staticmethod
    def all(category_id: Optional[int] = None) -> list[dict]:
        rows = list(_products.values())
        if category_id is not None:
            rows = [p for p in rows if p["category_id"] == category_id]
        return rows

    @staticmethod
    def create(name: str, price: float, category_id: int, sku: str,
               stock: int = 0) -> dict:
        global _next_product_id
        product: dict = {
            "id": _next_product_id,
            "name": name,
            "price": price,
            "category_id": category_id,
            "sku": sku,
            "stock": stock,
        }
        _products[_next_product_id] = product
        _next_product_id += 1
        return product

    @staticmethod
    def update_stock(product_id: int, delta: int) -> Optional[dict]:
        """UPDATE products SET stock = stock + delta WHERE id = :product_id."""
        product = _products.get(product_id)
        if product is None:
            return None
        product["stock"] = max(0, product["stock"] + delta)
        return product


class Category:
    """ORM-style model for the `categories` table."""

    @staticmethod
    def find(category_id: int) -> Optional[dict]:
        return _categories.get(category_id)

    @staticmethod
    def all() -> list[dict]:
        return list(_categories.values())
