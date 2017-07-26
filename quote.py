import json
import telepot
import time
from datetime import datetime
from subprocess import check_output

from classes import Chat, User
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

VERSION = (1, 1, 0)

# User state codes
NO_CHAT_SPECIFIED = 0
SELECTING_CHAT = 1
SELECTED_CHAT = 2


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
        origin = chat_id

        if content_type != 'text':
            return

        if chat_type == 'channel':
            return

        message_id = m['message_id']
        user_id = m['from']['id']
        text = m['text'].lower()

        if chat_type != 'private' and not text.startswith('/'):
            return

        raw_command = text.split(' ')[0]
        args = text.replace(raw_command, '').lstrip()
        command = raw_command.replace(self.username.lower(), '').lstrip('/')

        # Ignore unsupported commands
        if chat_type != 'private' and command not in self.commands:
            return

        self.database.add_or_update_user(User.from_telegram(m['from']))

        if user_id != chat_id:
            self.database.add_or_update_chat(Chat.from_telegram(m['chat']))
            self.database.add_membership(user_id, chat_id)

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
            return self.sendMessage(chat_id, response,
                disable_web_page_preview=True, parse_mode='HTML')

        elif chat_type != 'private' and command == 'addquote':
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
                return self.sendMessage(
                    origin, response, reply_to_message_id=message_id)

            # Users can't add their own messages as quotes
            if sent_by['id'] == quoted_by['id']:
                response = "can't quote own messages"
                return self.sendMessage(
                    origin, response, reply_to_message_id=message_id)

            self.database.add_or_update_user(User.from_telegram(sent_by))
            self.database.add_or_update_user(User.from_telegram(quoted_by))

            result = self.database.add_quote(
                chat_id, quote['message_id'], sent_at, sent_by['id'],
                quote['text'], quote.get('entities', list()), quoted_by['id'])

            if result == QuoteDatabase.QUOTE_ADDED:
                response = "quote added"
            elif result == QuoteDatabase.QUOTE_ALREADY_EXISTS:
                response = "quote already exists"

            return self.sendMessage(
                chat_id, response, reply_to_message_id=message_id)

        # Browse quotes via direct message

        if chat_type == 'private':
            code, data = self.database.get_or_create_state(user_id)
            data = '' if data is None or not data else json.loads(data)

            if command in ['start', 'chats'] or code == NO_CHAT_SPECIFIED:
                chats = self.database.get_chats(user_id)

                if not chats:
                    response = "<b>Chat selection</b>\nno chats found"
                    return self.sendMessage(
                        origin, response, parse_mode='HTML')

                response = [
                    "<b>Chat selection</b>",
                    "Choose a chat by its number or title:",
                    "",
                ]

                mapping = []
                for i, (chat_id, chat_title) in enumerate(chats):
                    response.append("<b>[{0}]</b> {1}".format(i, chat_title))
                    mapping.append([i, chat_id, chat_title])

                self.database.set_state(
                    user_id, SELECTING_CHAT, data=json.dumps(mapping))

                response = '\n'.join(response)
                return self.sendMessage(origin, response, parse_mode='HTML')

            elif code == SELECTING_CHAT:
                choice = text

                try:
                    i = int(choice)
                    _, selected_id, title = data[i]
                except IndexError:
                    return self.sendMessage(chat_id, "invalid chat number")
                except ValueError:
                    try:
                        _, selected_id, title = next(filter(data,
                            lambda chat: choice.lower() in chat[2].lower()))
                    except StopIteration:
                        return self.sendMessage(
                            chat_id, "no chat titles matched")

                self.database.set_state(
                    user_id, SELECTED_CHAT, data=str(selected_id))

                response = 'selected chat "{0}"'.format(title)
                self.sendMessage(origin, response, parse_mode='HTML')

                chat_id = selected_id

            elif code == SELECTED_CHAT:
                chat_id = int(self.database.get_state(user_id)[1])

                if command == 'which':
                    chat = self.database.get_chat_by_id(chat_id)
                    response = 'searching quotes from "{0}"'.format(chat.title)
                    return self.sendMessage(origin, response)

        # Find quotes

        if command == 'random':
            result = self.database.get_random_quote(chat_id)

            if result is None:
                response = "no quotes in database"
                self.sendMessage(origin, response)
            else:
                response = self._format_quote(*result)
                self._send_quote(origin, response, result.quote.id)

        elif command == 'quotes':
            if not args:
                count = self.database.get_quote_count(chat_id)
                response = "{0} quotes in this chat".format(count)
            else:
                count = self.database.get_quote_count(chat_id, search=args)
                response = ('{0} quotes in this chat '
                    'for search term "{1}"').format(count, args)

            self.sendMessage(origin, response, reply_to_message_id=message_id)

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

            self.sendMessage(origin, '\n'.join(response), parse_mode='HTML')

        elif command == 'author':
            if not args:
                return

            result = self.database.get_random_quote(chat_id, name=args)

            if result is None:
                response = 'no quotes found by author "{}"'.format(args)
                self.sendMessage(origin, response)
            else:
                response = self._format_quote(*result)
                self._send_quote(origin, response, result.quote.id)

        elif command == 'search':
            if not args:
                return

            result = self.database.search_quote(chat_id, args)

            if result is None:
                response = 'no quotes found for search terms "{}"'.format(args)
                self.sendMessage(origin, response)
            else:
                response = self._format_quote(*result)
                self._send_quote(origin, response, result.quote.id)


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
