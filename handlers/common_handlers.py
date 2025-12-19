# handlers/common_handlers.py

import os
from handlers.tictactoe_handlers import stats as tictactoe_stats
from db import get_balance, change_balance


def register_handlers(bot):
    """Регистрирует общие хэндлеры"""
    
    # Загружаем ADMIN_ID из переменных окружения
    ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))
    
    @bot.message_handler(commands=['start', 'help'])
    def start_message(message):
        print(f">>> /start from {message.from_user.id}")
        bot.reply_to(
            message,
            "Привет! 🎮\n"
            "Доступные игры:\n\n"
            "🎯 **Крестики-нолики:**\n"
            "/newgame - создать игру (станешь игроком X)\n"
            "/join - присоединиться к игре (станешь игроком O)\n\n"
            "🚢 **Морской бой:**\n"
            "/newsea - создать игру (станешь игроком A)\n"
            "/joinsea - присоединиться к игре (станешь игроком B)\n"
            "/seahint - подсказка (открывает случайную клетку за алмазы)\n"
            "/seagiveup - сдаться и завершить игру\n\n"
            "💣 **Сапер:**\n"
            "/minesweeper или /mine - начать сапера\n"
            "/mineeasy - легкий уровень (4x4, 19% мин)\n"
            "/minemedium - средний уровень (6x6, 22% мин)\n"
            "/minehard - сложный уровень (8x8, 26% мин)\n\n"
            "💎 /balance - показать твой баланс алмазов\n"
            "📊 /stats - твоя статистика\n\n"
            "💳 **Пополнение баланса:**\n"
            "Перевод на +7 977 4646109\n"
            "1 рубль = 1 алмаз 💎\n"
            "В комментарии укажите ваш ID"
        )

    @bot.message_handler(commands=['stats'])
    def handle_stats(message):
        user_id = message.from_user.id
        
        user_stats = tictactoe_stats.get(user_id, {'wins': 0, 'losses': 0, 'draws': 0})
        text = f"Твоя статистика:\n" \
               f"Победы: {user_stats['wins']}\n" \
               f"Поражения: {user_stats['losses']}\n" \
               f"Ничьи: {user_stats['draws']}\n"
        
        leaderboard = [(uid, data['wins']) for uid, data in tictactoe_stats.items() if data['wins'] > 0]
        
        if leaderboard:
            leaderboard.sort(key=lambda x: x[1], reverse=True)
            top_3 = leaderboard[:3]
            text += "\n🏆 Топ-3 игроков:\n"
            for place, (uid, wins) in enumerate(top_3, start=1):
                marker = " 👈" if uid == user_id else ""
                text += f"{place}. {uid} - {wins} побед{marker}\n"
        else:
            text += "\nПока нет побед, табличка лидеров будет позже."
        
        bot.reply_to(message, text)

    @bot.message_handler(commands=['balance'])
    def balance_handler(message):
        user_id = message.from_user.id
        diamonds = get_balance(user_id)
        
        reply_text = (
            f"💰 **Твой баланс:** {diamonds} алмазов 💎\n\n"
            f"💳 **Пополнить баланс:**\n"
            f"Перевод на +7 977 4646109\n"
            f"1 рубль = 1 алмаз 💎\n"
            f"В комментарии укажите ваш ID: `{user_id}`\n\n"
            f"⚡ **Быстрое пополнение:**\n"
            f"• 10 алмазов = 10 рублей\n"
            f"• 50 алмазов = 50 рублей\n"
            f"• 100 алмазов = 100 рублей\n\n"
            f"После перевода алмазы поступят в течение 5 минут!"
        )
        
        bot.reply_to(message, reply_text)
        
    @bot.message_handler(commands=['add_diamonds'])
    def add_diamonds_handler(message):
        # Проверяем, установлен ли ADMIN_ID
        if ADMIN_ID == 0:
            bot.reply_to(message, "⚠️ Админский ID не настроен. Установите переменную окружения ADMIN_ID.")
            return
            
        user_id = message.from_user.id
        if user_id != ADMIN_ID:
            bot.reply_to(message, "Эта команда доступна только администратору.")
            return

        try:
            _, target_id_str, amount_str = message.text.split(maxsplit=2)
            target_id = int(target_id_str)
            amount = int(amount_str)
        except (ValueError, IndexError):
            bot.reply_to(
                message,
                "Формат: /add_diamonds <user_id> <amount>\n"
                "Например: /add_diamonds 123456789 100",
            )
            return

        try:
            new_balance = change_balance(target_id, amount)
            bot.reply_to(
                message,
                f"✅ Пользователю {target_id} начислено {amount} алмазов. "
                f"Теперь у него {new_balance} 💎",
            )
        except Exception as e:
            bot.reply_to(message, f"❌ Ошибка: {str(e)}")