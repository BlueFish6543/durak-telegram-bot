from telegram import Bot, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
from enum import Enum
import math
import random
import re
from threading import Timer
from poker import Card, Rank

TOKEN = '1149877964:AAEsgPRA71GcpjDLkGgqrpKaWlq2AXqW9hY'
bot = Bot(TOKEN)

timer = Timer(10.0, end_round)

class State(Enum):
    WAITING_FOR_ATTACKER = 1
    FREE_TO_ATTACK = 2
    ATTACKEE_SECOND_RESPONSE = 3
    END_ROUND = 4

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
        self.attackee = 0
        self.state = None
        self.attacked_cards = []
        self.defended_cards = []
        self.played_numbers = []
        self.chosen_card = ''

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
    durak.deck = []
    for i in range(n_decks):
        durak.deck += list(Card)
    random.shuffle(durak.deck)

    # Deal cards
    for i in range(len(durak.players)):
        durak.cards[durak.players[i]] = [str(durak.deck.pop()) for _ in range(7)]
    
    display_cards_info(message)
    play_game()

def launch_attack():
    # Reset
    durak.attacked_cards = []
    durak.defended_cards = []

    durak.state = State.WAITING_FOR_ATTACKER
    reply_keyboard = [durak.cards[durak.players[durak.attacker]]]
    message = 'You are the attacker this round. Choose a card to attack {}.'.format(durak.players[durak.attackee])
    bot.send_message(chat_id=durak.chat_ids[durak.attacker], text=message,
                     reply_markup=ReplyKeyboardMarkup(reply_keyboard))

def attack_card(card):
    for i in range(len(durak.players)):
        if i == durak.attacker:
            message = 'You have chosen to attack {} with {}.'.format(durak.players[durak.attackee], card)
            durak.cards[durak.players[durak.attacker]].remove(card)
            if card[0] not in durak.played_numbers:
                durak.played_numbers.append(card[0])
            reply_keyboard = [durak.cards[durak.players[durak.attacker]]]
        elif i == durak.attackee:
            message = 'You have been attacked by {} with {}.'.format(durak.players[durak.attacker], card)
            keyboard = durak.cards[durak.players[durak.attackee]] + ['Take']
            reply_keyboard = [keyboard]
        else:
            message = '{} has attacked {} with {}.'.format(durak.players[durak.attacker], durak.players[durak.attackee], card)
            reply_keyboard = [durak.cards[durak.players[i]]]
        bot.send_message(chat_id=durak.chat_ids[i], text=message,
                         reply_markup=ReplyKeyboardMarkup(reply_keyboard))
    
    durak.attacked_cards.append(card)
    durak.state = State.FREE_TO_ATTACK

def attack_card_from_anyone(card, user):
    if card[0] not in durak.played_numbers:
        return
    if len(durak.attacked_cards) == min(7, len(durak.cards[durak.players[durak.attackee]])):
        return

    timer.cancel()
    for i in range(len(durak.players)):
        if durak.players[i] == user:
            message = 'You have attacked {} with {}.'.format(durak.players[durak.attackee], card)
            durak.cards[user].remove(card)
            reply_keyboard = [durak.cards[user]]
        elif i == durak.attackee:
            message = '{} has attacked you with {}.'.format(user, card)
            keyboard = durak.cards[durak.players[durak.attackee]] + ['Take']
            reply_keyboard = [keyboard]
        else:
            message = '{} has attacked {} with {}.'.format(user, durak.players[durak.attackee], card)
            reply_keyboard = [durak.cards[durak.players[i]]]
        bot.send_message(chat_id=durak.chat_ids[i], text=message,
                         reply_markup=ReplyKeyboardMarkup(reply_keyboard))

    durak.attacked_cards.append(card)

def compare_cards(card):
    lower_cards = []

    for attacked_card in durak.attacked_cards:
        if attacked_card[1] == durak.trump_suit:
            if card[1] != durak.trump_suit:
                continue
            if Rank(card[0]) > Rank(attacked_card[0]):
                lower_cards.append(attacked_card)
        else:
            if card[1] == durak.trump_suit:
                lower_cards.append(attacked_card)
            elif card[1] != attacked_card[1]:
                continue
                # by now the cards should be same suit
            elif Rank(card[0]) > Rank(attacked_card[0]):
                lower_cards.append(attacked_card)

    return lower_cards

def deflect_attack():
    durak.attackee = (durak.attackee + 1) % len(durak.players)
    while len(durak.cards[durak.players[durak.attackee]]) == 0:
        # Go to the next active player
        durak.attackee = (durak.attackee + 1) % len(durak.players)

    for i in range(len(durak.players)):
        if i == durak.attackee:
            message = 'The attack has been deflected. You are being attacked with {}.'.format(durak.attacked_cards)
            reply_keyboard = [durak.cards[durak.players[durak.attackee]]]
        else:
            message = 'The attack has been deflected. {} is being attacked with {}'.format(durak.players[durak.attackee], durak.attacked_cards)
            reply_keyboard = [durak.cards[durak.players[i]]]
        bot.send_message(chat_id=durak.chat_ids[i], text=message,
                         reply_markup=ReplyKeyboardMarkup(reply_keyboard))
    
def respond_to_attack(card):
    if card[0] == durak.played_numbers[0]:
        if card[1] != durak.trump_suit:
            durak.attacked_cards.append(card)
            deflect_attack()
        else:
            pass
            # TODO: what happens if play the same number but with a trump
    
    elif card == 'Take':
        durak.cards[durak.players[durak.attackee]] += durak.attacked_cards
        for i in range(len(durak.players)):
            if i == durak.attackee:
                message = 'You have taken all cards on the table.'
                reply_keyboard = [durak.cards[durak.players[durak.attackee]]]
            else:
                message = '{} has taken all cards on the table.'.format(durak.players[durak.attackee])
                reply_keyboard = [durak.cards[durak.players[i]]]
            bot.send_message(chat_id=durak.chat_ids[i], text=message,
                            reply_markup=ReplyKeyboardMarkup(reply_keyboard))
        end_round()

    else:
        lower_cards = compare_cards(card)
        if len(lower_cards) == 0:
            return
        else:
            reply_keyboard = [lower_cards]
            message = 'Which card to you want to defend against?'
            bot.send_message(chat_id=durak.chat_ids[durak.attackee], text=message,
                             reply_markup=ReplyKeyboardMarkup(reply_keyboard))
            durak.state = State.ATTACKEE_SECOND_RESPONSE
            durak.chosen_card = card

def choose_card_to_defend(card):
    durak.cards[durak.players[durak.attackee]].remove(durak.chosen_card)
    durak.attacked_cards.remove(card)
    durak.defended_cards.append(card)
    if card[0] not in durak.played_numbers:
        durak.played_numbers.append(card[0])

    for i in range(len(durak.players)):
        if i == durak.attackee:
            message = 'You have defended {} with {}.'.format(card, durak.chosen_card)
            reply_keyboard = [durak.cards[durak.players[durak.attackee]]]
        else:
            message = '{} has defended {} with {}'.format(durak.players[durak.attackee], card, durak.chosen_card)
            reply_keyboard = [durak.cards[durak.players[i]]]
        bot.send_message(chat_id=durak.chat_ids[i], text=message,
                         reply_markup=ReplyKeyboardMarkup(reply_keyboard))
    
    if (len(durak.defended_cards) == 7) or (len(durak.cards[durak.players[durak.attackee]]) == 0):
        end_round()
    else:
        if len(durak.attacked_cards == 0):
            timer.start()
        durak.state = State.FREE_TO_ATTACK

def end_round():
    durak.state = State.END_ROUND
    # TODO: draw cards, report state
            
def validate_string(text):
    pattern = re.compile(r'^(?:[2-9TJQKA])(?:[♣️♦️♥️♠️])$')
    return bool(pattern.match(text)) or (text == 'Take')

def handle_response(update, context):
    if (durak.state == State.WAITING_FOR_ATTACKER) and (update.message.from_user.first_name == durak.players[durak.attacker]):
        if not validate_string(update.message.text):
            return
        attack_card(update.message.text)

    elif (durak.state == State.FREE_TO_ATTACK or durak.state == State.ATTACKEE_SECOND_RESPONSE) and \
            (update.message.from_user.first_name != durak.players[durak.attackee]):
        if not validate_string(update.message.text):
            return
        attack_card_from_anyone(update.message.text, update.message.from_user.first_name)
    
    elif (durak.state == State.FREE_TO_ATTACK) and (update.message.from_user.first_name == durak.players[durak.attackee]):
        if not validate_string(update.message.text):
            return
        respond_to_attack(update.message.text)

    elif (durak.state == State.ATTACKEE_SECOND_RESPONSE) and (update.message.from_user.first_name == durak.players[durak.attackee]):
        if not validate_string(update.message.text):
            return
        choose_card_to_defend(update.message.text)

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