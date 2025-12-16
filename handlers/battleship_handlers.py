# handlers/battleship_handlers.py

from battleship import Game as SeaGame
from db import get_balance, change_balance
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import random

HINT_COST = 5
ROWS = "ABCDEFGHIJ"

sea_games = {}
sea_players = {}

def build_row_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    buttons = [InlineKeyboardButton(text=row, callback_data=f"sea_row_{row}") for row in ROWS]
    kb.row(*buttons)
    return kb

def build_cell_keyboard(game, target_board, row_char: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    buttons = []
    row = ord(row_char) - ord("A")

    for col in range(1, 11):
        ch = target_board.grid[row][col - 1]
        # пропускаем, если сюда уже стреляли
        if ch in ("X", "·"):
            continue

        buttons.append(
            InlineKeyboardButton(
                text=str(col),
                callback_data=f"sea_cell_{row_char}{col}",
            )
        )
        if len(buttons) == 5:
            kb.row(*buttons)
            buttons = []

    if buttons:
        kb.row(*buttons)

    kb.row(InlineKeyboardButton(text="⬅️ Ряд", callback_data="sea_back_rows"))
    return kb



def register_handlers(bot):
    """Регистрирует все хэндлеры для морского боя"""
    
    @bot.message_handler(commands=['newsea'])
    def new_sea_game_message(message):
        chat_id = message.chat.id
        if chat_id in sea_games:
            bot.reply_to(message, "Игра уже создана!")
            return
        
        sea_players[chat_id] = []
        bot.reply_to(message, "Морской бой создан! 🚢\n"
                              "/joinsea - присоединиться (первый A, второй B)\n"
                              "Выстрелы делаются через кнопки под полем.")
        
    def render_public_board(game) -> str:
        board_a = game.boards[game.player_a_id]
        board_b = game.boards[game.player_b_id]
        current_is_a = (game.turn == game.player_a_id)

        if current_is_a:
            title = "Морской бой. Ход игрока A\n\n"
            enemy_label = "Поле B (стреляешь сюда):\n"
            enemy_board = board_b.renderForOpponent()
        else:
            title = "Морской бой. Ход игрока B\n\n"
            enemy_label = "Поле A (стреляешь сюда):\n"
            enemy_board = board_a.renderForOpponent()

        # ВАЖНО: пустая строка перед `````` чтобы Telegram точно включил моноширинный шрифт
        return (
            title
            + enemy_label
            + "\n```
            + enemy_board
            + "\n```"
        )



    @bot.message_handler(commands=['joinsea'])
    def join_sea_game_message(message):
        chat_id = message.chat.id
        user = message.from_user
        
        if chat_id not in sea_players:
            bot.reply_to(message, "Сначала создай игру: /newsea.")
            return
        
        players = sea_players[chat_id]
        if user.id in players:
            bot.reply_to(message, "Ты уже в игре.")
            return
        
        if len(players) >= 2:
            bot.reply_to(message, "Уже двое в игре!")
            return
        
        players.append(user.id)
        bot.reply_to(message, f"{user.first_name}, ты присоединился! 🎮")

        
        # Если оба играют, начинаем игру
        if len(players) >= 2:
            player_a_id, player_b_id = players
            game = SeaGame(player_a_id, player_b_id)
            game.chat_id = chat_id

            game.auto_place_fleet_for(player_a_id)
            game.auto_place_fleet_for(player_b_id)
            sea_games[chat_id] = game

            text = render_public_board(game)
            msg = bot.send_message(chat_id, text, reply_markup=build_row_keyboard())
            game.message_id = msg.message_id
            

    @bot.callback_query_handler(func=lambda call: call.data.startswith("sea_row_"))
    def handle_row_choice(call):
        chat_id = call.message.chat.id
        user_id = call.from_user.id
        row_char = call.data.split("_", 2)[2]  # "A"..."J"

        if chat_id not in sea_games:
            bot.answer_callback_query(call.id, "Нет активной игры.")
            return

        game = sea_games[chat_id]

        if user_id not in [game.player_a_id, game.player_b_id]:
            bot.answer_callback_query(call.id, "Ты не в этой игре!")
            return

        # определяем доску, по которой стреляем
        if user_id == game.player_a_id:
            target_board = game.boards[game.player_b_id]
        else:
            target_board = game.boards[game.player_a_id]

        # показываем клавиатуру выбора столбца только по ещё не прострелянным клеткам
        bot.edit_message_reply_markup(
            chat_id=chat_id,
            message_id=game.message_id,
            reply_markup=build_cell_keyboard(game, target_board, row_char),
        )
        bot.answer_callback_query(call.id)



    @bot.callback_query_handler(func=lambda call: call.data.startswith("sea_cell_") or call.data == "sea_back_rows")
    def handle_cell_or_back(call):
        chat_id = call.message.chat.id
        user_id = call.from_user.id

        if chat_id not in sea_games:
            bot.answer_callback_query(call.id, "Нет активной игры.")
            return

        game = sea_games[chat_id]

        if call.data == "sea_back_rows":
            # просто вернуться к выбору ряда
            bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=game.message_id,
                reply_markup=build_row_keyboard()
            )
            bot.answer_callback_query(call.id)
            return

        # sea_cell_A5
        coord_text = call.data.split("_", 2)[2]  # "A5"
        row_char = coord_text[0]
        col_str = coord_text[1:]

        # Проверка, что пользователь в игре и его ход
        if user_id not in [game.player_a_id, game.player_b_id]:
            bot.answer_callback_query(call.id, "Ты не в этой игре!")
            return
        if user_id != game.turn:
            bot.answer_callback_query(call.id, "Сейчас не твой ход!")
            return

        # Парсим координаты
        try:
            row = ord(row_char) - ord("A")
            col = int(col_str) - 1
            if not (0 <= row < 10 and 0 <= col < 10):
                raise ValueError
        except ValueError:
            bot.answer_callback_query(call.id, "Неверная клетка.")
            return

        # Выбираем целевую доску, как в handle_shot
        if user_id == game.player_a_id:
            target_board = game.boards[game.player_b_id]
        else:
            target_board = game.boards[game.player_a_id]

        result = target_board.receive_shot((row, col))

        # Проверка победы
        if target_board.all_ships_sunk():
            winner_name = "A" if user_id == game.player_a_id else "B"
            text = render_public_board(game)
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=game.message_id,
                text=text,
                reply_markup=None,
            )
            bot.answer_callback_query(call.id, f"Победа! Игрок {winner_name} выиграл! 🏆")
            sea_games.pop(chat_id, None)
            sea_players.pop(chat_id, None)
            return

        # Обновляем ход: при miss меняем игрока, при hit/sunk — оставляем
        if result == "miss":
            game.switch_turn()
            info = "Мимо."
        elif result == "hit":
            info = "Попадание!"
        else:  # sunk
            info = "Корабль потоплен!"

        # Обновляем текст и возвращаемся к выбору ряда
        text = render_public_board(game)
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=game.message_id,
            text=text,
            reply_markup=build_row_keyboard(),
        )
        bot.answer_callback_query(call.id, info)


        
    @bot.message_handler(commands=['seahint'])
    def sea_hint_handler(message):
        chat_id = message.chat.id
        user_id = message.from_user.id

        # Проверяем, что есть активная игра
        if chat_id not in sea_games:
            bot.reply_to(message, "Нет активной игры. Создай /newsea.")
            return

        game = sea_games[chat_id]

        # Проверяем, что пользователь в этой игре
        if user_id not in [game.player_a_id, game.player_b_id]:
            bot.reply_to(message, "Ты не в этой игре!")
            return

        # Пытаемся списать алмазы
        try:
            new_balance = change_balance(user_id, -HINT_COST)
        except ValueError:
            current = get_balance(user_id)
            bot.reply_to(
                message,
                f"Не хватает алмазов. Нужно {HINT_COST}, у тебя {current} 💎."
            )
            return

        # Определяем целевую доску (подсказка по противнику)
        if user_id == game.player_a_id:
            target_id = game.player_b_id
        else:
            target_id = game.player_a_id
        target_board = game.boards[target_id]

        # Собираем кандидатов
        candidates = []
        for r in range(target_board.SIZE):
            for c in range(target_board.SIZE):
                ch = target_board.grid[r][c]
                if ch in (" ", "O"):
                    candidates.append((r, c))

        if not candidates:
            bot.reply_to(message, "Подсказок больше нет: всё поле уже прострелянo.")
            return

        # Делаем выстрел
        r, c = random.choice(candidates)
        result = target_board.receive_shot((r, c))
        coord_text = f"{chr(ord('A') + r)}{c + 1}"

        if result == "hit":
            text = f"Подсказка: в клетке {coord_text} есть корабль! 🎯"
        elif result == "sunk":
            text = f"Подсказка: вы добили корабль в клетке {coord_text}! 💥"
        else:
            text = f"Подсказка: в клетке {coord_text} пусто. 💧"

        bot.reply_to(
            message,
            f"{text}\nСписано {HINT_COST} алмазов, осталось {new_balance} 💎."
        )

        # Обновляем общее поле в чате
        text_board = render_public_board(game)
        bot.edit_message_text(
            chat_id=game.chat_id,
            message_id=game.message_id,
            text=text_board,
            reply_markup=build_row_keyboard(),
        )


    @bot.message_handler(commands=['seagiveup'])
    def sea_giveup_handler(message):
        chat_id = message.chat.id
        user_id = message.from_user.id

        if chat_id not in sea_games:
            bot.reply_to(message, "Нет активной игры. Создай /newsea.")
            return

        game = sea_games[chat_id]

        if user_id not in [game.player_a_id, game.player_b_id]:
            bot.reply_to(message, "Ты не в этой игре!")
            return

        # Определяем, кто победил
        winner_name = "A" if user_id != game.player_a_id else "B"

        bot.send_message(
            chat_id,
            f"Игрок {'A' if user_id == game.player_a_id else 'B'} сдался. "
            f"Победил игрок {winner_name}! 🏆"
        )

        # Удаляем игру
        sea_games.pop(chat_id, None)
        sea_players.pop(chat_id, None)
