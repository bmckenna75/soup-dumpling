CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT,
    username TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS quote (
    id INTEGER PRIMARY KEY,
    chat_id INTEGER NOT NULL,
    message_id INTEGER NOT NULL,
    sent_at INTEGER NOT NULL,
    sent_by INTEGER NOT NULL REFERENCES user (id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    content TEXT,
    quoted_by INTEGER REFERENCES user (id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    UNIQUE(chat_id, message_id) ON CONFLICT ROLLBACK
);
