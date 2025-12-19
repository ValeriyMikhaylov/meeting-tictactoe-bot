# tests/test_minesweeper.py
"""
ТЕСТ ДЛЯ ПРОВЕРКИ ЧТО СЛОЖНОСТЬ САПЁРА СНИЖЕНА НА 25%
Файл minesweeper.py находится в КОРНЕ проекта!
"""
import sys
import os

# Настраиваем пути
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.insert(0, project_root)

print("=" * 60)
print("🧪 ТЕСТ: СНИЖЕНИЕ СЛОЖНОСТИ САПЁРА НА 25%")
print("=" * 60)

# Показываем где ищем
print(f"📁 Ищем minesweeper.py в: {project_root}")

# Проверяем существует ли файл
minesweeper_path = os.path.join(project_root, "minesweeper.py")
if not os.path.exists(minesweeper_path):
    print(f"❌ Файл не найден: {minesweeper_path}")
    print(f"📂 Файлы в корне: {[f for f in os.listdir(project_root) if f.endswith('.py')]}")
    exit(1)

print(f"✅ Файл найден: {minesweeper_path}")

# Пробуем импортировать
try:
    # Прямой импорт из корня
    import minesweeper
    print("✅ Модуль minesweeper импортирован!")
    
    # Получаем класс
    MinesweeperGame = minesweeper.MinesweeperGame
    
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("\nПробуем альтернативный способ...")
    
    # Альтернативный способ
    import importlib.util
    spec = importlib.util.spec_from_file_location("minesweeper", minesweeper_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    MinesweeperGame = module.MinesweeperGame
    print("✅ Загружено через importlib!")

# Теперь тестируем
print("\n🎯 СОЗДАЕМ ИГРЫ РАЗНЫХ УРОВНЕЙ...")

try:
    easy_game = MinesweeperGame(player_id=1, difficulty='easy')
    medium_game = MinesweeperGame(player_id=2, difficulty='medium')
    hard_game = MinesweeperGame(player_id=3, difficulty='hard')
    
    print("✅ Игры созданы успешно")
    
except Exception as e:
    print(f"❌ Ошибка при создании игр: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Выводим результаты
print("\n📊 РЕЗУЛЬТАТЫ ПОСЛЕ СНИЖЕНИЯ СЛОЖНОСТИ:")
print(f"   Легкая (Easy):")
print(f"     • Поле: {easy_game.size}x{easy_game.size}")
print(f"     • Процент мин: {easy_game.mine_percentage:.3f} ({easy_game.mine_percentage*100:.0f}%)")

print(f"\n   Средняя (Medium):")
print(f"     • Поле: {medium_game.size}x{medium_game.size}")
print(f"     • Процент мин: {medium_game.mine_percentage:.3f} ({medium_game.mine_percentage*100:.0f}%)")

print(f"\n   Сложная (Hard):")
print(f"     • Поле: {hard_game.size}x{hard_game.size}")
print(f"     • Процент мин: {hard_game.mine_percentage:.3f} ({hard_game.mine_percentage*100:.0f}%)")

# Проверяем что сложность снижена
print("\n🔍 ПРОВЕРЯЕМ СНИЖЕНИЕ СЛОЖНОСТИ НА 25%...")

# Старые значения (до снижения) - из старого README
OLD_VALUES = {'easy': 0.25, 'medium': 0.30, 'hard': 0.35}

# Новые значения (после снижения на 25%)
# 25% от 0.25 = 0.0625, 0.25 - 0.0625 = 0.1875 ≈ 0.19
# 25% от 0.30 = 0.0750, 0.30 - 0.0750 = 0.2250 ≈ 0.22  
# 25% от 0.35 = 0.0875, 0.35 - 0.0875 = 0.2625 ≈ 0.26
NEW_VALUES = {'easy': 0.19, 'medium': 0.22, 'hard': 0.26}

games = {'easy': easy_game, 'medium': medium_game, 'hard': hard_game}

all_good = True

print("\n📈 СРАВНЕНИЕ:")
for difficulty, game in games.items():
    old_val = OLD_VALUES[difficulty]
    new_val = NEW_VALUES[difficulty]
    actual_val = game.mine_percentage
    
    # Допустимая погрешность (округление)
    if abs(actual_val - new_val) < 0.01:
        reduction = (old_val - actual_val) / old_val * 100
        print(f"   ✅ {difficulty.upper()}: {actual_val:.3f} (было {old_val} → снижение на {reduction:.0f}%)")
    else:
        print(f"   ❌ {difficulty.upper()}: {actual_val:.3f} (ожидалось {new_val}, было {old_val})")
        all_good = False

print("\n" + "=" * 60)

if all_good:
    print("🎉 ТЕСТ ПРОЙДЕН!")
    print("Сложность сапёра успешно снижена на 25%")
    print("Теперь игрокам будет легче!")
    
    # Показываем разницу в количестве мин
    print("\n📉 РАЗНИЦА В КОЛИЧЕСТВЕ МИН:")
    for difficulty, game in games.items():
        old_val = OLD_VALUES[difficulty]
        new_val = NEW_VALUES[difficulty]
        
        total_cells = game.size * game.size
        old_mines = int(total_cells * old_val)
        new_mines = int(total_cells * new_val)
        difference = old_mines - new_mines
        
        print(f"   {difficulty.upper()}: было ~{old_mines} мин, теперь ~{new_mines} мин (-{difference})")
    
else:
    print("⚠️  ТЕСТ НЕ ПРОЙДЕН!")
    print("Сложность не изменилась или изменилась неправильно")
    print("Проверьте файл minesweeper.py - изменили ли вы DIFFICULTY_LEVELS?")

print("=" * 60)