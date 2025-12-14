import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from battleship import Game as SeaGame
import time
import requests
import os

import logging
import sys

# ... после импортов ...

# Проверяем, не запущен ли уже бот
try:
    import requests
    # Быстрая проверка
    test_response = requests.get(f"https://api.telegram.org/bot{TOKEN}/getMe", timeout=5)
    if test_response.status_code == 200:
        print("✓ Telegram API доступен")
except Exception as e:
    print(f"✗ Ошибка доступа к Telegram API: {e}")
    
# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

print(">>> bot script import OK")

# ВСТАВЬ СВОЙ ТОКЕН
TOKEN = os.environ.get("TOKEN")

if not TOKEN:
    print("ERROR: TOKEN not found in environment variables!")
    exit(1)

bot = telebot.TeleBot(TOKEN, parse_mode=None)

# chat_id -> state
games = {}
sea_games = {}  # chat_id -> SeaGame
sea_players = {}  # chat_id -> list[user_id]

# Статистика игроков: {user_id: {"wins": int, "losses": int, "draws": int}}
stats = {}

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

def update_stats(winner_id, loser_id, draw=False):
    """Обновляет статистику игроков по итогам партии."""
    def ensure(user_id):
        if user_id not in stats:
            stats[user_id] = {"wins": 0, "losses": 0, "draws": 0}

    if draw:
        # Ничья: увеличиваем счётчик для обоих игроков
        for uid in (winner_id, loser_id):
            if uid is None:
                continue
            ensure(uid)
            stats[uid]["draws"] += 1
    else:
        # Есть победитель и проигравший
        if winner_id is not None:
            ensure(winner_id)
            stats[winner_id]["wins"] += 1
        if loser_id is not None:
            ensure(loser_id)
            stats[loser_id]["losses"] += 1

@bot.message_handler(commands=["start", "help"])
def start(message):
    print(">>> /start from", message.from_user.id)
    bot.reply_to(
        message,
        "Привет! Бот крестики-нолики для совещаний.\n\n"
        "/newgame — создать игру в этом чате\n"
        "/join — присоединиться (первый X, второй O)\n"
        "/stats — твоя статистика и топ-3 по победам\n"
        "/newsea — создать игру Морской бой\n"
        "/joinsea — присоединиться к Морскому бою\n"
        "/shot — сделать выстрел в Морском бою (например, /shot A5)"
    )

@bot.message_handler(commands=["stats"])
def handle_stats(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # личная статистика
    user_stats = stats.get(user_id, {"wins": 0, "losses": 0, "draws": 0})

    text = (
        "Твоя статистика:\n"
        f"Победы: {user_stats['wins']}\n"
        f"Поражения: {user_stats['losses']}\n"
        f"Ничьи: {user_stats['draws']}\n\n"
    )

    # формируем топ-3 по победам
    leaderboard = [
        (uid, data["wins"])
        for uid, data in stats.items()
        if data["wins"] > 0
    ]

    if leaderboard:
        leaderboard.sort(key=lambda x: x[1], reverse=True)
        top3 = leaderboard[:3]

        text += "Топ-3 по победам:\n"
        for place, (uid, wins) in enumerate(top3, start=1):
            marker = " (ты)" if uid == user_id else ""
            text += f"{place}. {uid}: {wins} побед{marker}\n"
    else:
        text += "Пока нет ни одной победы, таблица лидеров будет позже.\n"

    bot.reply_to(message, text)

@bot.message_handler(commands=["newgame"])
def new_game(message):
    chat_id = message.chat.id
    games[chat_id] = {
        "board": empty_board(),
        "players": {},
        "turn": "X",
        "message_id": None,
    }
    bot.reply_to(
        message,
        "Новая игра создана!\n"
        "Первый, кто напишет /join, будет X.\n"
        "Второй /join — будет O.",
    )

@bot.message_handler(commands=["newsea"])
def new_sea_game(message):
    chat_id = message.chat.id

    if chat_id in sea_games:
        bot.reply_to(message, "Игра морской бой уже создана в этом чате.")
        return

    sea_players[chat_id] = []
    bot.reply_to(
        message,
        "Новая игра Морской бой создана!\n"
        "Первый, кто напишет /joinsea, станет игроком A.\n"
        "Второй /joinsea — игроком B.",
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

    if user.id in players:
        bot.reply_to(message, f"Ты уже играешь за '{players[user.id]}'.")
        return

    if len(players) >= 2:
        bot.reply_to(message, "В этой игре уже два игрока.")
        return

    symbol = "X" if "X" not in players.values() else "O"
    players[user.id] = symbol
    bot.reply_to(message, f"{user.first_name} играет за '{symbol}'.")

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

@bot.message_handler(commands=["joinsea"])
def join_sea_game(message):
    chat_id = message.chat.id
    user = message.from_user

    if chat_id not in sea_players:
        bot.reply_to(message, "Сначала создайте игру командой /newsea.")
        return

    players = sea_players[chat_id]

    if user.id in players:
        bot.reply_to(message, "Ты уже участвуешь в этой игре.")
        return

    if len(players) >= 2:
        bot.reply_to(message, "В этой игре уже два игрока.")
        return

    players.append(user.id)
    bot.reply_to(message, f"{user.first_name} присоединился к Морскому бою.")

    if len(players) == 2:
        player_a_id, player_b_id = players
        game = SeaGame(player_a_id, player_b_id)
        game.auto_place_fleet_for(player_a_id)
        game.auto_place_fleet_for(player_b_id)
        sea_games[chat_id] = game

        bot.send_message(
            chat_id,
            "Флот для обоих игроков расставлен автоматически.\n"
            "Игрок A ходит первым. Используйте команду /shot для выстрела (например, /shot A5).",
        )

@bot.message_handler(commands=["shot"])
def handle_shot(message):
    """Обработка выстрела в Морском бою."""
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if chat_id not in sea_games:
        bot.reply_to(message, "Нет активной игры в Морской бой. Создайте её командой /newsea.")
        return
    
    game = sea_games[chat_id]
    
    # Проверяем, участвует ли игрок в игре
    if user_id not in [game.player_a_id, game.player_b_id]:
        bot.reply_to(message, "Вы не участвуете в этой игре.")
        return
    
    # Проверяем, чей сейчас ход
    if user_id != game.turn:
        bot.reply_to(message, "Сейчас не ваш ход.")
        return
    
    # Парсим координаты
    try:
        _, coord_text = message.text.split(maxsplit=1)
        coord_text = coord_text.strip().upper()
        
        # Проверяем формат координат (например, "A5")
        if len(coord_text) < 2:
            raise ValueError
        
        col_char = coord_text[0]
        row_str = coord_text[1:]
        
        # Преобразуем букву в число (A=0, B=1, ...)
        row = ord(col_char) - ord('A')
        if row < 0 or row >= 10:
            raise ValueError
            
        # Преобразуем номер столбца (1-based в 0-based)
        col = int(row_str) - 1
        if col < 0 or col >= 10:
            raise ValueError
            
    except (ValueError, IndexError):
        bot.reply_to(message, "Неверный формат координат. Используйте формат: /shot A5")
        return
    
    # Определяем, в кого стреляем
    if user_id == game.player_a_id:
        target_id = game.player_b_id
        target_board = game.boards[target_id]
    else:
        target_id = game.player_a_id
        target_board = game.boards[target_id]
    
    # Выполняем выстрел
    result = target_board.receive_shot((row, col))
    
    # Формируем сообщение
    response = f"Выстрел по {coord_text}: "
    if result == "miss":
        response += "промах!"
    elif result == "hit":
        response += "попадание!"
    elif result == "sunk":
        response += "корабль потоплен!"
    
    # Отправляем результат
    bot.reply_to(message, response)
    
    # Проверяем конец игры
    if target_board.all_ships_sunk():
        winner_name = "Игрок A" if user_id == game.player_a_id else "Игрок B"
        bot.send_message(chat_id, f"🎉 {winner_name} победил! Игра окончена.")
        
        # Обновляем статистику (пока только для крестиков-ноликов)
        update_stats(user_id, target_id, draw=False)
        
        # Удаляем игру
        sea_games.pop(chat_id, None)
        sea_players.pop(chat_id, None)
        return
    
    # Передаем ход другому игроку
    game.switch_turn()
    
    # Показываем состояние игры
    next_player = "Игрок A" if game.turn == game.player_a_id else "Игрок B"
    bot.send_message(chat_id, f"Следующий ход: {next_player}")

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
        player_ids = list(players.keys())
        if len(player_ids) == 2:
            update_stats(player_ids[0], player_ids[1], draw=True)

        text = "Ничья!\n\n" + board_text(board)
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=text,
        )
        games.pop(chat_id, None)
        bot.answer_callback_query(call.id)
        return

    elif result in ("X", "O"):
        player_ids = list(players.keys())
        if len(player_ids) == 2:
            if result == players[player_ids[0]]:
                winner_id = player_ids[0]
                loser_id = player_ids[1]
            else:
                winner_id = player_ids[1]
                loser_id = player_ids[0]

            update_stats(winner_id, loser_id, draw=False)

        text = f"Победил '{result}'!\n\n" + board_text(board)
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=text,
        )
        games.pop(chat_id, None)
        bot.answer_callback_query(call.id)
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

def main():
    logger.info("Bot starting...")
    print(">>> Bot started")
    
    # Принудительно закрываем все предыдущие сессии
    try:
        import requests
        response = requests.post(f"https://api.telegram.org/bot{TOKEN}/close", timeout=5)
        logger.info(f"Closed previous bot sessions: {response.status_code}")
        time.sleep(3)  # Даем время закрыться
    except Exception as e:
        logger.info(f"No previous sessions or error: {e}")
    
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            logger.info(f"Starting polling (attempt {retry_count + 1}/{max_retries})...")
            bot.infinity_polling(
                timeout=60, 
                long_polling_timeout=60,
                skip_pending=True,  # Пропустить старые сообщения
                restart_on_change=False  # Не перезапускать при изменении
            )
            
        except Exception as e:
            error_str = str(e)
            
            # Критическая ошибка - другой бот уже запущен
            if "409" in error_str or "Conflict" in error_str:
                logger.error(f"CRITICAL: Another bot instance is running! Error: {error_str}")
                print("CRITICAL: Another bot instance detected. This bot will exit.")
                
                # Попробуем закрыть сессии конкурента
                try:
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/close", timeout=5)
                    time.sleep(2)
                except:
                    pass
                    
                # Выходим полностью
                return
                
            # Обычные сетевые ошибки
            elif "Connection" in error_str or "reset" in error_str or "timeout" in error_str:
                logger.warning(f"Network error: {e}, retrying in 10 seconds...")
                time.sleep(10)
                retry_count += 1
                continue
                
            else:
                logger.error(f"Unexpected error: {e}")
                time.sleep(5)
                retry_count += 1
                continue
    
    logger.error(f"Failed after {max_retries} attempts. Exiting.")
    print(">>> Bot stopped after multiple failures")

if __name__ == "__main__":
    main()