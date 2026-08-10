"""Create schema and load customers/products/orders CSVs directly into Postgres."""

import csv
import logging
from pathlib import Path

from refund_system.db.connection import get_pg_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = BASE_DIR / "data"
SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def create_schema(conn) -> None:
    schema_sql = SCHEMA_PATH.read_text()
    with conn.cursor() as cur:
        for statement in schema_sql.split(";"):
            statement = statement.strip()
            if statement:
                cur.execute(statement)
    conn.commit()
    logger.info("Schema created.")


def load_customers(conn) -> None:
    with open(DATA_DIR / "customers.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    with conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO customers
               (customer_id, first_name, last_name, email, phone, address_line1,
                address_line2, city, state, zip_code, country, date_joined, customer_tier)
               VALUES (%(customer_id)s, %(first_name)s, %(last_name)s, %(email)s, %(phone)s,
                       %(address_line1)s, %(address_line2)s, %(city)s, %(state)s, %(zip_code)s,
                       %(country)s, %(date_joined)s, %(customer_tier)s)
               ON CONFLICT (customer_id) DO NOTHING""",
            rows,
        )
    conn.commit()
    logger.info("Loaded %d customers.", len(rows))


def load_products(conn) -> None:
    with open(DATA_DIR / "products.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row["fragile"] = row["fragile"] == "True"
        row["restockable"] = row["restockable"] == "True"
    with conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO products
               (product_id, product_name, category, subcategory, price,
                return_window_days, weight_lbs, fragile, restockable)
               VALUES (%(product_id)s, %(product_name)s, %(category)s, %(subcategory)s, %(price)s,
                       %(return_window_days)s, %(weight_lbs)s, %(fragile)s, %(restockable)s)
               ON CONFLICT (product_id) DO NOTHING""",
            rows,
        )
    conn.commit()
    logger.info("Loaded %d products.", len(rows))


def load_orders(conn) -> None:
    with open(DATA_DIR / "orders.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        if row["delivery_date"] == "":
            row["delivery_date"] = None
    with conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO orders
               (order_id, customer_id, product_id, order_date, quantity,
                unit_price, total_amount, status, delivery_date, shipping_address)
               VALUES (%(order_id)s, %(customer_id)s, %(product_id)s, %(order_date)s, %(quantity)s,
                       %(unit_price)s, %(total_amount)s, %(status)s, %(delivery_date)s, %(shipping_address)s)
               ON CONFLICT (order_id) DO NOTHING""",
            rows,
        )
    conn.commit()
    logger.info("Loaded %d orders.", len(rows))


def main() -> None:
    conn = get_pg_connection()
    try:
        create_schema(conn)
        load_customers(conn)
        load_products(conn)
        load_orders(conn)
        logger.info("Database ready.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
