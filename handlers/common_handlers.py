# handlers/common_handlers.py

from handlers.tictactoe_handlers import stats as tictactoe_stats

def register_handlers(bot):
    """Регистрирует общие хэндлеры"""
    
    @bot.message_handler(commands=['start', 'help'])
    def start_message(message):
        print(f">>> /start from {message.from_user.id}")
        bot.reply_to(message, "Привет! 🎮\n"
                              "Доступные игры:\n\n"
                              "🎯 **Крестики-нолики:**\n"
                              "/newgame - создать игру\n"
                              "/join - присоединиться\n\n"
                              "🚢 **Морской бой:**\n"
                              "/newsea - создать игру\n"
                              "/joinsea - присоединиться\n"
                              "/shot A5 - выстрел\n\n"
                              "📊 /stats - твоя статистика")

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
