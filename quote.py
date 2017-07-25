import telepot
import time
from datetime import datetime
from subprocess import check_output

from classes import User
from database import QuoteDatabase


TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

REPOSITORY_NAME = "Doktor/soup-dumpling"
REPOSITORY_URL = "https://github.com/Doktor/soup-dumpling"

COMMIT_HASH = check_output(['git', 'rev-parse', 'HEAD'],
    encoding='utf8').rstrip('\n')
COMMIT_URL = REPOSITORY_URL + '/commit/' + COMMIT_HASH

DATE_ARGS = ['git', 'log', COMMIT_HASH,
    '-1', '--date=iso', r'--pretty=format:%cd']
COMMIT_DATE = check_output(DATE_ARGS, encoding='utf8')[:19]

# The relative date is used for the 'about' command
DATE_ARGS[4] = '--date=relative'

VERSION = (1, 0, 0)


class QuoteBot(telepot.Bot):
    commands = ['about',
        'random', 'quotes', 'stats', 'author', 'search', 'addquote']

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
        if command == 'about':
            info = {
                'version': '.'.join((str(n) for n in VERSION)),
                'updated': COMMIT_DATE,
                'updated_rel': check_output(DATE_ARGS, encoding='utf8'),
                'repo_url': REPOSITORY_URL,
                'repo_name': REPOSITORY_NAME,
                'hash_url': COMMIT_URL,
                'hash': COMMIT_HASH[:7],
            }

            response = ['"Nice quote!" - <b>Soup Dumpling {version}</b>',
                '<i>{updated} ({updated_rel})</i>',
                '',
                'Source code at <a href="{repo_url}">{repo_name}</a>',
                'Running on commit <a href="{hash_url}">{hash}</a>',
            ]

            response = '\n'.join(response).format(**info)
            self.sendMessage(chat_id, response,
                disable_web_page_preview=True, parse_mode='HTML')

        elif command == 'random':
            result = self.database.get_random_quote(chat_id)

            if result is None:
                response = "no quotes in database"
                self.sendMessage(chat_id, response)
            else:
                response = self._format_quote(*result)
                self._send_quote(chat_id, response, result.quote.id)

        elif command == 'quotes':
            if not args:
                count = self.database.get_quote_count(chat_id)
                response = "{0} quotes in this chat".format(count)
            else:
                count = self.database.get_quote_count(chat_id, search=args)
                response = ('{0} quotes in this chat '
                    'for search term "{1}"').format(count, args)

            self.sendMessage(chat_id, response, reply_to_message_id=message_id)

        elif command == 'stats':
            # Overall
            total_count = self.database.get_quote_count(chat_id)
            first_quote_dt = self.database.get_first_quote(chat_id).sent_at

            response = list()

            response.append("<b>Total quote count</b>")
            response.append("• {0} quotes since {1}".format(total_count,
                datetime.fromtimestamp(first_quote_dt).strftime(TIME_FORMAT)))
            response.append("")

            # Users
            most_quoted = self.database.get_most_quoted(chat_id, limit=5)

            response.append("<b>Users with the most quotes</b>")
            for count, name in most_quoted:
                response.append("• {0} ({1:.1%}): {2}".format(
                    count, count / total_count, name))
            response.append("")

            added_most = self.database.get_most_quotes_added(chat_id, limit=5)

            response.append("<b>Users who add the most quotes</b>")
            for count, name in added_most:
                response.append("• {0} ({1:.1%}): {2}".format(
                    count, count / total_count, name))

            self.sendMessage(chat_id, '\n'.join(response), parse_mode='HTML')

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
                chat_id, quote['message_id'], sent_at, sent_by['id'],
                quote['text'], quote.get('entities', list()), quoted_by['id'])

            if result == QuoteDatabase.QUOTE_ADDED:
                response = "quote added"
            elif result == QuoteDatabase.QUOTE_ALREADY_EXISTS:
                response = "quote already exists"

            self.sendMessage(
                chat_id, response, reply_to_message_id=message_id)


def main():
    with open('tokens/soup.txt', 'r') as f:
        token = f.read().strip()

    bot = QuoteBot(token)
    bot.message_loop()

    while True:
        time.sleep(10)


if __name__ == '__main__':
    print("[%s] running" % datetime.now())
    main()
