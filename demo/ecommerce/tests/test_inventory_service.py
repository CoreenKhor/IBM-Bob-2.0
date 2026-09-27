"""
Demo E-Commerce — Unit Tests for Inventory Service
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.inventory_service import check_stock, reserve_item, add_stock, InsufficientStockError
import pytest


def test_add_stock_increases_level():
    """add_stock increases the stock level by the specified amount."""
    before = check_stock(102)
    add_stock(102, 10)
    assert check_stock(102) == before + 10


def test_reserve_item_reduces_stock():
    """reserve_item reduces stock by the requested quantity and returns new level."""
    before = check_stock(102)
    new_level = reserve_item(102, 3)
    assert new_level == before - 3
    assert check_stock(102) == before - 3


def test_reserve_item_raises_when_insufficient():
    """reserve_item raises InsufficientStockError when stock is insufficient."""
    before = check_stock(103)
    with pytest.raises(InsufficientStockError):
        reserve_item(103, before + 1000)


if __name__ == "__main__":
    test_add_stock_increases_level()
    test_reserve_item_reduces_stock()
    test_reserve_item_raises_when_insufficient()
    print("All inventory service tests passed.")
