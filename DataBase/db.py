import sqlite3

conn = sqlite3.connect("game.db", check_same_thread=False)
cur = conn.cursor()

# создаём таблицу пользователей, если её ещё нет
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id   INTEGER PRIMARY KEY,
    diamonds  INTEGER NOT NULL DEFAULT 0
)
""")
conn.commit()


def get_balance(user_id: int) -> int:
    cur.execute("SELECT diamonds FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    if row is None:
        cur.execute(
            "INSERT INTO users (user_id, diamonds) VALUES (?, 0)",
            (user_id,),
        )
        conn.commit()
        return 0
    return row[0]


def change_balance(user_id: int, delta: int) -> int:
    balance = get_balance(user_id)
    new_balance = balance + delta
    if new_balance < 0:
        raise ValueError("Not enough diamonds")

    cur.execute(
        "UPDATE users SET diamonds = ? WHERE user_id = ?",
        (new_balance, user_id),
    )
    conn.commit()
    return new_balance
