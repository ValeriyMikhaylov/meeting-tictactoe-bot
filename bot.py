# bot.py

import telebot
import os
import logging
import sys
import time
import requests

from handlers import tictactoe_handlers, battleship_handlers, common_handlers

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)
print(">>> bot script import OK")

TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    print("ERROR: TOKEN not found in environment variables!")
    exit(1)

bot = telebot.TeleBot(TOKEN, parse_mode=None)

# Регистрируем все хэндлеры
tictactoe_handlers.register_handlers(bot)
battleship_handlers.register_handlers(bot)
common_handlers.register_handlers(bot)

# Импорт и регистрация сапера (если файл существует)
try:
    from handlers.minesweeper_handlers import register_handlers as register_minesweeper_handlers
    register_minesweeper_handlers(bot)
    print(">>> Minesweeper handlers registered successfully")
except ImportError as e:
    print(f">>> Minesweeper not available: {e}")
    print(">>> To add minesweeper, create handlers/minesweeper_handlers.py")

def main():
    logger.info("Bot starting...")
    print(">>> Bot started")
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