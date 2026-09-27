"""Create schema and load synthetic wealth-management data via Faker.

Own clean version of the reference project's data generator — same idea
(fake advisors/clients/portfolios), but targets Postgres via psycopg
instead of SQL Server via pyodbc.
"""

import logging
import random
from datetime import datetime, timedelta
from pathlib import Path

from faker import Faker

from wealth_agent.db.connection import get_pg_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
fake = Faker()

""" Postgres. Purpose: runs schema.sql against the database, splitting on ; since psycopg doesn't reliably handle multiple statements in one call."""


def create_schema(conn) -> None:
    # Runs every CREATE TABLE statement in schema.sql, one at a time.
    schema_sql = SCHEMA_PATH.read_text()
    with conn.cursor() as cur:
        for statement in schema_sql.split(";"):
            statement = statement.strip()
            if statement:
                cur.execute(statement)
    conn.commit()
    logger.info("Schema created.")


"""load_advisors. Generates fake advisor names/contact info and inserts them — the first table, since everything else eventually links back to an advisor through a client."""


def load_advisors(conn, count: int = 50) -> None:
    # Generates `count` fake advisors (name + phone) and inserts them.
    rows = [
        {"name": fake.name(), "contact_info": fake.phone_number()} for _ in range(count)
    ]
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO advisors (name, contact_info) VALUES (%(name)s, %(contact_info)s)",
            rows,
        )
    conn.commit()
    logger.info("Loaded %d advisors.", count)


"""load_clients. Each fake client is linked to a random advisor and given a risk profile — the field the Risk Agent will lean on later."""


def load_clients(conn, count: int = 300, num_advisors: int = 50) -> None:
    # Generates `count` fake clients, each linked to a random advisor.
    rows = [
        {
            "name": fake.name(),
            "contact_info": fake.phone_number(),
            "advisor_id": random.randint(1, num_advisors),
            "risk_profile": random.choice(["Low", "Medium", "High"]),
        }
        for _ in range(count)
    ]
    with conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO clients (name, contact_info, advisor_id, risk_profile)
               VALUES (%(name)s, %(contact_info)s, %(advisor_id)s, %(risk_profile)s)""",
            rows,
        )
    conn.commit()
    logger.info("Loaded %d clients.", count)


def load_accounts(conn, count: int = 500, num_clients: int = 300) -> None:
    # Generates `count` fake accounts, each linked to a random client.
    rows = [
        {
            "account_type": random.choice(["Savings", "Checking", "Investment"]),
            "client_id": random.randint(1, num_clients),
        }
        for _ in range(count)
    ]
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO accounts (account_type, client_id) VALUES (%(account_type)s, %(client_id)s)",
            rows,
        )
    conn.commit()
    logger.info("Loaded %d accounts.", count)


def load_assets(conn, count: int = 200) -> None:
    # Generates `count` fake assets (stocks/bonds/etc.) with a current value.
    rows = [
        {
            "name": fake.company(),
            "asset_type": random.choice(
                ["Stock", "Bond", "Real Estate", "Commodity", "Cash"]
            ),
            "current_value": round(random.uniform(10, 1000), 2),
        }
        for _ in range(count)
    ]
    with conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO assets (name, asset_type, current_value)
               VALUES (%(name)s, %(asset_type)s, %(current_value)s)""",
            rows,
        )
    conn.commit()
    logger.info("Loaded %d assets.", count)


def load_portfolios(conn, count: int = 300, num_clients: int = 300) -> None:
    # Generates `count` fake portfolios, each linked to a random client.
    rows = [
        {
            "client_id": random.randint(1, num_clients),
            "name": f"Portfolio {fake.word().capitalize()}",
            "risk_level": random.choice(["Low", "Medium", "High"]),
        }
        for _ in range(count)
    ]
    with conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO portfolios (client_id, name, risk_level)
               VALUES (%(client_id)s, %(name)s, %(risk_level)s)""",
            rows,
        )
    conn.commit()
    logger.info("Loaded %d portfolios.", count)


def load_portfolio_assets(
    conn, num_portfolios: int = 300, num_assets: int = 200
) -> None:
    # Gives each portfolio 2-6 random holdings whose allocations sum to 100%,
    # instead of independent random percentages that don't add up to a real portfolio.
    rows = []
    for portfolio_id in range(1, num_portfolios + 1):
        asset_ids = random.sample(range(1, num_assets + 1), random.randint(2, 6))
        weights = [random.random() for _ in asset_ids]
        total_weight = sum(weights)
        rows.extend(
            {
                "portfolio_id": portfolio_id,
                "asset_id": asset_id,
                "allocation": round(weight / total_weight * 100, 2),
            }
            for asset_id, weight in zip(asset_ids, weights)
        )
    with conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO portfolio_assets (portfolio_id, asset_id, allocation)
               VALUES (%(portfolio_id)s, %(asset_id)s, %(allocation)s)""",
            rows,
        )
    conn.commit()
    logger.info("Loaded %d portfolio assets.", len(rows))


""" load_transactions. Fake buy/sell/deposit/withdraw activity spread over the last 4 years."""


def load_transactions(
    conn, count: int = 2000, num_accounts: int = 500, num_assets: int = 200
) -> None:
    # Generates `count` fake transactions dated randomly over the last 4 years.
    start_date = datetime(2021, 1, 1)
    rows = [
        {
            "account_id": random.randint(1, num_accounts),
            "asset_id": random.randint(1, num_assets),
            "transaction_date": start_date + timedelta(days=random.randint(1, 365 * 4)),
            "type": random.choice(["Buy", "Sell", "Deposit", "Withdraw"]),
            "amount": round(random.uniform(100, 10000), 2),
        }
        for _ in range(count)
    ]
    with conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO transactions (account_id, asset_id, transaction_date, type, amount)
               VALUES (%(account_id)s, %(asset_id)s, %(transaction_date)s, %(type)s, %(amount)s)""",
            rows,
        )
    conn.commit()
    logger.info("Loaded %d transactions.", count)


"""load_projections. Fake future-value estimates for random portfolios"""


def load_projections(conn, count: int = 400, num_portfolios: int = 300) -> None:
    # Generates `count` fake future-value projections, dated up to 10 years out.
    start_date = datetime(2021, 1, 1)
    rows = [
        {
            "portfolio_id": random.randint(1, num_portfolios),
            "future_value": round(random.uniform(1000, 100000), 2),
            "projection_date": start_date + timedelta(days=random.randint(1, 365 * 10)),
        }
        for _ in range(count)
    ]
    with conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO projections (portfolio_id, future_value, projection_date)
               VALUES (%(portfolio_id)s, %(future_value)s, %(projection_date)s)""",
            rows,
        )
    conn.commit()
    logger.info("Loaded %d projections.", count)


"""main(), which runs everything in the right order (parents before children, so foreign keys always point at something real)"""


def main() -> None:
    # Creates the schema, then loads synthetic data in dependency order
    # (advisors before clients, clients before accounts/portfolios, etc.)
    conn = get_pg_connection()
    try:
        create_schema(conn)
        load_advisors(conn, count=50)
        load_clients(conn, count=300, num_advisors=50)
        load_accounts(conn, count=500, num_clients=300)
        load_assets(conn, count=200)
        load_portfolios(conn, count=300, num_clients=300)
        load_portfolio_assets(conn, num_portfolios=300, num_assets=200)
        load_transactions(conn, count=2000, num_accounts=500, num_assets=200)
        load_projections(conn, count=400, num_portfolios=300)
        logger.info("Database ready.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
