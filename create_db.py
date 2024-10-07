import os.path
import sqlite3

if os.path.isfile("tx.db"):
    os.remove("tx.db")

with open("./create_table.sql", "r", encoding="utf-8") as f:
    create_db = "\n".join(f.readlines())

with open("./insert.sql", "r", encoding="utf-8") as f:
    insert_db = "\n".join(f.readlines())

with sqlite3.connect("tx.db") as con:
    cur = con.cursor()
    cur.executescript(create_db)
    cur.executescript(insert_db)
