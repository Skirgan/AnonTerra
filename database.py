import sqlite3

connection = sqlite3.connect("database.db")
cursor = connection.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS names (
        id INT,
        name TEXT
    )""")
cursor.execute("""CREATE TABLE IF NOT EXISTS privates (
        first_id INT,
        second_id INT
    )""")
cursor.execute("""CREATE TABLE IF NOT EXISTS blacklist (
        id INT
    )""")
connection.commit()