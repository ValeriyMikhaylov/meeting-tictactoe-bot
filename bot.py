import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ВСТАВЬ СВОЙ ТОКЕН
import os
TOKEN = os.environ.get("TOKEN")

bot = telebot.TeleBot(TOKEN, parse_mode=None)

# chat_id -> state
games = {}


def empty_board():
    return [[" " for _ in range(3)] for _ in range(3)]


def board_text(board):
    lines = []
    for row in board:
        lines.append(" | ".join(cell if cell != " " else "·" for cell in row))
    return "\n---------\n".join(lines)


def build_keyboard(board):
    markup = InlineKeyboardMarkup()
    for i in range(3):
        row = []
        for j in range(3):
            text = board[i][j] if board[i][j] != " " else " "
            row.append(InlineKeyboardButton(text=text, callback_data=f"move:{i}:{j}"))
        markup.row(*row)
    return markup


def check_winner(board):
    lines = []
    for i in range(3):
        lines.append(board[i])
        lines.append([board[0][i], board[1][i], board[2][i]])
    lines.append([board[0][0], board[1][1], board[2][2]])
    lines.append([board[0][2], board[1][1], board[2][0]])

    for line in lines:
        if line[0] != " " and line.count(line[0]) == 3:
            return line[0]

    if all(cell != " " for row in board for cell in row):
        return "draw"

    return None


def next_symbol(sym):
    return "O" if sym == "X" else "X"


@bot.message_handler(commands=["start", "help"])
def start(message):
    bot.reply_to(
        message,
        "Привет! Бот крестики‑нолики для совещаний.\n\n"
        "/newgame — создать игру в этом чате\n"
        "/join — присоединиться (первый X, второй O)",
    )


@bot.message_handler(commands=["newgame"])
def new_game(message):
    chat_id = message.chat.id
    games[chat_id] = {
        "board": empty_board(),
        "players": {},  # user_id -> 'X'/'O'
        "turn": "X",
        "message_id": None,
    }
    bot.reply_to(
        message,
        "Новая игра создана!\n"
        "Первый, кто напишет /join, будет X.\n"
        "Второй /join — будет O.",
    )


@bot.message_handler(commands=["join"])
def join(message):
    chat_id = message.chat.id
    user = message.from_user

    if chat_id not in games:
        bot.reply_to(message, "Сначала создайте игру командой /newgame.")
        return

    game = games[chat_id]
    players = game["players"]

    # если этого пользователя уже записали – просто говорим, за кого он играет
    if user.id in players:
        bot.reply_to(message, f"Ты уже играешь за '{players[user.id]}'.")
        return

    # если свободных мест нет
    if len(players) >= 2:
        bot.reply_to(message, "В этой игре уже два игрока.")
        return

    # назначаем символ первому и второму игроку
    symbol = "X" if "X" not in players.values() else "O"
    players[user.id] = symbol
    bot.reply_to(message, f"{user.first_name} играет за '{symbol}'.")

    # когда набралось ровно два игрока – рисуем поле
    if len(players) == 2:
        text = "Игра началась!\n"
        text += f"Ходит '{game['turn']}'.\n\n"
        text += board_text(game["board"])
        msg = bot.send_message(
            chat_id,
            text,
            reply_markup=build_keyboard(game["board"])
        )
        game["message_id"] = msg.message_id


@bot.callback_query_handler(func=lambda call: call.data.startswith("move:"))
def handle_move(call):
    chat_id = call.message.chat.id
    user = call.from_user

    if chat_id not in games:
        bot.answer_callback_query(call.id, "Игра не найдена.")
        return

    game = games[chat_id]
    players = game["players"]

    if user.id not in players:
        bot.answer_callback_query(call.id, "Ты не участвуешь в игре.", show_alert=True)
        return

    symbol = players[user.id]
    if symbol != game["turn"]:
        bot.answer_callback_query(call.id, "Сейчас ход другого игрока.", show_alert=True)
        return

    _, si, sj = call.data.split(":")
    i, j = int(si), int(sj)

    board = game["board"]
    if board[i][j] != " ":
        bot.answer_callback_query(call.id, "Клетка уже занята.", show_alert=True)
        return

    board[i][j] = symbol

    result = check_winner(board)
    if result == "draw":
        text = "Ничья!\n\n" + board_text(board)
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=text,
        )
        games.pop(chat_id, None)
        return
    elif result in ("X", "O"):
        text = f"Победил '{result}'!\n\n" + board_text(board)
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=text,
        )
        games.pop(chat_id, None)
        return

    # Игра продолжается
    game["turn"] = next_symbol(symbol)
    text = f"Ходит '{game['turn']}'.\n\n" + board_text(board)
    bot.edit_message_text(
        chat_id=chat_id,
        message_id=call.message.message_id,
        text=text,
        reply_markup=build_keyboard(board),
    )
    bot.answer_callback_query(call.id)


import time
import requests

def main():
    print("Bot started")
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except requests.exceptions.ConnectionError:
            print("Connection error, retrying in 5 seconds...")
            time.sleep(5)
        except Exception as e:
            print(f"Unexpected error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
