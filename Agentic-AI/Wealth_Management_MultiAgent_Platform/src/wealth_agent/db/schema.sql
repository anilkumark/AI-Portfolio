
CREATE EXTENSION IF NOT EXISTS vector;


CREATE TABLE IF NOT EXISTS advisors (
    advisor_id     INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name           VARCHAR(100) NOT NULL,
    contact_info   VARCHAR(100)
);

-- Clients= This holds each client's basic info and links 
-- them to the advisor managing their account — 
-- the risk_profile field is what the Risk Agent will lean on heavily later.
CREATE TABLE IF NOT EXISTS clients (
    client_id      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name           VARCHAR(100) NOT NULL,
    contact_info   VARCHAR(100),
    advisor_id     INTEGER REFERENCES advisors(advisor_id),
    risk_profile   VARCHAR(50) CHECK (risk_profile IN ('Low', 'Medium', 'High'))
);

-- Accounts. Each client can have multiple accounts (savings, checking, investment) — this is what transactions get attributed to.
-- Every transaction below is tied to one of these, not directly to a client.
CREATE TABLE IF NOT EXISTS accounts (
    account_id     INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    account_type   VARCHAR(50) NOT NULL,
    client_id      INTEGER REFERENCES clients(client_id)
);

-- Assets. Individual investable instruments (stocks, bonds, real estate, etc.) with a current market value — referenced by both transactions and portfolio holdings below
-- Both transactions and portfolio holdings reference these.
CREATE TABLE IF NOT EXISTS assets (
    asset_id       INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name           VARCHAR(100) NOT NULL,
    asset_type     VARCHAR(50),
    current_value  NUMERIC(18,2)
);

-- Portfolios: a client's named collection of holdings, with its own risk
-- level. PortfolioAssets (next) attaches specific assets and allocations to these.
CREATE TABLE IF NOT EXISTS portfolios (
    portfolio_id   INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    client_id      INTEGER REFERENCES clients(client_id),
    name           VARCHAR(100),
    risk_level     VARCHAR(50) CHECK (risk_level IN ('Low', 'Medium', 'High'))
);


-- PortfolioAssets. This is the actual holdings data — which assets a portfolio contains and what percentage allocation each one has. This is what the Stock Position and Risk agents will analyze most directly.
CREATE TABLE IF NOT EXISTS portfolio_assets (
    portfolio_asset_id   INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    portfolio_id         INTEGER REFERENCES portfolios(portfolio_id),
    asset_id             INTEGER REFERENCES assets(asset_id),
    allocation           NUMERIC(5,2)
);

-- Transactions: historical activity log (buy/sell/deposit/withdraw) tied
-- to an account and an asset. What the Data Query Agent reports on for history.
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id   INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    account_id       INTEGER REFERENCES accounts(account_id),
    asset_id         INTEGER REFERENCES assets(asset_id),
    transaction_date TIMESTAMPTZ NOT NULL,
    type             VARCHAR(50) CHECK (type IN ('Buy', 'Sell', 'Deposit', 'Withdraw')),
    amount           NUMERIC(18,2)
);

-- Projections: an estimated future value for a portfolio at a given date.
-- Used in forward-looking client reports, not historical fact.
CREATE TABLE IF NOT EXISTS projections (
    projection_id    INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    portfolio_id      INTEGER REFERENCES portfolios(portfolio_id),
    future_value      NUMERIC(18,2),
    projection_date   TIMESTAMPTZ
);

-- Tracks compliance approval requests: a paused Supervisor conversation
-- waiting on a human advisor to approve or deny risk/mitigation advice.
CREATE TABLE IF NOT EXISTS pending_approvals (
    thread_id       TEXT PRIMARY KEY,
    token           TEXT NOT NULL UNIQUE,
    portfolio_id    INTEGER NOT NULL,
    reason          TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending'
                      CHECK (status IN ('pending', 'approved', 'denied')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at     TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS market_insights_chunks (
    chunk_id         INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    document_id      TEXT NOT NULL,
    document_title   TEXT NOT NULL,
    section          TEXT,
    chunk_type       TEXT NOT NULL CHECK (chunk_type IN ('section','example')),
    content          TEXT NOT NULL,
    embedding        VECTOR(1536),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_market_insights_embedding
    ON market_insights_chunks USING hnsw (embedding vector_cosine_ops);

-- Long-term, cross-session memory: durable notes about a client that persist
-- across conversations, unlike the LangGraph checkpointer which is scoped to
-- a single thread_id and forgotten once that conversation ends.
CREATE TABLE IF NOT EXISTS client_profile_notes (
    note_id      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    client_id    INTEGER NOT NULL REFERENCES clients(client_id),
    note         TEXT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Governance: per-agent token usage for every call, so cost can be
-- attributed to a specific agent rather than only the conversation as a whole.
CREATE TABLE IF NOT EXISTS agent_usage (
    usage_id       INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    thread_id      TEXT NOT NULL,
    agent_name     TEXT NOT NULL,
    input_tokens   INTEGER NOT NULL,
    output_tokens  INTEGER NOT NULL,
    total_tokens   INTEGER NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
