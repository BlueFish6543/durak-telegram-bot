import logging
from telegram import Bot, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
import math
import random
from poker import Card

TOKEN = '1149877964:AAEsgPRA71GcpjDLkGgqrpKaWlq2AXqW9hY'

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

bot = Bot(TOKEN)

users = []
chat_ids = []
cards = {}

def update_players():
    for i in range(len(users) - 1):
        message = '{} has joined the game. Current players: '.format(users[-1])
        for j in range(len(users)):
            message += users[j]
            message += ', '
        message = message[:-2]
        bot.send_message(chat_id=chat_ids[i], text=message)

def start(update, context):
    user = update.message.from_user.first_name
    if user not in users:
        users.append(user)
        chat_ids.append(update.message.chat_id)
    message = 'You have joined a game of Durak. Type /startgame to start game. '
    message += 'Current players: '
    for i in range(len(users)):
        message += users[i]
        message += ', '
    message = message[:-2]
    update.message.reply_text(message)
    update_players()

def start_game(update, context):
    message = 'A game has been started. Current players: '
    for i in range(len(users)):
        message += users[i]
        message += ', '
    message = message[:-2]

    n_decks = int(math.ceil(len(users) / 5))
    message += '\nUsing {} decks. '.format(n_decks)
    deck = []
    for i in range(n_decks):
        deck += list(Card)
    random.shuffle(deck)

    for i in range(len(users)):
        cards[users[i]] = [deck.pop() for _ in range(7)]
    

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('startgame', start_game))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()