"""Tools for the Validation Agent: lookups and eligibility checks against Postgres."""

from datetime import date

from refund_system.db.connection import get_pg_connection


def get_customer(customer_id: str) -> dict | None:
    """Look up a customer by ID. Returns None if not found."""
    conn = get_pg_connection()
    try:
        row = conn.execute(
            "SELECT * FROM customers WHERE customer_id = %s", (customer_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_order(order_id: str) -> dict | None:
    """Look up an order by ID. Returns None if not found."""
    conn = get_pg_connection()
    try:
        row = conn.execute(
            "SELECT * FROM orders WHERE order_id = %s", (order_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_product(product_id: str) -> dict | None:
    """Look up a product's details (price, return window, fragile/restockable) by ID."""
    conn = get_pg_connection()
    try:
        row = conn.execute(
            "SELECT * FROM products WHERE product_id = %s", (product_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def check_return_eligibility(order_id: str) -> dict:
    """Check whether an order is still within its product's return window."""
    order = get_order(order_id)
    if order is None:
        return {"eligible": False, "reason": "Order not found"}

    product = get_product(order["product_id"])
    if product is None:
        return {"eligible": False, "reason": "Product not found"}

    if order["delivery_date"] is None:
        return {"eligible": False, "reason": "Order not yet delivered"}

    days_since_delivery = (date.today() - order["delivery_date"]).days
    window = product["return_window_days"]

    return {
        "eligible": days_since_delivery <= window,
        "days_since_delivery": days_since_delivery,
        "return_window_days": window,
        "order": order,
        "product": product,
    }


def get_customer_orders(customer_id: str) -> list[dict]:
    """List all orders for a customer, most recent first."""
    conn = get_pg_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM orders WHERE customer_id = %s ORDER BY order_date DESC",
            (customer_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
