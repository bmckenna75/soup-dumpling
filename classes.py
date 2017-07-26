from collections import namedtuple


class User:
    def __init__(self, id_, first_name, last_name='', username='',
            language_code=''):
        self.id = id_
        self.first_name = first_name
        self.last_name = last_name
        self.username = username

    @classmethod
    def from_database(cls, user):
        return cls(*user)

    @classmethod
    def from_telegram(cls, user):
        copy = user.copy()
        copy['id_'] = copy.pop('id')
        return cls(**copy)


class Chat:
    def __init__(self, id_, type_, title='', username='', **kwargs):
        self.id = id_
        self.type = type_
        self.title = title
        self.username = username

    @classmethod
    def from_database(cls, chat):
        return cls(*chat)

    @classmethod
    def from_telegram(cls, chat):
        copy = chat.copy()
        copy['id_'] = copy.pop('id')
        copy['type_'] = copy.pop('type')
        return cls(**copy)


class Quote:
    def __init__(self, id_, chat_id, message_id, sent_at, sent_by,
            content, quoted_by=None):
        self.id = id_
        self.chat_id = chat_id
        self.message_id = message_id
        self.sent_at = sent_at
        self.sent_by = sent_by
        self.content = content
        self.quoted_by = quoted_by

    @classmethod
    def from_database(cls, quote):
        return cls(*quote)


Result = namedtuple('Result', ['quote', 'user'])
