-- =====================================================
-- UoN Student Marketplace - MySQL schema (generated from schema.sql)
-- Import order: mysql_schema.sql, then mysql_seed.sql
-- e.g. in phpMyAdmin (XAMPP): import both files - the script creates
-- the `uon_marketplace` database itself.
-- =====================================================
CREATE DATABASE IF NOT EXISTS `uon_marketplace` CHARACTER SET utf8mb4;
USE `uon_marketplace`;

-- =====================================================================
-- UoN Student Marketplace - database schema (SQLite dialect)
-- COMP6900 Group 7 - Assessment 4
-- Companion MySQL script: mysql_schema.sql (same structure)
-- =====================================================================



-- ---------------------------------------------------------------------
-- users: every account on the platform.
-- BR-01 registration is restricted to approved UoN emails (validated in
-- application code); BR-09 roles can only be changed by an administrator.
-- ---------------------------------------------------------------------
CREATE TABLE users (
    user_id        INT PRIMARY KEY AUTO_INCREMENT,
    email          VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,                -- PBKDF2-SHA256, never plain text
    first_name VARCHAR(80) NOT NULL,
    last_name VARCHAR(80) NOT NULL,
    phone VARCHAR(30),
    role           TEXT NOT NULL DEFAULT 'student'
                   CHECK (role IN ('student', 'admin')),
    status VARCHAR(20) NOT NULL DEFAULT 'active'
                   CHECK (status IN ('active', 'suspended')),
    created_at     TEXT NOT NULL
);

-- ---------------------------------------------------------------------
-- categories: listing categories (Goods / Housing / Transport / Services
-- plus the two extra demo categories). Administrators manage them (FR-13).
-- ---------------------------------------------------------------------
CREATE TABLE categories (
    category_id   INT PRIMARY KEY AUTO_INCREMENT,
    name          VARCHAR(120) NOT NULL UNIQUE,
    description TEXT,
    is_archived   INTEGER NOT NULL DEFAULT 0      -- 0 active, 1 archived (hidden)
);

-- ---------------------------------------------------------------------
-- listings: items posted by students (FR-04).
-- status lifecycle: active -> archived | sold; administrators may set
-- 'removed' when moderating (BR-07, BR-10).
-- ---------------------------------------------------------------------
CREATE TABLE listings (
    listing_id   INT PRIMARY KEY AUTO_INCREMENT,
    user_id      INTEGER NOT NULL REFERENCES users (user_id),
    category_id  INTEGER NOT NULL REFERENCES categories (category_id),
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    price DECIMAL(10, 2) NOT NULL DEFAULT 0,          -- AUD, 0 = free
    condition    TEXT NOT NULL
                 CHECK (condition IN ('New', 'Like new', 'Good', 'Fair', 'Needs repair')),
    location VARCHAR(255),
    status VARCHAR(20) NOT NULL DEFAULT 'active'
                 CHECK (status IN ('active', 'archived', 'sold', 'removed')),
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);

-- Listing photos (FR-05): up to 3 per listing, first one is primary.
CREATE TABLE listing_images (
    image_id     INT PRIMARY KEY AUTO_INCREMENT,
    listing_id   INTEGER NOT NULL REFERENCES listings (listing_id) ON DELETE CASCADE,
    file_path VARCHAR(255) NOT NULL,
    is_primary   INTEGER NOT NULL DEFAULT 0,
    uploaded_at  TEXT NOT NULL
);

-- Favourites (FR-08): one save per user per listing.
CREATE TABLE favourites (
    user_id      INTEGER NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    listing_id   INTEGER NOT NULL REFERENCES listings (listing_id) ON DELETE CASCADE,
    created_at   TEXT NOT NULL,
    PRIMARY KEY (user_id, listing_id)
);

-- Conversations (FR-09): one per (listing, buyer); the seller is the
-- listing owner. BR-05: only these two parties may read/write messages.
CREATE TABLE conversations (
    conversation_id INT PRIMARY KEY AUTO_INCREMENT,
    listing_id      INTEGER NOT NULL REFERENCES listings (listing_id) ON DELETE CASCADE,
    buyer_id        INTEGER NOT NULL REFERENCES users (user_id),
    created_at      TEXT NOT NULL,
    UNIQUE (listing_id, buyer_id)
);

-- Individual messages inside a conversation (FR-09).
CREATE TABLE messages (
    message_id      INT PRIMARY KEY AUTO_INCREMENT,
    conversation_id INTEGER NOT NULL REFERENCES conversations (conversation_id) ON DELETE CASCADE,
    sender_id       INTEGER NOT NULL REFERENCES users (user_id),
    body TEXT NOT NULL,
    sent_at         TEXT NOT NULL,
    is_read         INTEGER NOT NULL DEFAULT 0
);

-- Reports (FR-11, BR-06): students report listings; administrators
-- resolve them (FR-12). status: open / in_review / resolved / dismissed.
CREATE TABLE reports (
    report_id       INT PRIMARY KEY AUTO_INCREMENT,
    listing_id      INTEGER NOT NULL REFERENCES listings (listing_id) ON DELETE CASCADE,
    reporter_id     INTEGER NOT NULL REFERENCES users (user_id),
    reason VARCHAR(255) NOT NULL,
    details TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'open'
                    CHECK (status IN ('open', 'in_review', 'resolved', 'dismissed')),
    resolved_by     INTEGER REFERENCES users (user_id),
    resolved_at     TEXT,
    resolution_note TEXT,
    created_at      TEXT NOT NULL
);

-- Audit trail (BR-08): every administrator action is recorded.
CREATE TABLE audit_log (
    audit_id    INT PRIMARY KEY AUTO_INCREMENT,
    admin_id    INTEGER NOT NULL REFERENCES users (user_id),
    action VARCHAR(255) NOT NULL,
    entity_type VARCHAR(255) NOT NULL,
    entity_id VARCHAR(255) NOT NULL,
    details TEXT,
    created_at  TEXT NOT NULL
);

-- Email notification log (FR-10): simulated emails when SMTP is not
-- configured, plus a record of real sends.
CREATE TABLE email_log (
    email_id  INT PRIMARY KEY AUTO_INCREMENT,
    recipient VARCHAR(255) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    status VARCHAR(20) NOT NULL,                        -- sent / simulated / failed
    sent_at   TEXT NOT NULL
);

-- ---------------------------------------------------------------------
-- Indexes for the main search paths (search & filtering, FR-06/FR-07)
-- ---------------------------------------------------------------------
CREATE INDEX idx_listings_status    ON listings (status);
CREATE INDEX idx_listings_category  ON listings (category_id);
CREATE INDEX idx_listings_price     ON listings (price);
CREATE INDEX idx_listings_user      ON listings (user_id);
CREATE INDEX idx_images_listing     ON listing_images (listing_id);
CREATE INDEX idx_messages_conv      ON messages (conversation_id);
CREATE INDEX idx_favourites_user    ON favourites (user_id);
CREATE INDEX idx_reports_status     ON reports (status);
