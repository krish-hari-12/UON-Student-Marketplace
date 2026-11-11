-- =====================================================================
-- UoN Student Marketplace - database schema (SQLite dialect)
-- COMP6900 Group 7 - Assessment 4
-- =====================================================================

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
-- 1. USERS
-- ---------------------------------------------------------------------
CREATE TABLE users (
    user_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    email          TEXT NOT NULL UNIQUE,
    password_hash  TEXT NOT NULL,
    first_name     TEXT NOT NULL,
    last_name      TEXT NOT NULL,
    phone          TEXT,
    profile_photo  TEXT,
    role           TEXT NOT NULL DEFAULT 'student'
                   CHECK (role IN ('student', 'admin')),
    status         TEXT NOT NULL DEFAULT 'active'
                   CHECK (status IN ('active', 'suspended')),
    created_at     TEXT NOT NULL
);

-- ---------------------------------------------------------------------
-- 2. CATEGORIES
-- ---------------------------------------------------------------------
CREATE TABLE categories (
    category_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL UNIQUE,
    description   TEXT,
    is_archived   INTEGER NOT NULL DEFAULT 0
);

-- ---------------------------------------------------------------------
-- 3. LISTINGS
-- ---------------------------------------------------------------------
CREATE TABLE listings (
    listing_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL REFERENCES users (user_id),
    category_id  INTEGER NOT NULL REFERENCES categories (category_id),
    title        TEXT NOT NULL,
    description  TEXT NOT NULL,
    price        REAL NOT NULL DEFAULT 0,
    condition    TEXT NOT NULL
                 CHECK (condition IN ('New', 'Like new', 'Good', 'Fair', 'Needs repair')),
    location     TEXT,
    status       TEXT NOT NULL DEFAULT 'active'
                 CHECK (status IN ('active', 'archived', 'sold', 'removed')),
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);

-- ---------------------------------------------------------------------
-- 4. LISTING IMAGES
-- ---------------------------------------------------------------------
CREATE TABLE listing_images (
    image_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id   INTEGER NOT NULL REFERENCES listings (listing_id) ON DELETE CASCADE,
    file_path    TEXT NOT NULL,
    is_primary   INTEGER NOT NULL DEFAULT 0,
    uploaded_at  TEXT NOT NULL
);

-- ---------------------------------------------------------------------
-- 5. FAVOURITES
-- ---------------------------------------------------------------------
CREATE TABLE favourites (
    user_id      INTEGER NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    listing_id   INTEGER NOT NULL REFERENCES listings (listing_id) ON DELETE CASCADE,
    created_at   TEXT NOT NULL,
    PRIMARY KEY (user_id, listing_id)
);

-- ---------------------------------------------------------------------
-- 6. CONVERSATIONS
-- ---------------------------------------------------------------------
CREATE TABLE conversations (
    conversation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id      INTEGER NOT NULL REFERENCES listings (listing_id) ON DELETE CASCADE,
    buyer_id        INTEGER NOT NULL REFERENCES users (user_id),
    created_at      TEXT NOT NULL,
    UNIQUE (listing_id, buyer_id)
);

-- ---------------------------------------------------------------------
-- 7. MESSAGES
-- ---------------------------------------------------------------------
CREATE TABLE messages (
    message_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL REFERENCES conversations (conversation_id) ON DELETE CASCADE,
    sender_id       INTEGER NOT NULL REFERENCES users (user_id),
    body            TEXT NOT NULL,
    sent_at         TEXT NOT NULL,
    is_read         INTEGER NOT NULL DEFAULT 0
);

-- ---------------------------------------------------------------------
-- 8. REPORTS
-- ---------------------------------------------------------------------
CREATE TABLE reports (
    report_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id      INTEGER NOT NULL REFERENCES listings (listing_id) ON DELETE CASCADE,
    reporter_id     INTEGER NOT NULL REFERENCES users (user_id),
    reason          TEXT NOT NULL,
    details         TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'open'
                    CHECK (status IN ('open', 'in_review', 'resolved', 'dismissed')),
    resolved_by     INTEGER REFERENCES users (user_id),
    resolved_at     TEXT,
    resolution_note TEXT,
    created_at      TEXT NOT NULL
);

-- ---------------------------------------------------------------------
-- 9. AUDIT LOG
-- ---------------------------------------------------------------------
CREATE TABLE audit_log (
    audit_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id    INTEGER NOT NULL REFERENCES users (user_id),
    action      TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id   TEXT NOT NULL,
    details     TEXT,
    created_at  TEXT NOT NULL
);

-- ---------------------------------------------------------------------
-- 10. EMAIL LOG
-- ---------------------------------------------------------------------
CREATE TABLE email_log (
    email_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    recipient TEXT NOT NULL,
    subject   TEXT NOT NULL,
    body      TEXT NOT NULL,
    status    TEXT NOT NULL,
    sent_at   TEXT NOT NULL
);

-- ---------------------------------------------------------------------
-- 11. EMAIL OTPS
-- ---------------------------------------------------------------------
CREATE TABLE email_otps (
    otp_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    email        TEXT NOT NULL,
    otp_hash     TEXT NOT NULL,
    purpose      TEXT NOT NULL
                 CHECK (purpose IN ('registration', 'password_reset')),
    expires_at   TEXT NOT NULL,
    attempts     INTEGER NOT NULL DEFAULT 0,
    is_used      INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL
);

-- ---------------------------------------------------------------------
-- 12. PENDING REGISTRATIONS
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pending_registrations (
    pending_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    first_name    TEXT NOT NULL,
    last_name     TEXT NOT NULL,
    phone         TEXT,
    expires_at    TEXT NOT NULL,
    created_at    TEXT NOT NULL
);

-- ---------------------------------------------------------------------
-- 13. SUPPORT TICKETS
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS support_tickets (
    ticket_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(user_id),
    category    TEXT NOT NULL,
    subject     TEXT NOT NULL,
    description TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'open'
                CHECK (status IN ('open', 'in_progress', 'resolved')),
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

-- ---------------------------------------------------------------------
-- 14. SUPPORT MESSAGES
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS support_messages (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id  INTEGER NOT NULL
               REFERENCES support_tickets(ticket_id) ON DELETE CASCADE,
    sender_id  INTEGER NOT NULL REFERENCES users(user_id),
    body       TEXT NOT NULL,
    sent_at    TEXT NOT NULL
);

-- ---------------------------------------------------------------------
-- 4. LISTING IMAGES
-- ---------------------------------------------------------------------
CREATE TABLE listing_images (
    image_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id   INTEGER NOT NULL REFERENCES listings (listing_id) ON DELETE CASCADE,
    file_path    TEXT NOT NULL,
    is_primary   INTEGER NOT NULL DEFAULT 0,
    is_archived  INTEGER NOT NULL DEFAULT 0
                 CHECK (is_archived IN (0, 1)),
    uploaded_at  TEXT NOT NULL
);

-- =====================================================================
-- INDEXES
-- =====================================================================

CREATE INDEX idx_listings_status
ON listings(status);

CREATE INDEX idx_listings_category
ON listings(category_id);

CREATE INDEX idx_listings_price
ON listings(price);

CREATE INDEX idx_listings_user
ON listings(user_id);

CREATE INDEX idx_images_listing
ON listing_images(listing_id);

CREATE INDEX idx_messages_conv
ON messages(conversation_id);

CREATE INDEX idx_favourites_user
ON favourites(user_id);

CREATE INDEX idx_reports_status
ON reports(status);

CREATE INDEX IF NOT EXISTS idx_email_otps_email_purpose
ON email_otps(email, purpose, is_used);

CREATE INDEX IF NOT EXISTS idx_pending_registrations_email
ON pending_registrations(email);

CREATE INDEX IF NOT EXISTS idx_support_tickets_user
ON support_tickets(user_id);

CREATE INDEX IF NOT EXISTS idx_support_tickets_status
ON support_tickets(status);

CREATE INDEX IF NOT EXISTS idx_support_messages_ticket
ON support_messages(ticket_id);

CREATE INDEX IF NOT EXISTS idx_videos_listing
ON listing_videos(listing_id);

CREATE INDEX idx_images_listing_active
ON listing_images(listing_id, is_archived);