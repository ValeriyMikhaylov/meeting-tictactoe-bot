print("=" * 60)
print("ТЕСТ РАБОТОСПОСОБНОСТИ PYTHON")
print("=" * 60)

# 1. Проверка Python
print("✅ Python работает!")

# 2. Проверка импортов
import os
import sys

print(f"✅ Модули импортируются")
print(f"   Текущая папка: {os.getcwd()}")
print(f"   Python версия: {sys.version}")

# 3. Попытка импорта нашего кода
print("\n" + "=" * 60)
print("ПОПЫТКА ИМПОРТА НАШИХ МОДУЛЕЙ")
print("=" * 60)

# Добавляем путь к проекту
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
print(f"✅ Добавили в путь: {project_root}")

# Пробуем импортировать db
try:
    import db
    print("✅ db.py импортирован успешно!")
except ImportError as e:
    print(f"❌ Ошибка импорта db.py: {e}")

# Пробуем импортировать bot
try:
    import bot
    print("✅ bot.py импортирован успешно!")
except ImportError as e:
    print(f"❌ Ошибка импорта bot.py: {e}")

print("\n" + "=" * 60)
print("ТЕСТ ЗАВЕРШЕН")
print("=" * 60)
input("Нажмите Enter чтобы выйти...")