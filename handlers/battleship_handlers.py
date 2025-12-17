# handlers/battleship_handlers.py

from battleship import Game as SeaGame, Board
from db import get_balance, change_balance
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import random
import time

HINT_COST = 5

sea_games = {}
sea_players = {}


def build_sea_field_keyboard(target_board: Board, is_player_a_turn: bool) -> InlineKeyboardMarkup:
    """Создает клавиатуру для поля морского боя
    
    Args:
        target_board: Доска противника
        is_player_a_turn: True, если сейчас ход игрока A
    """
    kb = InlineKeyboardMarkup()
    for r in range(target_board.SIZE):
        row_btns = []
        for c in range(target_board.SIZE):
            ch = target_board.grid[r][c]
            
            # Определяем текст кнопки
            if ch == target_board.HIT:
                text = "💥"
            elif ch == target_board.MISS:
                text = "⚪"
            else:
                # Разные цвета для разных игроков
                text = "🟦" if is_player_a_turn else "⬜"  # A - синий, B - серый
            
            # Определяем callback_data
            if ch in (target_board.HIT, target_board.MISS):
                # В уже прострелянные клетки нельзя стрелять
                callback_data = f"sea_ignore"
            else:
                callback_data = f"sea_cell_{r}_{c}"
                
            row_btns.append(
                InlineKeyboardButton(
                    text=text,
                    callback_data=callback_data,
                )
            )
        kb.row(*row_btns)
    return kb


def render_game_info(game) -> str:
    """Рендерит текстовую информацию о текущем состоянии игры"""
    current_is_a = game.turn == game.player_a_id
    
    if current_is_a:
        title = "🎯 Морской бой. Ход игрока A\n\n"
        # Для игрока A: неизвестное поле синее
        unknown_color = "🟦"
    else:
        title = "🎯 Морской бой. Ход игрока B\n\n"
        # Для игрока B: неизвестное поле серое
        unknown_color = "⬜"
    
    legend = f"{unknown_color} неизвестно | 💥 попадание | ⚪ промах\n" \
             f"Чит-выстрел: /seahint ({HINT_COST}💎)\n" \
             f"/seagiveup - сдаться и завершить игру\n\n"
    
    return title + legend


def get_target_board_and_player(game, user_id):
    """Возвращает доску противника и ID противника для стрельбы"""
    if user_id == game.player_a_id:
        return game.boards[game.player_b_id], game.player_b_id
    else:
        return game.boards[game.player_a_id], game.player_a_id


def update_game_board(bot, game):
    """Обновляет игровое поле в чате с защитой от слишком частых запросов"""
    current_player_id = game.turn
    target_board, _ = get_target_board_and_player(game, current_player_id)
    text = render_game_info(game)
    
    # Определяем, чей сейчас ход для выбора цвета
    is_player_a_turn = (game.turn == game.player_a_id)
    
    try:
        # Добавляем небольшую задержку, чтобы избежать ошибки 429
        time.sleep(0.1)
        
        if hasattr(game, 'message_id') and game.message_id:
            bot.edit_message_text(
                chat_id=game.chat_id,
                message_id=game.message_id,
                text=text,
                reply_markup=build_sea_field_keyboard(target_board, is_player_a_turn)
            )
    except Exception as e:
        print(f"Ошибка при обновлении поля: {e}")


def declare_winner(bot, chat_id, user_id, game):
    """Объявляет победителя и завершает игру"""
    winner_name = "A" if user_id == game.player_a_id else "B"
    
    # Показываем последний ход с цветом победителя
    target_board, _ = get_target_board_and_player(game, user_id)
    text = render_game_info(game)
    
    # Для последнего отображения используем цвет победителя
    is_player_a_winner = (winner_name == "A")
    
    try:
        time.sleep(0.1)
        if hasattr(game, 'message_id') and game.message_id:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=game.message_id,
                text=text,
                reply_markup=build_sea_field_keyboard(target_board, is_player_a_winner)
            )
    except Exception as e:
        print(f"Ошибка при показе последнего хода: {e}")
    
    # Затем объявляем победителя
    time.sleep(0.2)
    bot.send_message(
        chat_id,
        f"🎉🎉🎉 ПОБЕДА! 🎉🎉🎉\n"
        f"Игрок {winner_name} выиграл! 🏆\n"
        f"Все корабли противника потоплены!"
    )
    
    # Очищаем игру
    sea_games.pop(chat_id, None)
    sea_players.pop(chat_id, None)


def register_handlers(bot):
    """Регистрирует все хэндлеры для морского боя"""
    @bot.message_handler(commands=["newsea"])
    def new_sea_game_message(message):
        chat_id = message.chat.id
        if chat_id in sea_games:
            bot.reply_to(message, "Игра уже создана!")
            return

        sea_players[chat_id] = []
        bot.reply_to(
            message,
            "🚢 Морской бой создан!\n"
            "/joinsea - присоединиться (первый A, второй B)\n"
            "Выстрелы делаются через кнопки под полем.",
        )

    @bot.message_handler(commands=["joinsea"])
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

            # Создаем игровое поле в чате (первый ход делает A)
            target_board = game.boards[player_b_id]
            text = render_game_info(game)
            
            # Первый ход делает A, поэтому синие клетки
            msg = bot.send_message(
                chat_id, 
                text, 
                reply_markup=build_sea_field_keyboard(target_board, is_player_a_turn=True)
            )
            game.message_id = msg.message_id

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

        # Проверяем, не игнорируемый ли это callback
        if call.data == "sea_ignore":
            bot.answer_callback_query(call.id, "Сюда уже стреляли!")
            return

        _, _, r_str, c_str = call.data.split("_")  # sea_cell_r_c
        r, c = int(r_str), int(c_str)

        # Получаем доску противника
        target_board, target_player_id = get_target_board_and_player(game, user_id)

        # Проверяем, не стреляли ли уже в эту клетку
        if target_board.grid[r][c] in (target_board.HIT, target_board.MISS):
            bot.answer_callback_query(call.id, "Сюда уже стреляли!")
            return

        # Делаем выстрел
        result = target_board.receive_shot((r, c))
        
        # Немедленно проверяем победу ДО обработки других действий
        if target_board.all_ships_sunk():
            try:
                bot.answer_callback_query(call.id, "ПОБЕДА! Все корабли противника потоплены! 🏆")
                declare_winner(bot, chat_id, user_id, game)
            except Exception as e:
                print(f"Ошибка при объявлении победителя: {e}")
                # Все равно очищаем игру при ошибке
                sea_games.pop(chat_id, None)
                sea_players.pop(chat_id, None)
                bot.send_message(chat_id, f"🎉 Игрок {'A' if user_id == game.player_a_id else 'B'} выиграл! 🏆")
            return

        # Обрабатываем результат выстрела (если игра еще не окончена)
        if result == "miss":
            info = "Мимо. Ход переходит к противнику."
            bot.answer_callback_query(call.id, info)
            
            # Переключаем ход
            game.switch_turn()
            
            # Немедленно обновляем поле в чате для нового стреляющего
            update_game_board(bot, game)
            
        elif result == "hit":
            info = "Попадание! Продолжай стрелять."
            bot.answer_callback_query(call.id, info)
            
            # Обновляем поле (текущий игрок продолжает ход)
            update_game_board(bot, game)
            
        else:  # sunk
            info = "Корабль потоплен! Продолжай стрелять."
            bot.answer_callback_query(call.id, info)
            
            # Обновляем поле (текущий игрок продолжает ход)
            update_game_board(bot, game)

    @bot.callback_query_handler(func=lambda call: call.data == "sea_ignore")
    def handle_sea_ignore(call):
        """Обрабатывает нажатие на уже прострелянную клетку"""
        bot.answer_callback_query(call.id, "Сюда уже стреляли!")

    @bot.message_handler(commands=["seahint"])
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

        # Проверяем, что сейчас ход пользователя
        if user_id != game.turn:
            bot.reply_to(message, "Подсказку можно использовать только во время своего хода!")
            return

        # Пытаемся списать алмазы
        try:
            new_balance = change_balance(user_id, -HINT_COST)
        except ValueError:
            current = get_balance(user_id)
            bot.reply_to(
                message,
                f"Не хватает алмазов. Нужно {HINT_COST}, у тебя {current} 💎.",
            )
            return

        # Определяем целевую доску (подсказка по противнику)
        target_board, target_player_id = get_target_board_and_player(game, user_id)

        # Собираем кандидатов (клетки, куда еще не стреляли)
        candidates = []
        for r in range(target_board.SIZE):
            for c in range(target_board.SIZE):
                ch = target_board.grid[r][c]
                if ch not in (target_board.HIT, target_board.MISS):
                    candidates.append((r, c))

        if not candidates:
            bot.reply_to(message, "Подсказок больше нет: всё поле уже простреляно.")
            return

        # Выбираем случайную клетку и делаем выстрел
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
            f"{text}\nСписано {HINT_COST} алмазов, осталось {new_balance} 💎.",
        )

        # Проверяем победу после подсказки
        if target_board.all_ships_sunk():
            declare_winner(bot, chat_id, user_id, game)
            return

        # Обновляем игровое поле в чате
        update_game_board(bot, game)

        # Если промах в подсказке - переключаем ход
        if result == "miss":
            game.switch_turn()
            update_game_board(bot, game)

    @bot.message_handler(commands=["seagiveup"])
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
        loser_name = "A" if user_id == game.player_a_id else "B"

        bot.send_message(
            chat_id,
            f"Игрок {loser_name} сдался. Победил игрок {winner_name}! 🏆",
        )

        # Удаляем игру
        sea_games.pop(chat_id, None)
        sea_players.pop(chat_id, None)