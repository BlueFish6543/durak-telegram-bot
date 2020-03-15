from telegram import Bot, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
import math
import random
from poker import Card

TOKEN = '1149877964:AAEsgPRA71GcpjDLkGgqrpKaWlq2AXqW9hY'
bot = Bot(TOKEN)

class Durak():
    def __init__(self):
        self.players = []
        self.chat_ids = []
        self.cards = {}
        self.deck = []
        self.discard_pile = []
        self.total_number_of_cards = 0
        self.trump_suit = ''
        self.attacker = 0
        self.attacked = 0
        self.state = None

durak = Durak()

def update_players():
    for i in range(len(durak.players) - 1):
        message = '{} has joined the game. Current players: '.format(durak.players[-1])
        for j in range(len(durak.players)):
            message += durak.players[j]
            message += ', '
        message = message[:-2]
        bot.send_message(chat_id=durak.chat_ids[i], text=message)

def start(update, context):
    user = update.message.from_user.first_name
    if user not in durak.players:
        durak.players.append(user)
        durak.chat_ids.append(update.message.chat_id)
    message = 'You have joined a game of Durak. Type /startgame to start game. '
    message += 'Current players: '
    for i in range(len(durak.players)):
        message += durak.players[i]
        message += ', '
    message = message[:-2]
    update.message.reply_text(message)
    update_players()

def update_cards_left():
    for i in range(len(durak.players)):
        message = 'There are {} cards left in the deck.'.format(len(durak.deck))
        bot.send_message(chat_id=durak.chat_ids[i], text=message)

def display_cards_info(text):
    for i in range(len(durak.players)):
        message = text
        message += 'Your cards: '
        for j in range(len(durak.cards[durak.players[i]])):
            message += durak.cards[durak.players[i]][j]
            message += ' '
        message += '\nThe trump (last card) is {}.'.format(durak.deck[0])
        bot.send_message(chat_id=durak.chat_ids[i], text=message)
    durak.trump_suit = str(durak.deck[0])[1]
    update_cards_left()

def start_game(update, context):
    message = 'A game has been started. Current players: '
    for i in range(len(durak.players)):
        message += durak.players[i]
        message += ', '
    message = message[:-2]

    n_decks = int(math.ceil(len(durak.players) / 5))
    durak.total_number_of_cards = 52 * n_decks
    message += '\nUsing {} deck(s). '.format(n_decks)
    for i in range(n_decks):
        durak.deck += list(Card)
    random.shuffle(durak.deck)

    # Deal cards
    for i in range(len(durak.players)):
        durak.cards[durak.players[i]] = [str(durak.deck.pop()) for _ in range(7)]
    
    display_cards_info(message)
    play_game()

def launch_attack():
    reply_keyboard = [durak.cards[durak.players[durak.attacker]]]
    message = 'You are the attacker this round. Choose a card to attack {}.'.format(durak.players[durak.attacked])
    bot.send_message(chat_id=durak.chat_ids[durak.attacker], text=message,
                     reply_markup=ReplyKeyboardMarkup(reply_keyboard))

def handle_response():
    pass

def play_game():
    launch_attack()

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('startgame', start_game))
    dp.add_handler(MessageHandler(Filters.text, handle_response))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()