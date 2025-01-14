import os
import sqlite3 as sq


db_path = os.path.join(os.path.dirname(__file__), "users.db")
with sq.connect(db_path) as con:
    cur = con.cursor()
    print(cur)
    cur.execute("SELECT login, password FROM users ")
    for result in cur:
        print(result)
