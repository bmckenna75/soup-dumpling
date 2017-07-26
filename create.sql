CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT,
    username TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS chat (
    id INTEGER PRIMARY KEY,
    type TEXT NOT NULL CHECK (type IN ('private', 'group', 'supergroup', 'channel')),
    title TEXT,
    username TEXT
);

CREATE TABLE IF NOT EXISTS membership (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES user (id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    chat_id INTEGER NOT NULL REFERENCES chat (id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    UNIQUE(user_id, chat_id) ON CONFLICT ROLLBACK
);

CREATE TABLE IF NOT EXISTS state (
    user_id INTEGER PRIMARY KEY REFERENCES user (id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    chat_id INTEGER NOT NULL REFERENCES chat (id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    code INTEGER NOT NULL DEFAULT 0,
    data TEXT DEFAULT ''
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
