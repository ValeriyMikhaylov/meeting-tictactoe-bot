# tictactoe.py

def empty_board():
    return [[' ' for _ in range(3)] for _ in range(3)]

def board_text(board):
    lines = []
    for row in board:
        lines.append(' | '.join(cell if cell != ' ' else ' ' for cell in row))
    return '---------\n'.join(lines)

def check_winner(board):
    lines = []
    for i in range(3):
        lines.append(board[i])
        lines.append([board[0][i], board[1][i], board[2][i]])
    lines.append([board[0][0], board[1][1], board[2][2]])
    lines.append([board[0][2], board[1][1], board[2][0]])
    
    for line in lines:
        if line[0] != ' ' and line.count(line[0]) == 3:
            return line[0]
    
    if all(cell != ' ' for row in board for cell in row):
        return 'draw'
    
    return None

def next_symbol(sym):
    return 'O' if sym == 'X' else 'X'
