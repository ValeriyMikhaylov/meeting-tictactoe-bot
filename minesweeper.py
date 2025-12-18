# minesweeper.py

import random
from dataclasses import dataclass
from typing import List, Tuple, Set

Coord = Tuple[int, int]


@dataclass
class MinesweeperGame:
    """Класс для игры в сапер"""
    
    # Уровни сложности: (размер поля, процент мин)
    DIFFICULTY_LEVELS = {
        'easy': (4, 0.25),    # 4x4, 25% мин = ~4 мины
        'medium': (6, 0.30),  # 6x6, 30% мин = ~11 мин
        'hard': (8, 0.35)     # 8x8, 35% мин = ~22 мины
    }
    
    # Символы для отображения
    MINE = "💣"
    FLAG = "🚩"
    UNOPENED = "🟦"
    ZERO = "⬜"
    NUMBERS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"]
    
    def __init__(self, player_id: int, difficulty: str = 'medium'):
        self.player_id = player_id
        self.difficulty = difficulty
        self.size, self.mine_percentage = self.DIFFICULTY_LEVELS[difficulty]
        
        # Инициализация поля
        self.board = [[self.UNOPENED for _ in range(self.size)] for _ in range(self.size)]
        self.mine_positions = set()
        self.opened_cells = set()
        self.flagged_cells = set()
        self.game_over = False
        self.win = False
        
        # Генерация мин
        self._generate_mines()
        
    def _generate_mines(self):
        """Генерирует мины на поле"""
        total_cells = self.size * self.size
        num_mines = int(total_cells * self.mine_percentage)
        
        # Гарантируем хотя бы 1 мину даже на маленьком поле
        if num_mines < 1:
            num_mines = 1
        
        while len(self.mine_positions) < num_mines:
            r = random.randint(0, self.size - 1)
            c = random.randint(0, self.size - 1)
            self.mine_positions.add((r, c))
    
    def _count_adjacent_mines(self, r: int, c: int) -> int:
        """Считает количество мин в соседних клетках"""
        count = 0
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.size and 0 <= nc < self.size:
                    if (nr, nc) in self.mine_positions:
                        count += 1
        return count
    
    def open_cell(self, r: int, c: int) -> bool:
        """Открывает клетку. Возвращает True если игра продолжается, False если проиграл"""
        if self.game_over:
            return False
        
        if (r, c) in self.flagged_cells:
            return True  # Нельзя открыть помеченную флагом клетку
        
        if (r, c) in self.opened_cells:
            return True  # Уже открыта
        
        self.opened_cells.add((r, c))
        
        # Проверка на мину
        if (r, c) in self.mine_positions:
            self.game_over = True
            self.win = False
            return False
        
        # Считаем соседние мины
        mine_count = self._count_adjacent_mines(r, c)
        
        if mine_count == 0:
            self.board[r][c] = self.ZERO
            # Автооткрытие соседних пустых клеток
            self._auto_open_empty(r, c)
        else:
            self.board[r][c] = self.NUMBERS[mine_count - 1]
        
        # Проверка победы
        self._check_win()
        
        return True
    
    def _auto_open_empty(self, r: int, c: int):
        """Автоматически открывает соседние пустые клетки (рекурсивно)"""
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if (0 <= nr < self.size and 0 <= nc < self.size and 
                    (nr, nc) not in self.opened_cells and
                    (nr, nc) not in self.flagged_cells):
                    
                    mine_count = self._count_adjacent_mines(nr, nc)
                    self.opened_cells.add((nr, nc))
                    
                    if mine_count == 0:
                        self.board[nr][nc] = self.ZERO
                        self._auto_open_empty(nr, nc)
                    else:
                        self.board[nr][nc] = self.NUMBERS[mine_count - 1]
    
    def toggle_flag(self, r: int, c: int):
        """Ставит или убирает флаг"""
        if self.game_over:
            return
        
        if (r, c) in self.opened_cells:
            return  # Нельзя ставить флаг на открытую клетку
        
        if (r, c) in self.flagged_cells:
            self.flagged_cells.remove((r, c))
            self.board[r][c] = self.UNOPENED
        else:
            self.flagged_cells.add((r, c))
            self.board[r][c] = self.FLAG
        
        # Проверка победы после установки флага
        self._check_win()
    
    def _check_win(self):
        """Проверяет, выиграл ли игрок"""
        # Игрок выигрывает, если:
        # 1. Все клетки без мин открыты
        # 2. ИЛИ все мины помечены флагами
        
        # Все не-минные клетки открыты
        all_non_mine_opened = all(
            (r, c) in self.opened_cells 
            for r in range(self.size) 
            for c in range(self.size) 
            if (r, c) not in self.mine_positions
        )
        
        # Все мины помечены флагами
        all_mines_flagged = self.mine_positions.issubset(self.flagged_cells)
        
        if all_non_mine_opened or all_mines_flagged:
            self.game_over = True
            self.win = True
    
    def reveal_all_mines(self):
        """Открывает все мины (для конца игры)"""
        for r, c in self.mine_positions:
            if (r, c) not in self.flagged_cells:
                self.board[r][c] = self.MINE
    
    def get_display_board(self) -> List[List[str]]:
        """Возвращает текущее состояние доски для отображения"""
        display_board = [row.copy() for row in self.board]
        
        # Если игра окончена, показываем все мины
        if self.game_over and not self.win:
            for r, c in self.mine_positions:
                if (r, c) not in self.flagged_cells:
                    display_board[r][c] = self.MINE
        
        return display_board
    
    def get_remaining_mines(self) -> int:
        """Возвращает количество непомеченных мин"""
        total_mines = len(self.mine_positions)
        flagged_mines = len([pos for pos in self.flagged_cells if pos in self.mine_positions])
        return total_mines - flagged_mines