# Soup Dumpling

Soup Dumpling is a simple quote bot for the Telegram chat client. It's written in Python 3 using the `telepot` library.

# Setup

1. Clone this repository: `git clone https://github.com/Doktor/soup-dumpling.git`
2. Install the required packages: `pip install -r requirements.txt`
3. Add your API key to the file `tokens/soup.txt`. To get an API key, message [@BotFather](https://telegram.me/BotFather).
4. Start the bot: `python3 quote.py`.

# Commands

## Anywhere
- `/about` Displays the current version, commit hash, and a link to this repository.
- `/random` Displays a random quote.
- `/author <name>` Displays a random quote from a user whose name or username contains `name`.
- `/search <term>` Displays a random quote whose content contains `term`.
- `/quotes [search]` Displays the number of quotes added, or the number of quotes whose content or author's name contains `search`.
- `/stats` Displays three statistics: the number of quotes added, the users who are quoted the most often, and the users who add the most quotes.

## Groups
- `/addquote` Reply to any message to quote it. You can't quote messages sent by yourself or a bot, or non-text messages.

## Direct messages
You can browse the quotes of any chat you're in by sending direct messages to the bot, to reduce spam in the chat.

- `/chats` Displays the list of chats you can browse.
- `/which` Displays the title of the chat you're browsing.
