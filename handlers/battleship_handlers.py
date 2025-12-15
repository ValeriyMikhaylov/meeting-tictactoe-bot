# handlers/battleship_handlers.py

from battleship import Game as SeaGame
from db import get_balance, change_balance
import random

HINT_COST = 5

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
                              "/shot (Координаты от A1 до J10) - выстрел, например /shot A5.")

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

        # Вместо лички лучше подсказка прямо в группе:
        bot.reply_to(
            message,
            "Если бот не может написать тебе поле в личку, открой диалог с ботом и нажми Start."
        )

        
        # Если оба играют, начинаем игру
        if len(players) >= 2:
            player_a_id, player_b_id = players
            game = SeaGame(player_a_id, player_b_id)
            game.auto_place_fleet_for(player_a_id)
            game.auto_place_fleet_for(player_b_id)
            sea_games[chat_id] = game
            
            # Отправляем доски каждому игроку в личку
            send_boards(bot, game)
            
            bot.send_message(chat_id, "Игра началась! 🚢\nИгрок A начинает. /shot A5")

    @bot.message_handler(commands=['shot'])
    def handle_shot(message):
        """Обработка выстрелов в Морском бое"""
        chat_id = message.chat.id
        user_id = message.from_user.id
        
        if chat_id not in sea_games:
            bot.reply_to(message, "Нет активной игры. Создай /newsea.")
            return
        
        game = sea_games[chat_id]
        
        # Проверяем, что пользователь в игре
        if user_id not in [game.player_a_id, game.player_b_id]:
            bot.reply_to(message, "Ты не в этой игре!")
            return
        
        # Проверяем, чей ход
        if user_id != game.turn:
            bot.reply_to(message, "Сейчас не твой ход!")
            return
        
        # Парсим координаты
        try:
            _, coord_text = message.text.split(maxsplit=1)
            coord_text = coord_text.strip().upper()
            
            # Проверяем формат A5, B1, ..., J10
            if len(coord_text) < 2:
                raise ValueError()
            
            col_char = coord_text[0]
            row_str = coord_text[1:]
            
            row = ord(col_char) - ord('A')
            if row < 0 or row >= 10:
                raise ValueError()
            
            col = int(row_str) - 1
            if col < 0 or col >= 10:
                raise ValueError()
        except (ValueError, IndexError):
            bot.reply_to(message, "Неверный формат. Используй /shot A5")
            return
        
        # Определяем целевую доску
        if user_id == game.player_a_id:
            target_id = game.player_b_id
            target_board = game.boards[target_id]
        else:
            target_id = game.player_a_id
            target_board = game.boards[target_id]
        
        # Делаем выстрел
        result = target_board.receive_shot((row, col))
        
        # Формируем ответ
        response = f"{coord_text}: "
        if result == 'miss':
            response += "Мимо! ❌"
        elif result == 'hit':
            response += "Попадание! 🎯"
        elif result == 'sunk':
            response += "Потоплен! 💥"
        
        bot.reply_to(message, response)
        
        # Проверяем, выиграл ли кто-то
        if target_board.all_ships_sunk():
            winner_name = "A" if user_id == game.player_a_id else "B"
            bot.send_message(chat_id, f"Игрок {winner_name} выиграл! 🏆")
            # Удаляем игру
            sea_games.pop(chat_id, None)
            sea_players.pop(chat_id, None)
            return

        # Обновляем доски для обоих игроков
        send_boards(bot, game)

        # Если был промах — передаём ход, если попадание/потоплен, ход остаётся
        if result == 'miss':
            game.switch_turn()
            next_player = "A" if game.turn == game.player_a_id else "B"
            bot.send_message(chat_id, f"Ход игрока {next_player}!")
        else:
            # попал или потопил — просто сообщаем, что ходит тот же игрок
            current_player = "A" if game.turn == game.player_a_id else "B"
            bot.send_message(chat_id, f"Игрок {current_player} ходит ещё раз!")

        
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

        # Определяем целевую доску (как в /shot — подсказка по противнику)
        if user_id == game.player_a_id:
            target_id = game.player_b_id
        else:
            target_id = game.player_a_id

        target_board = game.boards[target_id]

        # Собираем все клетки, куда ещё не стреляли: " " или "O"
        candidates = []
        for r in range(target_board.SIZE):
            for c in range(target_board.SIZE):
                ch = target_board.grid[r][c]
                if ch in (" ", "O"):
                    candidates.append((r, c))

        if not candidates:
            bot.reply_to(message, "Подсказок больше нет: всё поле уже прострелянo.")
            return

        # Выбираем случайную клетку и «стреляем» туда
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

        # Обновляем поля для обоих игроков
        send_boards(bot, game)

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



def send_boards(bot, game):
    """Отправляет доски обоим игрокам в личку"""
    board_a = game.boards[game.player_a_id]
    board_b = game.boards[game.player_b_id]

    # Игроку A: его поле + поле противника B
    bot.send_message(
        game.player_a_id,
        f"**Твоё поле (A):**\n"
        f"```\n{board_a.renderForOwner()}\n```\n\n"
        f"**Поле противника (B):**\n"
        f"```\n{board_b.renderForOpponent()}\n```"
    )

    # Игроку B: его поле + поле противника A
    bot.send_message(
        game.player_b_id,
        f"**Твоё поле (B):**\n"
        f"```\n{board_b.renderForOwner()}\n```\n\n"
        f"**Поле противника (A):**\n"
        f"```\n{board_a.renderForOpponent()}\n```"
    )


