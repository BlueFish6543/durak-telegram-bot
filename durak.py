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
deck = []
discard_pile = []
total_number_of_cards = 0
trump_suit = None

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

def update_cards_left():
    for i in range(len(users)):
        message = 'There are {} cards left in the deck.'.format(len(deck))
        bot.send_message(chat_id=chat_ids[i], text=message)

def display_cards_info(text):
    global trump_suit
    for i in range(len(users)):
        message = text
        message += 'Your cards: '
        for j in range(len(cards[users[i]])):
            message += cards[users[i]][j]
            message += ' '
        message += '\nThe trump (last card) is {}.'.format(deck[0])
        bot.send_message(chat_id=chat_ids[i], text=message)
    trump_suit = str(deck[0])[1]
    update_cards_left()

def start_game(update, context):
    global deck

    message = 'A game has been started. Current players: '
    for i in range(len(users)):
        message += users[i]
        message += ', '
    message = message[:-2]

    n_decks = int(math.ceil(len(users) / 5))
    total_number_of_cards = 52 * n_decks
    message += '\nUsing {} deck(s). '.format(n_decks)
    for i in range(n_decks):
        deck += list(Card)
    random.shuffle(deck)

    # Deal cards
    for i in range(len(users)):
        cards[users[i]] = [str(deck.pop()) for _ in range(7)]
    
    display_cards_info(message)
    play_game()

def play_game():
    n_players = len(users)
    while(len(discard_pile) < total_number_of_cards):
        pass

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('startgame', start_game))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()