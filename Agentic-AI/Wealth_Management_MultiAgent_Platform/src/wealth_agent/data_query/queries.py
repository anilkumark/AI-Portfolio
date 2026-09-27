"""Fixed SQL query functions for the Data Query Agent — real facts only,
no LLM-generated SQL. Same pattern as the refund project's validation/queries.py."""

"""Purpose: looks up one client's basic info by ID — the foundation lookup everything else builds on"""
from wealth_agent.db.connection import get_pg_connection


def get_client(client_id: int) -> dict | None:
    # Looks up one client's basic info (name, contact, advisor, risk profile).
    conn = get_pg_connection()
    try:
        row = conn.execute(
            "SELECT * FROM clients WHERE client_id = %s", (client_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


"""get_client_accounts. Lists all accounts belonging to a client — needed before we can look up their portfolios or transactions"""


def get_client_accounts(client_id: int) -> list[dict]:
    # Lists every account belonging to a client.
    conn = get_pg_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM accounts WHERE client_id = %s", (client_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


""" get_client_portfolios. Lists a client's portfolios"""


def get_client_portfolios(client_id: int) -> list[dict]:
    # Lists every portfolio belonging to a client.
    conn = get_pg_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM portfolios WHERE client_id = %s", (client_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


""" get_portfolio_holdings. This one joins portfolio_assets with assets so the result includes the actual asset name/type/value, not just raw IDs — this is the core data the Stock Position and Risk agents will analyze"""


def get_portfolio_holdings(portfolio_id: int) -> list[dict]:
    # Lists a portfolio's holdings with real asset details (name, type, value, allocation %).
    conn = get_pg_connection()
    try:
        rows = conn.execute(
            """SELECT pa.allocation, a.asset_id, a.name, a.asset_type, a.current_value
               FROM portfolio_assets pa
               JOIN assets a ON a.asset_id = pa.asset_id
               WHERE pa.portfolio_id = %s""",
            (portfolio_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


"""get_client_transactions. Transaction history for a client — since transactions link to accounts, not directly to clients, this joins through accounts and also brings in the asset name for readability"""


def get_client_transactions(client_id: int, limit: int = 20) -> list[dict]:
    # Lists a client's recent transactions (most recent first), across all their accounts.
    conn = get_pg_connection()
    try:
        rows = conn.execute(
            """SELECT t.transaction_id, t.transaction_date, t.type, t.amount,
                      a.name AS asset_name, acc.account_type
               FROM transactions t
               JOIN accounts acc ON acc.account_id = t.account_id
               JOIN assets a ON a.asset_id = t.asset_id
               WHERE acc.client_id = %s
               ORDER BY t.transaction_date DESC
               LIMIT %s""",
            (client_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
