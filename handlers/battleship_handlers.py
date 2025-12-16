# handlers/battleship_handlers.py

from battleship import Game as SeaGame, Board
from db import get_balance, change_balance
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import random

HINT_COST = 5
ROWS = "ABCDEFGHIJ"

sea_games = {}
sea_players = {}

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
        current_is_a = (game.turn == game.player_a_id)
        if current_is_a:
            title = "Морской бой. Ход игрока A\n\n"
            enemy_label = "Стреляешь по полю B:\n"
        else:
            title = "Морской бой. Ход игрока B\n\n"
            enemy_label = "Стреляешь по полю A:\n"
        legend = "⬜ неизвестно | 💥 попадание | ⚪ промах\n\n"
        return title + legend + enemy_label


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

            # первый ход делает A по полю B
            target_board = game.boards[player_b_id]
            text = render_public_board(game)
            msg = bot.send_message(chat_id, text, reply_markup=build_sea_field_keyboard(target_board))
            game.message_id = msg.message_id

           
        def build_sea_field_keyboard(target_board: Board) -> InlineKeyboardMarkup:
        kb = InlineKeyboardMarkup()
        for r in range(target_board.SIZE):  # SIZE = 8
            row_btns = []
            for c in range(target_board.SIZE):
                ch = target_board.grid[r][c]
                if ch == target_board.HIT:
                    text = "💥"
                elif ch == target_board.MISS:
                    text = "⚪"
                else:
                    text = "⬜"  # ещё не стреляли / скрытый корабль
                row_btns.append(
                    InlineKeyboardButton(
                        text=text,
                        callback_data=f"sea_cell_{r}_{c}",
                    )
                )
            kb.row(*row_btns)
        return kb



@bot.callback_query_handler(func=lambda call: call.data.startswith("sea_cell_"))
def handle_sea_cell(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id

    if chat_id not in sea_games:
        bot.answer_callback_query(call.id, "Нет активной игры.")
        return

    game = sea_games[chat_id]

    if user_id not in [game.player_a_id, game.player_b_id]:
        bot.answer_callback_query(call.id, "Ты не в этой игре!")
        return

    if user_id != game.turn:
        bot.answer_callback_query(call.id, "Сейчас не твой ход!")
        return

    _, _, r_str, c_str = call.data.split("_")  # sea_cell_r_c
    r, c = int(r_str), int(c_str)

    # выбираем доску противника
    if user_id == game.player_a_id:
        target_id = game.player_b_id
    else:
        target_id = game.player_a_id

    target_board = game.boards[target_id]

    result = target_board.receive_shot((r, c))

    # проверка победы
    if target_board.all_ships_sunk():
        winner_name = "A" if user_id == game.player_a_id else "B"
        text = render_public_board(game)
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=game.message_id,
            text=text,
            reply_markup=build_sea_field_keyboard(target_board),
        )
        bot.answer_callback_query(call.id, f"Победа! Игрок {winner_name} выиграл! 🏆")
        sea_games.pop(chat_id, None)
        sea_players.pop(chat_id, None)
        return

    if result == "miss":
        game.switch_turn()
        info = "Мимо."
    elif result == "hit":
        info = "Попадание!"
    else:
        info = "Корабль потоплен!"

    text = render_public_board(game)
    bot.edit_message_text(
        chat_id=chat_id,
        message_id=game.message_id,
        text=text,
        reply_markup=build_sea_field_keyboard(target_board),
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

        # Собираем кандидатов (используем константы Board)
        candidates = []
        for r in range(target_board.SIZE):
            for c in range(target_board.SIZE):
                ch = target_board.grid[r][c]
                if ch in (target_board.EMPTY, target_board.SHIP):
                    candidates.append((r, c))

        if not candidates:
            bot.reply_to(message, "Подсказок больше нет: всё поле уже простреляно.")
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
        # подсказка всегда по доске противника относительно того, кто вызывал
        target_board = game.boards[target_id]
        bot.edit_message_text(
            chat_id=game.chat_id,
            message_id=game.message_id,
            text=text_board,
            reply_markup=build_sea_field_keyboard(target_board),
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
