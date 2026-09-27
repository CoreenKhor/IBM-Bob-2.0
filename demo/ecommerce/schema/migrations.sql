-- ============================================================
-- Demo E-Commerce — Database Schema  (SQLite-compatible)
-- Analyzed by the Change Blast Radius Analyzer's ContractChecker
-- ============================================================

-- Users table
-- Blast-radius target: adding 'loyalty_tier' → UserService, OrderService,
-- PaymentService, Checkout frontend, test_user_service.py
CREATE TABLE users (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    email            TEXT    NOT NULL UNIQUE,
    hashed_password  TEXT    NOT NULL,
    name             TEXT    NOT NULL DEFAULT '',
    phone            TEXT             DEFAULT '',
    is_active        INTEGER NOT NULL DEFAULT 1,
    created_at       DATETIME         DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME         DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE addresses (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    line1      TEXT    NOT NULL,
    line2      TEXT             DEFAULT '',
    city       TEXT    NOT NULL,
    state      TEXT    NOT NULL,
    zip_code   TEXT    NOT NULL,
    country    TEXT    NOT NULL DEFAULT 'US',
    is_default INTEGER NOT NULL DEFAULT 0
);

-- Categories and products
CREATE TABLE categories (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE
);

CREATE TABLE products (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    price       REAL    NOT NULL DEFAULT 0.0,
    category_id INTEGER REFERENCES categories(id),
    sku         TEXT    NOT NULL UNIQUE,
    created_at  DATETIME         DEFAULT CURRENT_TIMESTAMP
);

-- Inventory table (separate from products for blast-radius clarity)
CREATE TABLE inventory (
    product_id INTEGER PRIMARY KEY REFERENCES products(id),
    stock      INTEGER NOT NULL DEFAULT 0,
    updated_at DATETIME         DEFAULT CURRENT_TIMESTAMP
);

-- Orders table
-- Blast-radius target: adding 'discount_code' or 'tax_rate' →
-- OrderService.calculate_order_total(), PaymentService.process_payment(),
-- Checkout frontend, test_order_service.py, test_payment_service.py
CREATE TABLE orders (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER NOT NULL REFERENCES users(id),
    status              TEXT    NOT NULL DEFAULT 'pending',
    subtotal            REAL    NOT NULL DEFAULT 0.0,
    tax_amount          REAL    NOT NULL DEFAULT 0.0,
    discount_amount     REAL    NOT NULL DEFAULT 0.0,
    total               REAL    NOT NULL DEFAULT 0.0,
    shipping_address_id INTEGER REFERENCES addresses(id),
    created_at          DATETIME         DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME         DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE order_items (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id   INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity   INTEGER NOT NULL DEFAULT 1,
    unit_price REAL    NOT NULL DEFAULT 0.0
);

-- Payments table
-- Blast-radius target: adding 'payment_method_type' or altering 'status' enum →
-- PaymentService.process_payment(), PaymentController.charge(),
-- Checkout/PaymentForm frontend, test_payment_service.py, test_checkout.py
CREATE TABLE payments (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id                INTEGER NOT NULL UNIQUE REFERENCES orders(id),
    user_id                 INTEGER NOT NULL REFERENCES users(id),
    amount                  REAL    NOT NULL,
    currency                TEXT    NOT NULL DEFAULT 'USD',
    status                  TEXT    NOT NULL DEFAULT 'pending',
    payment_method          TEXT    NOT NULL,
    card_last_four          TEXT             DEFAULT '',
    gateway_transaction_id  TEXT,
    gateway_response        TEXT,    -- JSON blob
    refund_amount           REAL             DEFAULT 0.0,
    created_at              DATETIME         DEFAULT CURRENT_TIMESTAMP,
    updated_at              DATETIME         DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- Indexes
-- ============================================================
CREATE INDEX idx_orders_user_id        ON orders(user_id);
CREATE INDEX idx_orders_status         ON orders(status);
CREATE INDEX idx_order_items_order     ON order_items(order_id);
CREATE INDEX idx_order_items_product   ON order_items(product_id);
CREATE INDEX idx_payments_order        ON payments(order_id);
CREATE INDEX idx_payments_user         ON payments(user_id);
CREATE INDEX idx_payments_status       ON payments(status);
CREATE INDEX idx_addresses_user        ON addresses(user_id);

-- ============================================================
-- Seed data
-- ============================================================
INSERT INTO categories (name, slug) VALUES
  ('Electronics', 'electronics'),
  ('Accessories', 'accessories'),
  ('Peripherals',  'peripherals');

INSERT INTO products (name, price, category_id, sku) VALUES
  ('Wireless Headphones', 79.99,  1, 'WH-1000'),
  ('USB-C Hub',           34.99,  2, 'UC-HUB4'),
  ('Mechanical Keyboard', 119.99, 3, 'MK-TKL'),
  ('Laptop Stand',        49.99,  2, 'LS-ADJ'),
  ('Webcam 1080p',        89.99,  1, 'WC-1080');
