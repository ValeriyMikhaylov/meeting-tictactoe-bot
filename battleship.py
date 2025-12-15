# battleship.py

from dataclasses import dataclass, field
from typing import List, Tuple, Set, Dict
import random

Coord = Tuple[int, int]  # (row, col)


@dataclass
class Ship:
    cells: List[Coord]                    # координаты палуб
    hits: Set[Coord] = field(default_factory=set)

    def is_sunk(self) -> bool:
        return set(self.cells) == self.hits


class Board:
    SIZE = 10

    def __init__(self) -> None:
        # " " — неизвестно, "O" — корабль, "X" — попадание, "·" — мимо
        self.grid: List[List[str]] = [[" " for _ in range(self.SIZE)] for _ in range(self.SIZE)]
        self.ships: List[Ship] = []

    def in_bounds(self, r: int, c: int) -> bool:
        return 0 <= r < self.SIZE and 0 <= c < self.SIZE

    def can_place_ship(self, bow: Coord, length: int, horizontal: bool) -> bool:
        """Проверка, можно ли поставить корабль (без выхода за поле, пересечений и 
        соприкосновения)."""
        dr, dc = (0, 1) if horizontal else (1, 0)
        cells: List[Coord] = []
        for i in range(length):
            r, c = bow[0] + dr * i, bow[1] + dc * i
            if not self.in_bounds(r, c):
                return False
            cells.append((r, c))

        # проверяем сам корабль и все соседние клетки вокруг каждой палубы
        for (r, c) in cells:
            for nr in range(r - 1, r + 2):
                for nc in range(c - 1, c + 2):
                    if not self.in_bounds(nr, nc):
                        continue
                    # если где-то рядом уже стоит корабль — нельзя
                    if self.grid[nr][nc] == "O":
                        return False

        return True    


    def place_ship(self, bow: Coord, length: int, horizontal: bool) -> bool:
        """Ставит корабль, если можно, и возвращает True/False."""
        if not self.can_place_ship(bow, length, horizontal):
            return False

        dr, dc = (0, 1) if horizontal else (1, 0)
        cells: List[Coord] = []
        for i in range(length):
            r, c = bow[0] + dr * i, bow[1] + dc * i
            self.grid[r][c] = "O"
            cells.append((r, c))

        self.ships.append(Ship(cells=cells))
        return True

    def receive_shot(self, coord: Coord) -> str:
        """
        Обрабатывает выстрел.
        Возвращает: "miss", "hit", "sunk".
        """
        r, c = coord
        if not self.in_bounds(r, c):
            return "miss"

        # уже стреляли сюда
        if self.grid[r][c] in ("X", "·"):
            return "miss"

        if self.grid[r][c] == "O":
            # попали в корабль
            self.grid[r][c] = "X"
            for ship in self.ships:
                if coord in ship.cells:
                    ship.hits.add(coord)
                    if ship.is_sunk():
                        # корабль утонул — обводим его точками
                        for sr, sc in ship.cells:
                            for nr in range(sr - 1, sr + 2):
                                for nc in range(sc - 1, sc + 2):
                                    if not self.in_bounds(nr, nc):
                                        continue
                                    if self.grid[nr][nc] == " ":
                                        self.grid[nr][nc] = "·"
                        return "sunk"
                    else:
                        return "hit"
        else:
            # мимо по пустой клетке
            self.grid[r][c] = "·"
            return "miss"

        return "miss"


    def all_ships_sunk(self) -> bool:
        return all(ship.is_sunk() for ship in self.ships)
    
    def renderForOwner(self) -> str:
        """Показывает доску владельцу - видны корабли и выстрелы"""
        lines = []

        # Шапка: числа 1–10 с отступом под букву
        header = "  " + " ".join(str(c) for c in range(1, self.SIZE + 1))
        lines.append(header)

        for r in range(self.SIZE):
            row_cells = []
            for c in range(self.SIZE):
                ch = self.grid[r][c]
                if ch == "O":
                    ch = "🛢"  # корабль
                elif ch == "X":
                    ch = "❌"  # попадание
                elif ch == "·" or ch == ".":  # промах (учитываем оба варианта)
                    ch = "💧"
                else:
                    ch = "⬜"  # пусто
                row_cells.append(ch)

            # Буква строки + пробел + клетки
            lines.append(f"{chr(ord('A') + r)} " + " ".join(row_cells))

        return "\n".join(lines)
   

    def renderForOpponent(self) -> str:
        """Показывает доску сопернику - скрывает корабли"""
        lines = []

        header = "  " + " ".join(str(c) for c in range(1, self.SIZE + 1))
        lines.append(header)

        for r in range(self.SIZE):
            row_cells = []
            for c in range(self.SIZE):
                ch = self.grid[r][c]
                if ch == "X":
                    ch = "❌"
                elif ch == "·" or ch == ".":
                    ch = "💧"
                else:
                    ch = "⬜"
                row_cells.append(ch)

            lines.append(f"{chr(ord('A') + r)} " + " ".join(row_cells))

        return "\n".join(lines)



    

class Game:
    """Состояние матча между двумя игроками."""

    FLEET_SCHEME = [4, 3, 3, 2, 2, 2, 1, 1, 1, 1]  # длины кораблей

    def __init__(self, player_a_id: int, player_b_id: int) -> None:
        self.player_a_id = player_a_id
        self.player_b_id = player_b_id
        self.boards: Dict[int, Board] = {
            player_a_id: Board(),
            player_b_id: Board(),
        }
        self.turn: int = player_a_id
        self.phase: str = "placing"  # "placing" или "battle"
        # можно хранить, сколько кораблей уже расставил каждый игрок
        self.placed_counts: Dict[int, int] = {player_a_id: 0, player_b_id: 0}

    def auto_place_fleet_for(self, player_id: int) -> None:
        """Случайно расставляет весь флот игрока на его доске."""
        board = self.boards[player_id]
        for length in self.FLEET_SCHEME:
            placed = False
            while not placed:
                horizontal = bool(random.getrandbits(1))
                r = random.randint(0, board.SIZE - 1)
                c = random.randint(0, board.SIZE - 1)
                placed = board.place_ship((r, c), length, horizontal)
        self.placed_counts[player_id] = len(self.FLEET_SCHEME)

    def switch_turn(self) -> None:
        self.turn = self.player_a_id if self.turn == self.player_b_id else self.player_b_id

    def is_over(self) -> bool:
        board_a = self.boards[self.player_a_id]
        board_b = self.boards[self.player_b_id]
        return board_a.all_ships_sunk() or board_b.all_ships_sunk()      
# if __name__ == "__main__":
    # простой тест авторасстановки и рендера поля
    # print("START BATTLESHIP TEST")
    # game = Game(1, 2)
    # game.auto_place_fleet_for(1)
    # print(game.boards[1].render_for_owner())
    # pass


   


