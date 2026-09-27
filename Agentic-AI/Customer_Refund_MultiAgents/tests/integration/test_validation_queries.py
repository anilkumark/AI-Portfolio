"""Integration tests for validation/queries.py — hit the real Postgres database.

Requires the project's Docker Postgres container to be running with seeded data
(python src/refund_system/db/init_db.py already run).
"""

from refund_system.validation import queries

KNOWN_CUSTOMER_ID = "MARWIL0205"
KNOWN_ORDER_ID = "ORD000004"


def test_get_customer_found():
    customer = queries.get_customer(KNOWN_CUSTOMER_ID)
    assert customer is not None
    assert customer["customer_id"] == KNOWN_CUSTOMER_ID
    assert customer["customer_tier"] in ("Bronze", "Silver", "Gold", "Platinum")


def test_get_customer_not_found():
    assert queries.get_customer("DOES_NOT_EXIST_0000") is None


def test_get_order_found():
    order = queries.get_order(KNOWN_ORDER_ID)
    assert order is not None
    assert order["order_id"] == KNOWN_ORDER_ID


def test_get_order_not_found():
    assert queries.get_order("ORD999999") is None


def test_check_return_eligibility_order_not_found():
    result = queries.check_return_eligibility("ORD999999")
    assert result["eligible"] is False
    assert result["reason"] == "Order not found"


def test_get_customer_orders_returns_list():
    orders = queries.get_customer_orders(KNOWN_CUSTOMER_ID)
    assert isinstance(orders, list)
    assert all(order["customer_id"] == KNOWN_CUSTOMER_ID for order in orders)
