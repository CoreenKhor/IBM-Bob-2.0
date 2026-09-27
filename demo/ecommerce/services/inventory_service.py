"""
Demo E-Commerce — InventoryService

Manages product stock levels and reservation.
Used by OrderService.place_order() and the product catalogue.
"""

from __future__ import annotations
from models.product import Product

# Separate stock store (mirrors an `inventory` table)
_stock: dict[int, int] = {
    101: 50,
    102: 120,
    103: 30,
    104: 75,
    105: 40,
}


class InsufficientStockError(Exception):
    pass


def check_stock(product_id: int) -> int:
    """Return current stock level for a product."""
    return _stock.get(product_id, 0)


def reserve_item(product_id: int, quantity: int) -> int:
    """
    Reserve `quantity` units of product_id.
    Raises InsufficientStockError if stock is insufficient.
    Returns new stock level.
    """
    available = check_stock(product_id)
    if available < quantity:
        product = Product.find(product_id)
        name = product["name"] if product else f"product {product_id}"
        raise InsufficientStockError(
            f"Insufficient stock for {name}: requested {quantity}, available {available}"
        )
    _stock[product_id] = available - quantity
    return _stock[product_id]


def release_item(product_id: int, quantity: int) -> int:
    """Release previously reserved stock back to inventory."""
    _stock[product_id] = _stock.get(product_id, 0) + quantity
    return _stock[product_id]


def add_stock(product_id: int, quantity: int) -> int:
    """Add stock for a product. Returns new stock level."""
    _stock[product_id] = _stock.get(product_id, 0) + quantity
    return _stock[product_id]


def get_low_stock_products(threshold: int = 10) -> list[dict]:
    """Return products with stock at or below the threshold."""
    results = []
    for product_id, qty in _stock.items():
        if qty <= threshold:
            product = Product.find(product_id)
            if product:
                results.append({**product, "stock": qty})
    return results
