CREATE TABLE IF NOT EXISTS customers (
    customer_id     TEXT PRIMARY KEY,
    first_name      TEXT NOT NULL,
    last_name       TEXT NOT NULL,
    email           TEXT NOT NULL,
    phone           TEXT,
    address_line1   TEXT,
    address_line2   TEXT,
    city            TEXT,
    state           TEXT,
    zip_code        TEXT,
    country         TEXT,
    date_joined     DATE,
    customer_tier   TEXT NOT NULL CHECK (customer_tier IN ('Bronze','Silver','Gold','Platinum'))
);

CREATE TABLE IF NOT EXISTS products (
    product_id          TEXT PRIMARY KEY,
    product_name        TEXT NOT NULL,
    category             TEXT NOT NULL,
    subcategory          TEXT,
    price                NUMERIC(10,2) NOT NULL,
    return_window_days   INTEGER NOT NULL,
    weight_lbs           NUMERIC(6,2),
    fragile              BOOLEAN NOT NULL,
    restockable          BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    order_id         TEXT PRIMARY KEY,
    customer_id      TEXT NOT NULL REFERENCES customers(customer_id),
    product_id       TEXT NOT NULL REFERENCES products(product_id),
    order_date       DATE NOT NULL,
    quantity         INTEGER NOT NULL,
    unit_price       NUMERIC(10,2) NOT NULL,
    total_amount     NUMERIC(10,2) NOT NULL,
    status           TEXT NOT NULL,
    delivery_date    DATE,
    shipping_address TEXT
);

CREATE TABLE IF NOT EXISTS processed_requests (
    request_id       INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id         TEXT NOT NULL REFERENCES orders(order_id),
    customer_id      TEXT NOT NULL REFERENCES customers(customer_id),
    product_id       TEXT NOT NULL REFERENCES products(product_id),
    reason           TEXT NOT NULL,
    description      TEXT,
    status           TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending','approved','denied','escalated')),
    refund_amount    NUMERIC(10,2),
    restocking_fee   NUMERIC(10,2),
    decision_notes   TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_product ON orders(product_id);
CREATE INDEX IF NOT EXISTS idx_requests_status ON processed_requests(status);


CREATE TABLE IF NOT EXISTS policy_chunks (
    chunk_id         INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    document_id      TEXT NOT NULL,
    document_title   TEXT NOT NULL,
    section          TEXT,
    chunk_type       TEXT NOT NULL CHECK (chunk_type IN ('section','example')),
    content          TEXT NOT NULL,
    categories       TEXT[],
    customer_tiers   TEXT[],
    embedding        VECTOR(1536),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);


CREATE INDEX IF NOT EXISTS idx_policy_chunks_embedding
    ON policy_chunks USING hnsw (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS pending_approvals (
    thread_id        TEXT PRIMARY KEY,
    token             TEXT NOT NULL UNIQUE,
    order_id          TEXT NOT NULL,
    refund_amount     NUMERIC(10,2) NOT NULL,
    reason            TEXT NOT NULL,
    status            TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending','approved','denied')),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at       TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS llm_usage (
    usage_id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    thread_id         TEXT NOT NULL,
    model             TEXT NOT NULL,
    prompt_tokens     INTEGER NOT NULL,
    completion_tokens INTEGER NOT NULL,
    cost_usd          NUMERIC(10,6) NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_llm_usage_thread ON llm_usage(thread_id);
