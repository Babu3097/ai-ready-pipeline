-- create_tables.sql : the database design (SQLite).
-- Each "table" is like one sheet in a workbook. A PRIMARY KEY is the column
-- that identifies each row uniquely. A FOREIGN KEY points at a row in another table.

DROP TABLE IF EXISTS audit_log;
DROP TABLE IF EXISTS human_reviews;
DROP TABLE IF EXISTS ai_triage;
DROP TABLE IF EXISTS data_quality_log;
DROP TABLE IF EXISTS quality_scores;
DROP TABLE IF EXISTS enquiries;
DROP TABLE IF EXISTS ground_truth;
DROP TABLE IF EXISTS raw_row_map;

-- One row per cleaned enquiry. raw_row = its line number in the raw sheet
-- (case_ref can be missing, so it can't be the key).
CREATE TABLE enquiries (
    raw_row               INTEGER PRIMARY KEY,
    case_ref              TEXT,
    received_date         TEXT,      -- ISO format: 2025-10-14
    channel               TEXT,      -- Email / Web form
    name                  TEXT,
    email                 TEXT,
    phone                 TEXT,
    postcode              TEXT,
    category              TEXT,      -- from the cleaned sheet (may be empty)
    urgency               TEXT,      -- legacy urgency (often empty)
    message               TEXT,
    message_masked        TEXT,      -- personal details hidden; the only text AI sees
    status                TEXT,      -- Open / Closed
    handling_mins         INTEGER,   -- legacy handling time, minutes
    category_ai_suggestion TEXT,
    category_ai_confidence REAL,
    category_ai_note      TEXT,
    possible_duplicate_of TEXT,
    quality_flags         TEXT,
    quality_status        TEXT       -- clean / fixed / needs_review
);

-- Every change the clean-up made (or flagged).
CREATE TABLE data_quality_log (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_row   INTEGER,
    field     TEXT,
    issue     TEXT,
    action    TEXT,
    old_value TEXT,
    new_value TEXT
);

CREATE TABLE quality_scores (
    metric  TEXT PRIMARY KEY,
    before  REAL,
    after   REAL,
    meaning TEXT
);

-- What the AI (or the demo stand-in) said about each enquiry.
CREATE TABLE ai_triage (
    raw_row             INTEGER PRIMARY KEY REFERENCES enquiries(raw_row),
    category            TEXT,
    urgency             TEXT,
    summary             TEXT,
    postcode            TEXT,   -- copied from the cleaned column; postcodes are never sent to AI
    requested_action    TEXT,
    confidence          REAL,
    needs_human_review  INTEGER,   -- 1 = a person must decide
    reason              TEXT,
    mode                TEXT,      -- 'claude' or 'demo'
    model               TEXT,
    input_tokens        INTEGER,
    output_tokens       INTEGER,
    cost_gbp            REAL,
    created_at          TEXT
);

-- What a person decided about a flagged enquiry.
CREATE TABLE human_reviews (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_row         INTEGER REFERENCES enquiries(raw_row),
    decision        TEXT,      -- approved / edited / rejected
    final_category  TEXT,
    final_urgency   TEXT,
    reviewer        TEXT,
    reviewed_at     TEXT,
    notes           TEXT,
    simulated       INTEGER    -- 1 = a stand-in reviewer in the demo, not a real person
);

-- A diary of everything that happened, by whom, and when.
CREATE TABLE audit_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ts         TEXT,
    raw_row    INTEGER,
    actor      TEXT,    -- system / ai / human
    action     TEXT,
    detail     TEXT
);

-- EVALUATION ONLY: the answer key. The pipeline never reads these two tables.
CREATE TABLE ground_truth (
    enquiry_id     TEXT PRIMARY KEY,
    received_date  TEXT, channel TEXT, name TEXT, email TEXT, phone TEXT, postcode TEXT,
    category       TEXT,
    urgency        TEXT,
    message        TEXT, status TEXT, handling_mins TEXT
);

CREATE TABLE raw_row_map (
    raw_row     INTEGER PRIMARY KEY,
    enquiry_id  TEXT,
    row_type    TEXT,
    issue_tags  TEXT
);
