import sqlite3
import os
import json
from threading import Lock

DB_PATH = os.path.join(os.path.dirname(__file__), "vars.db")
_LOCK = Lock()

def INIT():
    with _LOCK, sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS object_types (
                type TEXT PRIMARY KEY,
                properties TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS objects (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                data TEXT,
                FOREIGN KEY (type) REFERENCES object_types(type)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS flags (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.commit()

def _serialize(value):
    return json.dumps(value)

def _deserialize(value):
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value

def REGISTER_OBJECT_TYPE(obj_type, properties):
    with _LOCK, sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT OR IGNORE INTO object_types (type, properties) VALUES (?, ?)",
                     (obj_type, _serialize(properties)))
        conn.commit()

def ADD_OBJECT(obj_type, obj_id, force=False, **props):
    with _LOCK, sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()

        if force:
            cur.execute("DELETE FROM objects WHERE id=?", (obj_id,))
        else:
            cur.execute("SELECT 1 FROM objects WHERE id=?", (obj_id,))
            if cur.fetchone():
                return  # Obiectul există deja, ieșim

        cur.execute("SELECT properties FROM object_types WHERE type=?", (obj_type,))
        row = cur.fetchone()
        if not row:
            raise ValueError("Object type not registered.")

        allowed_props = _deserialize(row[0])
        data = {}
        for prop in allowed_props:
            data[prop] = props.get(prop, None)
        if 'id' in allowed_props:
            data['id'] = obj_id

        cur.execute("INSERT INTO objects (id, type, data) VALUES (?, ?, ?)",
                    (obj_id, obj_type, _serialize(data)))
        conn.commit()



def MODIFY_OBJECT(obj_id, **props):
    with _LOCK, sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT type, data FROM objects WHERE id=?", (obj_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError("Object not found.")
        obj_type, existing_data = row
        cur.execute("SELECT properties FROM object_types WHERE type=?", (obj_type,))
        allowed_props = _deserialize(cur.fetchone()[0])
        existing = _deserialize(existing_data)
        for key, value in props.items():
            if key in allowed_props:
                existing[key] = value
        cur.execute("UPDATE objects SET data=? WHERE id=?", (_serialize(existing), obj_id))
        conn.commit()

def _GET_OBJECT_RAW(obj_id):
    with _LOCK, sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT data FROM objects WHERE id=?", (obj_id,))
        row = cur.fetchone()
        return _deserialize(row[0]) if row else None

def GET_OBJECT(obj_type, obj_id):
    with _LOCK, sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT data FROM objects WHERE id=? AND type=?", (obj_id, obj_type))
        row = cur.fetchone()
        return _deserialize(row[0]) if row else None


def LIST_OBJECTS(obj_type):
    with _LOCK, sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, data FROM objects WHERE type=?", (obj_type,))
        return {obj_id: _deserialize(data) for obj_id, data in cur.fetchall()}

def SET_FLAG(key, value):
    with _LOCK, sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT INTO flags (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                     (key, _serialize(value)))
        conn.commit()

def GET_FLAG(key, default=None):
    with _LOCK, sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM flags WHERE key=?", (key,))
        row = cur.fetchone()
        return _deserialize(row[0]) if row else default

def SET_VAR(key, value):
    SET_FLAG(key, value)  # same logic, different emotional packaging

def GET_VAR(key, default=None):
    return GET_FLAG(key, default)

def DELETE_FLAG(key):
    with _LOCK, sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM flags WHERE key=?", (key,))
        conn.commit()

def LIST_FLAGS():
    with _LOCK, sqlite3.connect(DB_PATH) as conn:
        return {row[0]: _deserialize(row[1]) for row in conn.execute("SELECT key, value FROM flags")}

def DEBUG_DUMP_ALL():
    with _LOCK, sqlite3.connect(DB_PATH) as conn:
        print("\n=== OBJECT TYPES ===")
        for row in conn.execute("SELECT * FROM object_types"):
            print(row)
        print("\n=== OBJECTS ===")
        for row in conn.execute("SELECT * FROM objects"):
            print(row)
        print("\n=== FLAGS ===")
        for row in conn.execute("SELECT * FROM flags"):
            print(row)

# Register templates (doar dacă vrei să le pui din start)
def REGISTER_DEFAULT_TEMPLATES():
    REGISTER_OBJECT_TYPE("box", ["id", "color", "letters", "zone_id"])
    REGISTER_OBJECT_TYPE("task", ["id", "from_zone", "to_zone", "box_id", "path_id", "status", "progress"])
    REGISTER_OBJECT_TYPE("path", ["id", "path_human", "path_stm32", "active_path", "tags_possible"])
    REGISTER_OBJECT_TYPE("zone", ["id", "name", "boxes", "capacity_left"])

