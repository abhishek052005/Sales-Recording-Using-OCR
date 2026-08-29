-- ============================================================
-- Supabase PostgreSQL Database Schema for OCR Backend
-- ============================================================

-- 1. USERS TABLE
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- 2. INVOICES TABLE
CREATE TABLE IF NOT EXISTS invoices (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    invoice_number VARCHAR(100),
    invoice_date VARCHAR(20),
    user_id INT REFERENCES users(id) ON DELETE SET NULL,
    vendor_name VARCHAR(255),
    vendor_gstin VARCHAR(50),
    vendor_address TEXT,
    vendor_phone VARCHAR(50),
    vendor_email VARCHAR(255),
    customer_name VARCHAR(255),
    customer_gstin VARCHAR(50),
    customer_address TEXT,
    customer_phone VARCHAR(50),
    customer_email VARCHAR(255),
    subtotal DOUBLE PRECISION,
    tax DOUBLE PRECISION,
    total DOUBLE PRECISION,
    currency VARCHAR(10),
    raw_ocr_text TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_filename UNIQUE (user_id, filename)
);

CREATE INDEX IF NOT EXISTS idx_invoices_user_id ON invoices(user_id);
CREATE INDEX IF NOT EXISTS idx_invoices_created_at ON invoices(created_at DESC);

-- 3. INVOICE ITEMS TABLE
CREATE TABLE IF NOT EXISTS invoice_items (
    id SERIAL PRIMARY KEY,
    invoice_id INT NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    quantity DOUBLE PRECISION,
    unit_price DOUBLE PRECISION,
    tax_rate DOUBLE PRECISION,
    amount DOUBLE PRECISION
);

CREATE INDEX IF NOT EXISTS idx_invoice_items_invoice_id ON invoice_items(invoice_id);
