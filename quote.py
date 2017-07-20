import telepot
import time
from datetime import datetime

from classes import User
from database import QuoteDatabase

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

VERSION = (1, 0, 0)


class QuoteBot(telepot.Bot):
    commands = ['random', 'quotes', 'author', 'search', 'addquote']

    def __init__(self, token):
        super(QuoteBot, self).__init__(token)

        self.database = QuoteDatabase()
        self.user = self.getMe()

        with open('tokens/username.txt', 'r') as f:
            self.username = f.read().strip()

    def _format_quote(self, quote, user):
        date = datetime.fromtimestamp(quote.sent_at).strftime(TIME_FORMAT)
        message = '"{text}" - {name}\n<i>{date}</i>'.format(
            text=quote.content, name=user.first_name, date=date)
        return message

    def _send_quote(self, chat_id, message, quote_id):
        sent = self.sendMessage(chat_id, message, parse_mode='HTML')

    def handle(self, m):
        content_type, chat_type, chat_id = telepot.glance(m)

        if content_type != 'text':
            return

        if chat_type == 'channel':
            return

        message_id = m['message_id']
        user_id = m['from']['id']
        text = m['text'].lower()

        if not text.startswith('/'):
            return

        raw_command = text.split(' ')[0]
        args = text.replace(raw_command, '').lstrip()
        command = raw_command.replace(self.username.lower(), '').lstrip('/')

        # Ignore unsupported commands
        if command not in self.commands:
            return

        # Handle commands
        if command == 'random':
            result = self.database.get_random_quote(chat_id)

            if result is None:
                response = "no quotes in database"
                self.sendMessage(chat_id, response)
            else:
                response = self._format_quote(*result)
                self._send_quote(chat_id, response, result.quote.id)

        elif command == 'quotes':
            count = self.database.get_quote_count(chat_id)
            response = "{0} quotes for this chat".format(count)
            self.sendMessage(chat_id, response)

        elif command == 'author':
            if not args:
                return

            result = self.database.get_random_quote(chat_id, name=args)

            if result is None:
                response = 'no quotes found by author "{}"'.format(args)
                self.sendMessage(chat_id, response)
            else:
                response = self._format_quote(*result)
                self._send_quote(chat_id, response, result.quote.id)

        elif command == 'search':
            if not args:
                return

            result = self.database.search_quote(chat_id, args)

            if result is None:
                response = 'no quotes found for search terms "{}"'.format(args)
                self.sendMessage(chat_id, response)
            else:
                response = self._format_quote(*result)
                self._send_quote(chat_id, response, result.quote.id)

        elif command == 'addquote':
            quote = m.get('reply_to_message', '')
            if not quote:
                return

            # Only text messages can be added as quotes
            content_type, _, _ = telepot.glance(quote)
            if content_type != 'text':
                return

            quoted_by = m['from']

            # Forwarded messages
            if 'forward_from' in quote:
                sent_by = quote['forward_from']
                sent_at = quote['forward_date']
            else:
                sent_by = quote['from']
                sent_at = quote['date']

            # Bot messages can't be added as quotes
            if sent_by['id'] == self.user['id']:
                response = "can't quote bot messages"
                self.sendMessage(
                    chat_id, response, reply_to_message_id=message_id)
                return

            # Users can't add their own messages as quotes
            if sent_by['id'] == quoted_by['id']:
                response = "can't quote own messages"
                self.sendMessage(
                    chat_id, response, reply_to_message_id=message_id)
                return

            self.database.add_or_update_user(User.from_telegram(sent_by))
            self.database.add_or_update_user(User.from_telegram(quoted_by))

            result = self.database.add_quote(
                chat_id, quote['message_id'], sent_at,
                sent_by['id'], quote['text'], quoted_by['id'])

            if result == QuoteDatabase.QUOTE_ADDED:
                response = "quote added"
            elif result == QuoteDatabase.QUOTE_ALREADY_EXISTS:
                response = "quote already exists"

            self.sendMessage(
                chat_id, response, reply_to_message_id=message_id)


def main():
    with open('tokens/weow.txt', 'r') as f:
        token = f.read().strip()

    bot = QuoteBot(token)
    bot.message_loop()

    while True:
        time.sleep(10)


if __name__ == '__main__':
    print("[%s] running" % datetime.now())
    main()
