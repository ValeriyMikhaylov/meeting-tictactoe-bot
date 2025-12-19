# tests/test_imports.py
"""Самый простой тест - проверяем что можем импортировать модули"""

def test_can_import_db():
    """Тест: можем ли импортировать db.py"""
    try:
        import db
        assert True, "db.py импортируется успешно"
    except ImportError as e:
        assert False, f"Не удалось импортировать db.py: {e}"

def test_can_import_bot():
    """Тест: можем ли импортировать bot.py"""
    try:
        import bot
        assert True, "bot.py импортируется успешно"
    except ImportError as e:
        assert False, f"Не удалось импортировать bot.py: {e}"

# Запускаем вручную
if __name__ == "__main__":
    test_can_import_db()
    test_can_import_bot()
    print("✅ Все импорты работают!")