from DATABASE import db

# De apelat la start

import time
from datetime import datetime



def get_task_info(task_id):
    task = db.GET_OBJECT("task", task_id)
    if not task:
        return f"Task '{task_id}' nu a fost găsit."
    return {
        "ID": task.get("id"),
        "Cutie": task.get("box_id"),
        "Din zona": task.get("from_zone"),
        "În zona": task.get("to_zone"),
        "Status": task.get("status"),
        "Progres": task.get("progress"),
        "Traseu": task.get("path_id")
    }

def get_box_info(box_id):
    box = db.GET_OBJECT("box", box_id)
    if not box:
        return f"Cutia '{box_id}' nu a fost găsită."
    return {
        "ID": box.get("id"),
        "Culoare": box.get("color"),
        "Litere": box.get("letters"),
        "Zona curentă": box.get("zone_id")
    }

def get_path_info(path_id):
    path = db.GET_OBJECT("path", path_id)
    if not path:
        return f"Traseul '{path_id}' nu a fost găsit."
    return {
        "ID": path.get("id"),
        "Descriere (uman)": path.get("path_human"),
        "Instrucțiuni STM32": path.get("path_stm32"),
        "Activ": path.get("active_path"),
        "Taguri posibile": path.get("tags_possible")
    }

# Exemplu de listare
def list_tasks():
    return db.LIST_OBJECTS("task")

def list_boxes():
    return db.LIST_OBJECTS("box")

def list_paths():
    return db.LIST_OBJECTS("path")



print(list_tasks())
print(list_boxes())
print(list_paths())

print("===========")
print(get_task_info("task_35"))
print(get_box_info("PJWBjYP"))
print(get_path_info("path_35"))
