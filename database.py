import os
import sqlite3

from classes import Quote, Result, User


ENTITY_TAGS = {
    'bold': ('<b>', '</b>'),
    'italic': ('<i>', '</i>'),
    'code': ('<code>', '</code>'),
    'pre': ('<pre>', '</pre>'),
}


class QuoteDatabase:
    # Status codes for quotes
    QUOTE_ADDED = 1
    QUOTE_ALREADY_EXISTS = 2

    def __init__(self, filename='data.db'):
        self.filename = filename

        if not os.path.isfile(filename):
            self.setup()

    # Database methods

    def connect(self):
        """Connects to the database."""
        self.db = sqlite3.connect(self.filename)
        self.c = self.db.cursor()

    def setup(self):
        """Creates the database."""
        self.connect()

        with open('create.sql', 'r') as f:
            create = f.read().strip()

        self.c.executescript(create)
        self.db.commit()

    # User methods

    def get_user_by_id(self, user_id):
        """Returns a User object for the user with the given ID, or None if the
        user doesn't exist."""
        self.connect()

        select = "SELECT * FROM user WHERE id = ?;"
        self.c.execute(select, (user_id,))

        user = self.c.fetchone()
        if not user:
            return None
        else:
            return User.from_database(user)

    def user_exists(self, user):
        """Returns whether the given user exists in the database."""
        self.connect()

        select = "SELECT EXISTS(SELECT * FROM user WHERE id = ? LIMIT 1);"
        self.c.execute(select, (user.id,))

        result = self.c.fetchone()
        return result[0]

    def add_or_update_user(self, user):
        """Adds a user to the database if they don't exist, or updates their
        data otherwise."""
        self.connect()

        if self.user_exists(user):
            update = ("UPDATE user SET "
                "first_name = ?, last_name = ?, username = ? WHERE id = ?;")
            self.c.execute(update,
                (user.first_name, user.last_name, user.username, user.id))
        else:
            insert = "INSERT INTO user VALUES (?, ?, ?, ?);"
            self.c.execute(insert,
                (user.id, user.first_name, user.last_name, user.username))

        self.db.commit()

    # User ranking methods

    def get_most_quoted(self, chat_id, limit=5):
        """Returns the names of the users who have the most quotes attributed
        to them."""
        self.connect()

        select = """SELECT COUNT(*) AS count,
            user.first_name || " " || user.last_name
            FROM quote INNER JOIN user
            ON quote.sent_by = user.id
            AND quote.chat_id = ?
            GROUP BY quote.sent_by
            ORDER BY count DESC
            LIMIT ?"""
        self.c.execute(select, (chat_id, limit))

        return self.c.fetchall()

    def get_most_quotes_added(self, chat_id, limit=5):
        """Returns the names of the users who have added the most quotes."""
        self.connect()

        select = """SELECT COUNT(*) AS count,
            user.first_name || " " || user.last_name
            FROM quote INNER JOIN user
            ON quote.quoted_by = user.id
            AND quote.chat_id = ?
            GROUP BY quote.quoted_by
            ORDER BY count DESC
            LIMIT ?"""
        self.c.execute(select, (chat_id, limit))

        return self.c.fetchall()

    # Quote methods

    def get_quote_count(self, chat_id, search=None):
        """Returns the number of quotes added in the given chat."""
        self.connect()

        if search is None:
            select = """SELECT COUNT(*) FROM quote
                WHERE quote.chat_id = ?"""
            self.c.execute(select, (chat_id,))
        else:
            select = """SELECT COUNT(DISTINCT quote.id),
                user.first_name || " " || user.last_name AS full_name
                FROM quote INNER JOIN user
                ON quote.sent_by = user.id
                AND quote.chat_id = ?
                AND (quote.content LIKE ?
                    OR full_name LIKE ?
                    OR user.username LIKE ?)"""
            search = '%' + search + '%'
            self.c.execute(select,
                (chat_id, search, search, search))

        return self.c.fetchone()[0]

    def get_first_quote(self, chat_id):
        """Returns the first quote added in the given chat."""
        self.connect()

        select = """SELECT * FROM quote
            WHERE chat_id = ?
            ORDER BY sent_at ASC
            LIMIT 1"""
        self.c.execute(select, (chat_id,))

        row = self.c.fetchone()
        return Quote.from_database(row)

    def get_random_quote(self, chat_id, name=None):
        """Returns a random quote, and the user who wrote the quote."""
        self.connect()

        if name is None:
            select = """SELECT id, chat_id, message_id, sent_at, sent_by,
                content FROM quote
                WHERE chat_id = ?
                ORDER BY RANDOM() LIMIT 1;"""
            self.c.execute(select, (chat_id,))
        else:
            name = name.lstrip('@')
            select = """SELECT
                quote.id, chat_id, message_id, sent_at, sent_by, content,
                user.first_name || " " || user.last_name AS full_name
                FROM quote INNER JOIN user
                ON quote.sent_by = user.id
                AND quote.chat_id = ?
                AND (full_name LIKE ? OR username LIKE ?)
                ORDER BY RANDOM() LIMIT 1;"""
            self.c.execute(select,
                (chat_id, '%' + name + '%', '%' + name + '%'))

        row = self.c.fetchone()
        if row is None:
            return None

        if name is not None:
            row = row[0:6]

        quote = Quote.from_database(row)
        user = self.get_user_by_id(quote.sent_by)
        return Result(quote, user)

    def search_quote(self, chat_id, search_terms):
        """Returns a random quote matching the search terms, and the user
        who wrote the quote."""
        self.connect()

        select = """SELECT id, chat_id, message_id, sent_at, sent_by, content
            FROM quote
            WHERE content LIKE ?
            ORDER BY RANDOM() LIMIT 1;"""
        self.c.execute(select, ('%' + search_terms + '%',))

        row = self.c.fetchone()
        if row is None:
            return None

        quote = Quote.from_database(row)
        user = self.get_user_by_id(quote.sent_by)
        return Result(quote, user)

    def add_quote(self, chat_id, message_id, sent_at, sent_by, content,
            entities, quoted_by):
        """Inserts a quote."""
        self.connect()

        select = ("SELECT * FROM quote "
                  "WHERE chat_id = ? AND message_id = ?;")
        self.c.execute(select, (chat_id, message_id))

        if self.c.fetchone() is None:
            pass
        else:
            return self.QUOTE_ALREADY_EXISTS

        # Convert text formatting to HTML
        entities = sorted(entities, key=lambda e: e['offset'], reverse=True)

        for entity in entities:
            if entity['type'] not in ENTITY_TAGS:
                continue

            s = entity['offset']
            e = s + entity['length']
            s_tag, e_tag = ENTITY_TAGS[entity['type']]

            content = content[0:s] + s_tag + content[s:e] + e_tag + content[e:]

        insert = ("INSERT INTO quote (chat_id, message_id, sent_at, sent_by,"
            "content, quoted_by) VALUES (?, ?, ?, ?, ?, ?);")
        self.c.execute(insert,
            (chat_id, message_id, sent_at, sent_by, content, quoted_by))
        self.db.commit()

        return self.QUOTE_ADDED
