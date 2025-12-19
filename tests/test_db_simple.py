# tests/test_db_simple.py
"""
ПРОСТЫЕ ТЕСТЫ ДЛЯ DB.PY - ПРОВЕРКА БАЛАНСА АЛМАЗОВ
"""
import sys
import os
import sqlite3

print("=" * 70)
print("🧪 ЗАПУСК ТЕСТОВ ДЛЯ DB.PY (СИСТЕМА АЛМАЗОВ)")
print("=" * 70)

# 1. Настраиваем пути для импорта
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.insert(0, project_root)

print(f"📁 Проект: {project_root}")

# 2. Пробуем импортировать наш модуль db
try:
    import db
    print("✅ db.py успешно импортирован!")
except ImportError as e:
    print(f"❌ Ошибка импорта db.py: {e}")
    print("   Убедитесь что файл db.py существует в папке проекта")
    exit(1)

# 3. Вспомогательная функция для создания тестовой БД
def create_test_db():
    """Создает временную базу данных в памяти"""
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    
    # Создаем таблицу как в реальном db.py
    cursor.execute("""
    CREATE TABLE users (
        user_id   INTEGER PRIMARY KEY,
        diamonds  INTEGER NOT NULL DEFAULT 0
    )
    """)
    conn.commit()
    
    return conn, cursor

# 4. Тест 1: Новый пользователь
def test_new_user():
    print("\n1️⃣  ТЕСТ: Новый пользователь")
    print("-" * 40)
    
    conn, cursor = create_test_db()
    
    # Сохраняем старые значения чтобы потом восстановить
    old_conn = db.conn
    old_cur = db.cur
    
    # Подменяем на тестовые
    db.conn = conn
    db.cur = cursor
    
    try:
        user_id = 999888777  # ID которого точно нет
        
        # Проверяем что пользователя нет в базе
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        assert cursor.fetchone() is None, "Пользователь не должен существовать"
        
        # Получаем баланс (должен создать пользователя)
        balance = db.get_balance(user_id)
        
        # Проверяем результат
        assert balance == 0, f"Баланс должен быть 0, а не {balance}"
        print(f"   ✅ Баланс нового пользователя: {balance}")
        
        # Проверяем что пользователь добавился в БД
        cursor.execute("SELECT diamonds FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        assert row is not None, "Пользователь должен быть создан в БД"
        assert row[0] == 0, f"В БД должен быть баланс 0, а не {row[0]}"
        print(f"   ✅ Пользователь создан в базе данных")
        
        return True
        
    finally:
        # Восстанавливаем оригинальные соединения
        db.conn = old_conn
        db.cur = old_cur
        conn.close()

# 5. Тест 2: Существующий пользователь
def test_existing_user():
    print("\n2️⃣  ТЕСТ: Существующий пользователь")
    print("-" * 40)
    
    conn, cursor = create_test_db()
    
    old_conn = db.conn
    old_cur = db.cur
    db.conn = conn
    db.cur = cursor
    
    try:
        # Создаем тестового пользователя
        test_user_id = 111222333
        test_balance = 150
        
        cursor.execute(
            "INSERT INTO users (user_id, diamonds) VALUES (?, ?)",
            (test_user_id, test_balance)
        )
        conn.commit()
        
        # Получаем баланс
        balance = db.get_balance(test_user_id)
        
        # Проверяем
        assert balance == test_balance, f"Баланс должен быть {test_balance}, а не {balance}"
        print(f"   ✅ Баланс существующего пользователя: {balance} (ожидалось: {test_balance})")
        
        return True
        
    finally:
        db.conn = old_conn
        db.cur = old_cur
        conn.close()

# 6. Тест 3: Добавление алмазов
def test_add_diamonds():
    print("\n3️⃣  ТЕСТ: Добавление алмазов")
    print("-" * 40)
    
    conn, cursor = create_test_db()
    
    old_conn = db.conn
    old_cur = db.cur
    db.conn = conn
    db.cur = cursor
    
    try:
        user_id = 555666777
        initial_balance = 75
        
        # Создаем пользователя
        cursor.execute(
            "INSERT INTO users (user_id, diamonds) VALUES (?, ?)",
            (user_id, initial_balance)
        )
        conn.commit()
        
        # Добавляем 25 алмазов
        diamonds_to_add = 25
        new_balance = db.change_balance(user_id, diamonds_to_add)
        
        # Проверяем
        expected_balance = initial_balance + diamonds_to_add
        assert new_balance == expected_balance, \
            f"Баланс должен быть {expected_balance}, а не {new_balance}"
        
        print(f"   ✅ Добавление алмазов: {initial_balance} + {diamonds_to_add} = {new_balance}")
        
        # Проверяем в БД
        cursor.execute("SELECT diamonds FROM users WHERE user_id = ?", (user_id,))
        db_balance = cursor.fetchone()[0]
        assert db_balance == expected_balance, \
            f"В БД баланс должен быть {expected_balance}, а не {db_balance}"
        
        print(f"   ✅ В базе данных тоже: {db_balance}")
        
        return True
        
    finally:
        db.conn = old_conn
        db.cur = old_cur
        conn.close()

# 7. Тест 4: Списание алмазов
def test_remove_diamonds():
    print("\n4️⃣  ТЕСТ: Списание алмазов")
    print("-" * 40)
    
    conn, cursor = create_test_db()
    
    old_conn = db.conn
    old_cur = db.cur
    db.conn = conn
    db.cur = cursor
    
    try:
        user_id = 888999000
        initial_balance = 100
        
        # Создаем пользователя
        cursor.execute(
            "INSERT INTO users (user_id, diamonds) VALUES (?, ?)",
            (user_id, initial_balance)
        )
        conn.commit()
        
        # Списываем 40 алмазов
        diamonds_to_remove = -40
        new_balance = db.change_balance(user_id, diamonds_to_remove)
        
        # Проверяем
        expected_balance = initial_balance + diamonds_to_remove  # 100 - 40 = 60
        assert new_balance == expected_balance, \
            f"Баланс должен быть {expected_balance}, а не {new_balance}"
        
        print(f"   ✅ Списание алмазов: {initial_balance} - 40 = {new_balance}")
        
        return True
        
    finally:
        db.conn = old_conn
        db.cur = old_cur
        conn.close()

# 8. Тест 5: Ошибка при недостатке алмазов
def test_insufficient_funds_error():
    print("\n5️⃣  ТЕСТ: Ошибка при недостатке алмазов")
    print("-" * 40)
    
    conn, cursor = create_test_db()
    
    old_conn = db.conn
    old_cur = db.cur
    db.conn = conn
    db.cur = cursor
    
    try:
        user_id = 333444555
        initial_balance = 30
        
        # Создаем пользователя
        cursor.execute(
            "INSERT INTO users (user_id, diamonds) VALUES (?, ?)",
            (user_id, initial_balance)
        )
        conn.commit()
        
        # Пытаемся списать 100 алмазов (больше чем есть)
        try:
            db.change_balance(user_id, -100)
            print("   ❌ ОШИБКА: должна была возникнуть ValueError!")
            return False
            
        except ValueError as e:
            error_msg = str(e)
            
            # Проверяем ключевые элементы сообщения об ошибке
            checks = [
                ("Не хватает алмазов", True),
                ("Нужно 100", True),
                ("у тебя 30", True),
                ("+7 977 4646109", True),  # Номер для пополнения
                ("1 рубль = 1 алмаз", True),
                ("В комментарии укажите ваш ID", True),
            ]
            
            all_passed = True
            for text, should_be_present in checks:
                is_present = text in error_msg
                if should_be_present and not is_present:
                    print(f"   ❌ В ошибке отсутствует: '{text}'")
                    all_passed = False
                elif not should_be_present and is_present:
                    print(f"   ❌ В ошибке лишнее: '{text}'")
                    all_passed = False
            
            if all_passed:
                print("   ✅ Правильная ошибка с информацией о пополнении")
                
                # Проверяем что баланс НЕ изменился
                cursor.execute("SELECT diamonds FROM users WHERE user_id = ?", (user_id,))
                balance_after = cursor.fetchone()[0]
                assert balance_after == initial_balance, \
                    f"Баланс не должен измениться, должен быть {initial_balance}, а не {balance_after}"
                
                print(f"   ✅ Баланс не изменился: {balance_after}")
                return True
            else:
                return False
                
    finally:
        db.conn = old_conn
        db.cur = old_cur
        conn.close()

# 9. Запуск всех тестов
def run_all_tests():
    """Запускает все тесты и показывает результаты"""
    
    tests = [
        ("Новый пользователь", test_new_user),
        ("Существующий пользователь", test_existing_user),
        ("Добавление алмазов", test_add_diamonds),
        ("Списание алмазов", test_remove_diamonds),
        ("Ошибка при недостатке", test_insufficient_funds_error),
    ]
    
    print("\n" + "=" * 70)
    print("🚀 ЗАПУСК ВСЕХ ТЕСТОВ")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\n🔍 Тест: {test_name}")
            
            if test_func():
                print(f"   ✅ ПРОЙДЕН")
                passed += 1
            else:
                print(f"   ❌ НЕ ПРОЙДЕН")
                failed += 1
                
        except AssertionError as e:
            print(f"   ❌ ОШИБКА: {e}")
            failed += 1
        except Exception as e:
            print(f"   ❌ НЕОЖИДАННАЯ ОШИБКА: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    # Итоги
    print("\n" + "=" * 70)
    print("📊 ИТОГИ ТЕСТИРОВАНИЯ DB.PY")
    print("=" * 70)
    print(f"✅ Пройдено: {passed}")
    print(f"❌ Упало:   {failed}")
    print(f"📈 Успешность: {passed}/{len(tests)} ({passed/len(tests)*100:.0f}%)")
    
    if failed == 0:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("Система алмазов работает корректно!")
    else:
        print(f"\n⚠️  ВНИМАНИЕ: {failed} тестов не прошло")
    
    print("=" * 70)
    
    return failed == 0

# 10. Точка входа
if __name__ == "__main__":
    success = run_all_tests()
    
    # Завершаем с кодом ошибки если тесты не прошли
    if not success:
        print("\n❌ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО С ОШИБКАМИ")
        exit(1)
    else:
        print("\n✨ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО УСПЕШНО")