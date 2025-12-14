# handlers/tictactoe_handlers.py

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from tictactoe import empty_board, board_text, check_winner, next_symbol

# Глобальные переменные (общие для всех игр)
games = {}
stats = {}

def build_keyboard(board):
    markup = InlineKeyboardMarkup()
    for i in range(3):
        row = []
        for j in range(3):
            text = board[i][j] if board[i][j] != ' ' else ' '
            row.append(InlineKeyboardButton(text=text, callback_data=f"move:{i}:{j}"))
        markup.row(*row)
    return markup

def update_stats(winner_id, loser_id, draw=False):
    """Обновить статистику"""
    def ensure_user(userid):
        if userid not in stats:
            stats[userid] = {'wins': 0, 'losses': 0, 'draws': 0}
    
    if draw:
        for uid in [winner_id, loser_id]:
            if uid is None:
                continue
            ensure_user(uid)
            stats[uid]['draws'] += 1
    else:
        if winner_id is not None:
            ensure_user(winner_id)
            stats[winner_id]['wins'] += 1
        if loser_id is not None:
            ensure_user(loser_id)
            stats[loser_id]['losses'] += 1

def register_handlers(bot):
    """Регистрирует все хэндлеры для крестиков-ноликов"""
    
    @bot.message_handler(commands=['newgame'])
    def new_game_message(message):
        chat_id = message.chat.id
        games[chat_id] = {
            'board': empty_board(),
            'players': {},
            'turn': 'X',
            'message_id': None,
        }
        bot.reply_to(message, "Игра создана! ✅\n"
                              "/join - присоединиться (первый X, второй O)\n")

    @bot.message_handler(commands=['join'])
    def join_message(message):
        chat_id = message.chat.id
        user = message.from_user
        
        if chat_id not in games:
            bot.reply_to(message, "Сначала создай игру: /newgame.")
            return
        
        game = games[chat_id]
        players = game['players']
        
        if user.id in players:
            bot.reply_to(message, f"Ты уже играешь за {players[user.id]}.")
            return
        
        if len(players) >= 2:
            bot.reply_to(message, "Уже двое в игре!")
            return
        
        symbol = 'X' if 'X' not in players.values() else 'O'
        players[user.id] = symbol
        bot.reply_to(message, f"{user.first_name}, ты играешь за {symbol}.")
        
        if len(players) >= 2:
            text = "Игра началась! ✅\n"
            text += f"Ходит '{game['turn']}'.\n\n"
            text += board_text(game['board'])
            msg = bot.send_message(chat_id, text, reply_markup=build_keyboard(game['board']))
            game['message_id'] = msg.message_id

    @bot.callback_query_handler(func=lambda call: call.data.startswith('move'))
    def handle_move(call):
        chat_id = call.message.chat.id
        user = call.from_user
        
        if chat_id not in games:
            bot.answer_callback_query(call.id, "Игра не найдена!")
            return
        
        game = games[chat_id]
        players = game['players']
        
        if user.id not in players:
            bot.answer_callback_query(call.id, "Ты не в этой игре!", show_alert=True)
            return
        
        symbol = players[user.id]
        if symbol != game['turn']:
            bot.answer_callback_query(call.id, "Не твой ход!", show_alert=True)
            return
        
        _, si, sj = call.data.split(':')
        i, j = int(si), int(sj)
        board = game['board']
        
        if board[i][j] != ' ':
            bot.answer_callback_query(call.id, "Клетка уже занята!", show_alert=True)
            return
        
        board[i][j] = symbol
        result = check_winner(board)
        
        if result == 'draw':
            player_ids = list(players.keys())
            if len(player_ids) == 2:
                update_stats(player_ids[0], player_ids[1], draw=True)
            
            text = "Ничья! 🤝\n"
            text += board_text(game['board'])
            bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=text)
            games.pop(chat_id, None)
            bot.answer_callback_query(call.id)
            return
        
        elif result in ['X', 'O']:
            player_ids = list(players.keys())
            if len(player_ids) == 2:
                if result == players[player_ids[0]]:
                    update_stats(player_ids[0], player_ids[1], draw=False)
                else:
                    update_stats(player_ids[1], player_ids[0], draw=False)
            
            text = f"{result} выиграл! 🎉\n"
            text += board_text(game['board'])
            bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=text)
            games.pop(chat_id, None)
            bot.answer_callback_query(call.id)
            return
        
        game['turn'] = next_symbol(symbol)
        text = f"Ходит '{game['turn']}'.\n\n"
        text += board_text(board)
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=text, reply_markup=build_keyboard(board))
        bot.answer_callback_query(call.id)
