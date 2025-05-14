import sqlite3
import os
from threading import Lock

DB_PATH = os.path.join(os.path.dirname(__file__), "vars.db")
_LOCK = Lock()


def INIT():
    with _LOCK, sqlite3.connect(DB_PATH) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS variables (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                name TEXT PRIMARY KEY
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS var_group_links (
                var_key TEXT,
                group_name TEXT,
                PRIMARY KEY (var_key, group_name),
                FOREIGN KEY (var_key) REFERENCES variables(key),
                FOREIGN KEY (group_name) REFERENCES groups(name)
            )
        """)
        connection.commit()


def REGISTER(key, groups=None):
    with _LOCK, sqlite3.connect(DB_PATH) as connection:
        connection.execute("INSERT OR IGNORE INTO variables (key, value) VALUES (?, '')", (key,))
        if groups:
            for group in groups:
                connection.execute("INSERT OR IGNORE INTO groups (name) VALUES (?)", (group,))
                connection.execute("INSERT OR IGNORE INTO var_group_links (var_key, group_name) VALUES (?, ?)", (key, group))
        connection.commit()


def SET(key, value):
    with _LOCK, sqlite3.connect(DB_PATH) as connection:
        connection.execute("INSERT INTO variables (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))
        connection.commit()


def GET(key, default=None):
    with _LOCK, sqlite3.connect(DB_PATH) as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT value FROM variables WHERE key=?", (key,))
        row = cursor.fetchone()
        return row[0] if row else default


def GET_GROUP(group_name):
    with _LOCK, sqlite3.connect(DB_PATH) as connection:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT v.key, v.value FROM variables v
            JOIN var_group_links l ON v.key = l.var_key
            WHERE l.group_name=?
        """, (group_name,))
        return dict(cursor.fetchall())


def ADD_TO_GROUP(variables, group):
    if isinstance(variables, str):
        variables = [variables]
    with _LOCK, sqlite3.connect(DB_PATH) as connection:
        connection.execute("INSERT OR IGNORE INTO groups (name) VALUES (?)", (group,))
        for var in variables:
            connection.execute("INSERT OR IGNORE INTO var_group_links (var_key, group_name) VALUES (?, ?)", (var, group))
        connection.commit()


def REMOVE_FROM_GROUP(variables, group):
    if isinstance(variables, str):
        variables = [variables]
    with _LOCK, sqlite3.connect(DB_PATH) as connection:
        for var in variables:
            connection.execute("DELETE FROM var_group_links WHERE var_key=? AND group_name=?", (var, group))
        connection.commit()


def LIST_GROUPS():
    with _LOCK, sqlite3.connect(DB_PATH) as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT name FROM groups")
        return [row[0] for row in cursor.fetchall()]


def LIST_VARS():
    with _LOCK, sqlite3.connect(DB_PATH) as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT key FROM variables")
        return [row[0] for row in cursor.fetchall()]
