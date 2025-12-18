# handlers/minesweeper_handlers.py

from minesweeper import MinesweeperGame
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import time

minesweeper_games = {}


def build_minesweeper_keyboard(game: MinesweeperGame) -> InlineKeyboardMarkup:
    """Создает клавиатуру для поля сапера"""
    kb = InlineKeyboardMarkup()
    display_board = game.get_display_board()
    
    for r in range(game.size):
        row_btns = []
        for c in range(game.size):
            cell_text = display_board[r][c]
            
            # Определяем callback_data
            if game.game_over:
                callback_data = "mine_ignore"
            elif cell_text in [MinesweeperGame.ZERO] + MinesweeperGame.NUMBERS:
                callback_data = "mine_ignore"  # Уже открытые клетки
            else:
                callback_data = f"mine_{r}_{c}"
            
            row_btns.append(
                InlineKeyboardButton(
                    text=cell_text,
                    callback_data=callback_data,
                )
            )
        kb.row(*row_btns)
    
    # Добавляем кнопки управления под полем
    if not game.game_over:
        control_row = []
        # Кнопка для установки флага (альтернативный клик)
        control_row.append(InlineKeyboardButton(
            text="🚩 Флаг",
            callback_data="mine_flag_mode"
        ))
        # Кнопка перезапуска
        control_row.append(InlineKeyboardButton(
            text="🔄 Новая игра",
            callback_data="mine_new_game"
        ))
        kb.row(*control_row)
    else:
        # После окончания игры только кнопка новой игры
        kb.row(InlineKeyboardButton(
            text="🔄 Новая игра",
            callback_data="mine_new_game"
        ))
    
    return kb


def render_minesweeper_info(game: MinesweeperGame, flag_mode: bool = False) -> str:
    """Рендерит информацию о текущей игре в сапер"""
    difficulty_names = {
        'easy': 'Легкая (4x4)',
        'medium': 'Средняя (6x6)',
        'hard': 'Сложная (8x8)'
    }
    
    title = f"💣 Сапер - {difficulty_names[game.difficulty]}\n"
    
    if game.game_over:
        if game.win:
            status = "🎉 ПОБЕДА! Все мины обезврежены! 🎉\n"
        else:
            status = "💥 ПРОИГРЫШ! Вы наступили на мину! 💥\n"
    else:
        status = f"⛏ Игра идет... Осталось мин: {game.get_remaining_mines()}\n"
    
    if flag_mode and not game.game_over:
        mode = "Режим: 🚩 Установка флага\n"
    elif not game.game_over:
        mode = "Режим: ⛏ Открытие клеток\n"
    else:
        mode = ""
    
    legend = "🟦 закрыто | ⬜ пусто | 1️⃣-8️⃣ рядом мин\n🚩 флаг | 💣 мина\n\n"
    
    instructions = "Кликните на клетку чтобы открыть\n"
    if not game.game_over:
        instructions += "Нажмите '🚩 Флаг' для режима установки флага\n"
    
    return title + status + mode + legend + instructions


def register_handlers(bot):
    """Регистрирует все хэндлеры для сапера"""
    
    @bot.message_handler(commands=["minesweeper", "mine", "сапер"])
    def new_minesweeper_game(message):
        """Начинает новую игру в сапера с выбором сложности"""
        user_id = message.from_user.id
        
        # Если у пользователя уже есть активная игра, спрашиваем подтверждение
        if user_id in minesweeper_games:
            bot.reply_to(
                message,
                "У тебя уже есть активная игра. Начать новую?\n"
                "/mineeasy - Легкая (4x4)\n"
                "/minemedium - Средняя (6x6)\n"
                "/minehard - Сложная (8x8)"
            )
            return
        
        # Создаем клавиатуру для выбора сложности
        kb = InlineKeyboardMarkup()
        kb.row(
            InlineKeyboardButton("Легкая (4x4)", callback_data="mine_difficulty_easy"),
            InlineKeyboardButton("Средняя (6x6)", callback_data="mine_difficulty_medium"),
            InlineKeyboardButton("Сложная (8x8)", callback_data="mine_difficulty_hard")
        )
        
        bot.reply_to(
            message,
            "💣 Выбери уровень сложности сапера:\n"
            "• Легкая: поле 4x4, немного мин\n"
            "• Средняя: поле 6x6, норма мин\n"
            "• Сложная: поле 8x8, много мин\n\n"
            "Начни с легкой, если играешь впервые!",
            reply_markup=kb
        )
    
    @bot.message_handler(commands=["mineeasy"])
    def start_easy_mine(message):
        """Начинает легкую игру"""
        _start_mine_game(bot, message.from_user.id, message.chat.id, 'easy')
    
    @bot.message_handler(commands=["minemedium"])
    def start_medium_mine(message):
        """Начинает среднюю игру"""
        _start_mine_game(bot, message.from_user.id, message.chat.id, 'medium')
    
    @bot.message_handler(commands=["minehard"])
    def start_hard_mine(message):
        """Начинает сложную игру"""
        _start_mine_game(bot, message.from_user.id, message.chat.id, 'hard')
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("mine_difficulty_"))
    def handle_difficulty_selection(call):
        """Обрабатывает выбор сложности"""
        user_id = call.from_user.id
        chat_id = call.message.chat.id
        
        difficulty = call.data.split("_")[-1]  # easy, medium или hard
        
        # Удаляем сообщение с выбором сложности
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass
        
        # Начинаем игру
        _start_mine_game(bot, user_id, chat_id, difficulty)
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("mine_"))
    def handle_mine_click(call):
        """Обрабатывает клики по полю сапера"""
        user_id = call.from_user.id
        chat_id = call.message.chat.id
        
        if user_id not in minesweeper_games:
            bot.answer_callback_query(call.id, "Нет активной игры. Начни новую: /minesweeper")
            return
        
        game, flag_mode, message_id = minesweeper_games[user_id]
        
        if call.data == "mine_ignore":
            bot.answer_callback_query(call.id, "Эта клетка уже открыта или игра окончена")
            return
        
        elif call.data == "mine_flag_mode":
            # Переключаем режим флага
            minesweeper_games[user_id] = (game, not flag_mode, message_id)
            text = render_minesweeper_info(game, not flag_mode)
            
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=build_minesweeper_keyboard(game)
            )
            bot.answer_callback_query(call.id, "Режим изменен")
            return
        
        elif call.data == "mine_new_game":
            # Запрашиваем новую сложность
            kb = InlineKeyboardMarkup()
            kb.row(
                InlineKeyboardButton("Легкая (4x4)", callback_data="mine_difficulty_easy"),
                InlineKeyboardButton("Средняя (6x6)", callback_data="mine_difficulty_medium"),
                InlineKeyboardButton("Сложная (8x8)", callback_data="mine_difficulty_hard")
            )
            
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text="💣 Выбери уровень сложности для новой игры:",
                reply_markup=kb
            )
            return
        
        # Обработка клика по клетке
        _, r_str, c_str = call.data.split("_")
        r, c = int(r_str), int(c_str)
        
        # Проверяем границы
        if not (0 <= r < game.size and 0 <= c < game.size):
            bot.answer_callback_query(call.id, "Неверная клетка")
            return
        
        if flag_mode:
            # Установка/снятие флага
            game.toggle_flag(r, c)
            action_text = "Флаг установлен/снят"
        else:
            # Открытие клетки
            success = game.open_cell(r, c)
            if not success:
                action_text = "💥 БАБАХ! Вы наступили на мину!"
            else:
                action_text = "Клетка открыта"
        
        # Обновляем игру в словаре
        minesweeper_games[user_id] = (game, flag_mode, message_id)
        
        # Обновляем сообщение с полем
        text = render_minesweeper_info(game, flag_mode)
        
        try:
            time.sleep(0.1)
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=build_minesweeper_keyboard(game)
            )
            
            # Если игра окончена, добавляем поздравление или соболезнование
            if game.game_over:
                if game.win:
                    bot.send_message(
                        chat_id,
                        f"🎉🎉🎉 УРА! Ты выиграл! 🎉🎉🎉\n"
                        f"Все {len(game.mine_positions)} мин обезврежены!\n"
                        f"Сыграть еще: /minesweeper"
                    )
                else:
                    bot.send_message(
                        chat_id,
                        f"💀 Игра окончена! Ты подорвался на мине!\n"
                        f"На поле было {len(game.mine_positions)} мин\n"
                        f"Попробуй еще: /minesweeper"
                    )
        
        except Exception as e:
            print(f"Ошибка при обновлении сапера: {e}")
        
        bot.answer_callback_query(call.id, action_text)


def _start_mine_game(bot, user_id, chat_id, difficulty):
    """Начинает новую игру в сапера"""
    game = MinesweeperGame(user_id, difficulty)
    
    # Состояние: (игра, режим_флага, id_сообщения)
    # Изначально режим флага выключен
    flag_mode = False
    
    text = render_minesweeper_info(game, flag_mode)
    msg = bot.send_message(
        chat_id,
        text,
        reply_markup=build_minesweeper_keyboard(game)
    )
    
    # Сохраняем игру
    minesweeper_games[user_id] = (game, flag_mode, msg.message_id)