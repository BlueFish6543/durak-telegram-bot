from telegram import Bot, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
from enum import Enum
import logging
import math
import random
import re
from threading import Timer
from poker import Card, Rank
from bot_token import TOKEN

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

bot = Bot(TOKEN)

class State(Enum):
    WAITING_FOR_ATTACKER = 1
    FREE_TO_ATTACK = 2
    ATTACKEE_SECOND_RESPONSE = 3
    DEFLECT_OR_DEFEND = 4
    END_ROUND = 5

class Durak():
    def __init__(self):
        self.players = []
        self.chat_ids = []
        self.cards = {}
        self.deck = []
        self.total_number_of_cards = 0
        self.trump_suit = ''
        self.trump_card = ''
        self.attacker = 0
        self.attackee = 1
        self.state = None
        self.attacked_cards = []
        self.n_attacked_cards = 0
        self.defended_cards = []
        self.played_numbers = []
        self.chosen_card = ''
        self.successfully_defended = False
        self.shown_cards = []
        self.temp_card = ''

def set_timer_time():
    n_active_players = sum(1 for condition in durak.cards.values() if bool(condition))
    if n_active_players == 2:
        return 5
    elif n_active_players == 3:
        return 10
    else:
        return 15

def to_number(card):
    face_cards = {'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
    if card[1] == durak.trump_suit:
        add = 13
    else:
        add = 0
    if card[0].isnumeric():
        return int(card[0]) + add
    elif len(card) == 2:
        return face_cards[card[0]] + add
    else:
        return 28

def format_reply_keyboard(cards_list):
    cards_list.sort(key=to_number)
    if len(cards_list) <= 7:
        return [cards_list]
    else:
        quotient, remainder = divmod(len(cards_list), 7)
        n_rows = quotient + 1
        quotient, remainder = divmod(len(cards_list), n_rows)
        new_list = []
        index = 0
        for i in range(n_rows):
            add = 1 if (i < remainder) else 0
            new_list.append(cards_list[index:index + quotient + add])
            index += quotient + add
        return new_list

def format_defended_cards(cards_list):
    new_list = []
    for i in range(len(cards_list)):
        if (i % 2 == 1):
            continue
        text = '{} -> {}'.format(cards_list[i], cards_list[i + 1])
        new_list.append(text)
    return new_list

def update_players():
    for i in range(len(durak.players) - 1):
        message = '{} has joined the game. Current players: '.format(durak.players[-1])
        for j in range(len(durak.players)):
            message += durak.players[j]
            message += ', '
        message = message[:-2]
        bot.send_message(chat_id=durak.chat_ids[i], text=message)

def start(update, context):
    if durak.state is not None:
        update.message.reply_text('Sorry, a game is already in progress.')
        return

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
    durak.trump_card = str(durak.deck[0])
    update_cards_left()

def start_game(update, context):
    if durak.state is not None:
        update.message.reply_text('Sorry, a game is already in progress.')
        return
    
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
    launch_attack()

def launch_attack():
    # Reset
    durak.attacked_cards = []
    durak.defended_cards = []
    durak.played_numbers = []
    durak.state = State.WAITING_FOR_ATTACKER

    for i in range(len(durak.players)):
        if i == durak.attacker:
            message = 'You are the attacker this round. Choose a card to attack {}, who has {} cards.'.format(durak.players[durak.attackee], len(durak.cards[durak.players[durak.attackee]]))
            reply_keyboard = format_reply_keyboard(durak.cards[durak.players[durak.attacker]])
        elif i == durak.attackee:
            message = 'You are being attacked by {} this round.'.format(durak.players[durak.attacker])
            reply_keyboard = format_reply_keyboard(durak.cards[durak.players[durak.attackee]])
        else:
            message = '{} is attacking {} this round, who has {} cards.'.format(durak.players[durak.attacker], durak.players[durak.attackee], len(durak.cards[durak.players[durak.attackee]]))
            reply_keyboard = format_reply_keyboard(durak.cards[durak.players[i]])
        bot.send_message(chat_id=durak.chat_ids[i], text=message,
                         reply_markup=ReplyKeyboardMarkup(reply_keyboard))

def attack_card(card):
    for i in range(len(durak.players)):
        if i == durak.attacker:
            message = 'You have chosen to attack {} with {}.'.format(durak.players[durak.attackee], card)
            durak.cards[durak.players[durak.attacker]].remove(card)
            if card[0] not in durak.played_numbers:
                durak.played_numbers.append(card[0])
            reply_keyboard = format_reply_keyboard(durak.cards[durak.players[durak.attacker]])
        elif i == durak.attackee:
            message = 'You have been attacked by {} with {}.'.format(durak.players[durak.attacker], card)
            keyboard = durak.cards[durak.players[durak.attackee]] + ['Take']
            reply_keyboard = format_reply_keyboard(keyboard)
        else:
            message = '{} has attacked {} with {}.'.format(durak.players[durak.attacker], durak.players[durak.attackee], card)
            reply_keyboard = format_reply_keyboard(durak.cards[durak.players[i]])
        bot.send_message(chat_id=durak.chat_ids[i], text=message,
                         reply_markup=ReplyKeyboardMarkup(reply_keyboard))
    
    durak.successfully_defended = False
    durak.attacked_cards.append(card)
    durak.n_attacked_cards = 1
    durak.state = State.FREE_TO_ATTACK

def attack_card_from_anyone(card, user):
    if card[0] not in durak.played_numbers:
        return
    if (durak.n_attacked_cards == 7) or len(durak.attacked_cards) == len(durak.cards[durak.players[durak.attackee]]):
        return
    if card not in durak.cards[user]:
        return
    timer.cancel()

    durak.attacked_cards.append(card)
    durak.n_attacked_cards += 1

    for i in range(len(durak.players)):
        if durak.players[i] == user:
            message = 'You have attacked {} with {}.'.format(durak.players[durak.attackee], card)
            durak.cards[user].remove(card)
            reply_keyboard = format_reply_keyboard(durak.cards[user])
        elif i == durak.attackee:
            message = '{} has attacked you with {}.'.format(user, card)
            keyboard = durak.cards[durak.players[durak.attackee]] + ['Take']
            reply_keyboard = format_reply_keyboard(keyboard)
        else:
            message = '{} has attacked {} with {}.'.format(user, durak.players[durak.attackee], card)
            reply_keyboard = format_reply_keyboard(durak.cards[durak.players[i]])
        message += '\nOutstanding cards to defend: {}'.format(durak.attacked_cards)
        message += '\nDefended cards: {}'.format(format_defended_cards(durak.defended_cards))
        bot.send_message(chat_id=durak.chat_ids[i], text=message,
                         reply_markup=ReplyKeyboardMarkup(reply_keyboard))

    durak.successfully_defended = False

def try_again(user):
    message = "Sorry, the attack didn't go through. Please try again."
    for i in range(len(durak.players)):
        if durak.players[i] == user:
            reply_keyboard = format_reply_keyboard(durak.cards[user])
            bot.send_message(chat_id=durak.chat_ids[i], text=message,
                             reply_markup=ReplyKeyboardMarkup(reply_keyboard))
            return

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

def deflect_attack(card):
    old_attackee = durak.attackee
    durak.attackee = (durak.attackee + 1) % len(durak.players)
    while len(durak.cards[durak.players[durak.attackee]]) == 0:
        # Go to the next active player
        durak.attackee = (durak.attackee + 1) % len(durak.players)

    if (card[1] == durak.trump_suit) and (card not in durak.shown_cards):
        add = 0
    else:
        add = 1

    if len(durak.cards[durak.players[durak.attackee]]) < (len(durak.attacked_cards) + add):
        message = 'Unable to deflect. {} only has {} card(s).'.format(durak.players[durak.attackee], len(durak.cards[durak.players[durak.attackee]]))
        durak.attackee = old_attackee
        reply_keyboard = format_reply_keyboard(durak.cards[durak.players[durak.attackee]])
        bot.send_message(chat_id=durak.chat_ids[durak.attackee], text=message,
                         reply_markup=ReplyKeyboardMarkup(reply_keyboard))
        return

    if (card[1] == durak.trump_suit) and (card not in durak.shown_cards):
        text = '{} has shown the card {}\n'.format(durak.players[old_attackee], card)
        durak.shown_cards.append(card)
    else:
        text = ''
        durak.attacked_cards.append(card)
        durak.cards[durak.players[old_attackee]].remove(card)

    for i in range(len(durak.players)):
        message = text
        if i == durak.attackee:
            message += 'The attack has been deflected. You are being attacked with {}.'.format(durak.attacked_cards)
            reply_keyboard = format_reply_keyboard(durak.cards[durak.players[durak.attackee]] + ['Take'])
        else:
            message += 'The attack has been deflected. {} is being attacked with {}'.format(durak.players[durak.attackee], durak.attacked_cards)
            reply_keyboard = format_reply_keyboard(durak.cards[durak.players[i]])
        bot.send_message(chat_id=durak.chat_ids[i], text=message,
                         reply_markup=ReplyKeyboardMarkup(reply_keyboard))

def deflect_or_defend(response):
    if response == 'Deflect':
        durak.state = State.FREE_TO_ATTACK
        deflect_attack(durak.temp_card)
    elif response == 'Defend':
        lower_cards = compare_cards(durak.temp_card)
        if len(lower_cards) == 0:
            durak.state = State.FREE_TO_ATTACK
            return
        else:
            reply_keyboard = format_reply_keyboard(lower_cards)
            message = 'Which card to you want to defend against?'
            bot.send_message(chat_id=durak.chat_ids[durak.attackee], text=message,
                            reply_markup=ReplyKeyboardMarkup(reply_keyboard))
            durak.state = State.ATTACKEE_SECOND_RESPONSE
            durak.chosen_card = durak.temp_card
    
def respond_to_attack(card):
    if card == 'Take':
        durak.cards[durak.players[durak.attackee]] += durak.attacked_cards
        durak.cards[durak.players[durak.attackee]] += durak.defended_cards
        for i in range(len(durak.players)):
            if i == durak.attackee:
                message = 'You have taken all cards on the table.'
                reply_keyboard = format_reply_keyboard(durak.cards[durak.players[durak.attackee]])
            else:
                message = '{} has taken all cards on the table.'.format(durak.players[durak.attackee])
                reply_keyboard = format_reply_keyboard(durak.cards[durak.players[i]])
            bot.send_message(chat_id=durak.chat_ids[i], text=message,
                            reply_markup=ReplyKeyboardMarkup(reply_keyboard))
        end_round()

    elif card[0] == durak.played_numbers[0]:
        if card[1] != durak.trump_suit:
            deflect_attack(card)
        else:
            message = 'Do you want to deflect or defend?'
            reply_keyboard = [['Deflect', 'Defend']]
            bot.send_message(chat_id=durak.chat_ids[durak.attackee], text=message,
                             reply_markup=ReplyKeyboardMarkup(reply_keyboard))
            durak.temp_card = card
            durak.state = State.DEFLECT_OR_DEFEND

    else:
        lower_cards = compare_cards(card)
        if len(lower_cards) == 0:
            return
        else:
            reply_keyboard = format_reply_keyboard(lower_cards)
            message = 'Which card to you want to defend against?'
            bot.send_message(chat_id=durak.chat_ids[durak.attackee], text=message,
                             reply_markup=ReplyKeyboardMarkup(reply_keyboard))
            durak.state = State.ATTACKEE_SECOND_RESPONSE
            durak.chosen_card = card

def choose_card_to_defend(card):
    global timer
    
    durak.cards[durak.players[durak.attackee]].remove(durak.chosen_card)
    durak.attacked_cards.remove(card)
    durak.defended_cards.append(card)
    durak.defended_cards.append(durak.chosen_card)
    if durak.chosen_card[0] not in durak.played_numbers:
        durak.played_numbers.append(durak.chosen_card[0])

    for i in range(len(durak.players)):
        if i == durak.attackee:
            message = 'You have defended {} with {}.'.format(card, durak.chosen_card)
            reply_keyboard = format_reply_keyboard(durak.cards[durak.players[durak.attackee]] + ['Take'])
        else:
            message = '{} has defended {} with {}'.format(durak.players[durak.attackee], card, durak.chosen_card)
            reply_keyboard = format_reply_keyboard(durak.cards[durak.players[i]])
        message += '\nOutstanding cards to defend: {}'.format(durak.attacked_cards)
        message += '\nDefended cards: {}'.format(format_defended_cards(durak.defended_cards))
        bot.send_message(chat_id=durak.chat_ids[i], text=message,
                         reply_markup=ReplyKeyboardMarkup(reply_keyboard))
    
    if (len(durak.defended_cards) == 14) or (len(durak.cards[durak.players[durak.attackee]]) == 0):
        successful_defend()
    else:
        if len(durak.attacked_cards) == 0:
            timer = Timer(set_timer_time(), successful_defend)
            timer.start()
        durak.state = State.FREE_TO_ATTACK

def print_status(update, context):
    message = ''
    message += 'Attacker: {}\n'.format(durak.players[durak.attacker])
    message += 'Attackee: {}\n'.format(durak.players[durak.attackee])
    for i in range(len(durak.players)):
        message += 'Player {}: {} who has {} cards\n'.format(i + 1, durak.players[i], len(durak.cards[durak.players[i]]))
    message += 'Number of cards left: {}\n'.format(len(durak.deck))
    message += 'Trump card: {}'.format(durak.trump_card)
    for i in range(len(durak.players)):
        bot.send_message(chat_id=durak.chat_ids[i], text=message)    

def successful_defend():
    global timer
    durak.successfully_defended = True
    end_round()
    timer = Timer(set_timer_time(), successful_defend)

def end_round():
    durak.state = State.END_ROUND
    message = 'Round has ended.\n'
    
    # Draw cards, if any
    for i in range(len(durak.players)):
        index = (durak.attacker + i) % len(durak.players)
        draw = 0
        while (len(durak.cards[durak.players[index]]) < 7) and (len(durak.deck) > 0):
            # Draw cards
            durak.cards[durak.players[index]] += [str(durak.deck.pop())]
            draw += 1
        if len(durak.cards[durak.players[index]]) > 0:
            message += '{} has drawn {} card(s) and has {} card(s) left.\n'.format(durak.players[index], draw, len(durak.cards[durak.players[index]]))
        else:
            message += '{} has finished.\n'.format(durak.players[index])
    
    message += 'There are {} card(s) left in the deck.'.format(len(durak.deck))
    for i in range(len(durak.players)):
        reply_keyboard = format_reply_keyboard(durak.cards[durak.players[i]])
        bot.send_message(chat_id=durak.chat_ids[i], text=message,
                         reply_markup=ReplyKeyboardMarkup(reply_keyboard))
    
    # Check if game has finished
    n_active_players = sum(1 for condition in durak.cards.values() if bool(condition))
    if n_active_players == 1:
        end_game()
        return
    
    # Change attacker and attackee
    if durak.successfully_defended:
        durak.attacker = durak.attackee
        while len(durak.cards[durak.players[durak.attacker]]) == 0:
            # Go to the next active player
            durak.attacker = (durak.attacker + 1) % len(durak.players)
    else:
        durak.attacker = (durak.attackee + 1) % len(durak.players)
        while len(durak.cards[durak.players[durak.attacker]]) == 0:
            # Go to the next active player
            durak.attackee = (durak.attacker + 1) % len(durak.players)
    durak.attackee = (durak.attacker + 1) % len(durak.players)
    while len(durak.cards[durak.players[durak.attackee]]) == 0:
        # Go to the next active player
        durak.attackee = (durak.attackee + 1) % len(durak.players)
    
    launch_attack()

def end_game():
    loser = None
    for i in range(len(durak.players)):
        if bool(durak.cards[durak.players[i]]):
            loser = durak.players[i]
            break
    message = 'The game has ended. The loser is {}. Thanks for playing! Type /start to join a new game.'.format(loser)
    for i in range(len(durak.players)):
        bot.send_message(chat_id=durak.chat_ids[i], text=message)
    # Reset
    durak.__init__()

def validate_string(text):
    pattern = re.compile(r'^(?:[2-9TJQKA])(?:[♣️♦️♥️♠️])$')
    return bool(pattern.match(text)) or (text == 'Take') or (text == 'Deflect') or (text == 'Defend')

def error(update, context):
    logger.warning('Update "%s" caused error "%s"', update, context.error)

def reset(update, context):
    global durak, timer
    for i in range(len(durak.players)):
        message = 'Game has been reset. Type /start to join.'
        bot.send_message(chat_id=durak.chat_ids[i], text=message)
    durak = Durak()
    timer = Timer(set_timer_time(), successful_defend)

def handle_response(update, context):
    if not validate_string(update.message.text):
        return

    try:
        if (durak.state == State.WAITING_FOR_ATTACKER) and (update.message.from_user.first_name == durak.players[durak.attacker]):
            attack_card(update.message.text)

        elif (durak.state == State.FREE_TO_ATTACK) and (update.message.from_user.first_name != durak.players[durak.attackee]):
            attack_card_from_anyone(update.message.text, update.message.from_user.first_name)

        elif (durak.state in [State.ATTACKEE_SECOND_RESPONSE, State.DEFLECT_OR_DEFEND]) and \
                (update.message.from_user.first_name != durak.players[durak.attackee]):
            try_again(update.message.from_user.first_name)
        
        elif (durak.state == State.FREE_TO_ATTACK) and (update.message.from_user.first_name == durak.players[durak.attackee]):
            respond_to_attack(update.message.text)

        elif (durak.state == State.ATTACKEE_SECOND_RESPONSE) and (update.message.from_user.first_name == durak.players[durak.attackee]):
            if update.message.text not in durak.attacked_cards:
                return
            choose_card_to_defend(update.message.text)
        
        elif (durak.state == State.DEFLECT_OR_DEFEND) and (update.message.from_user.first_name == durak.players[durak.attackee]):
            deflect_or_defend(update.message.text)
        
        else:
            # Ignore message
            pass
    
    except Exception as e:
        print(e)

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('startgame', start_game))
    dp.add_handler(CommandHandler('reset', reset))
    dp.add_handler(CommandHandler('status', print_status))
    dp.add_handler(MessageHandler(Filters.text, handle_response))
    dp.add_error_handler(error)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    durak = Durak()
    timer = Timer(set_timer_time(), successful_defend)
    main()