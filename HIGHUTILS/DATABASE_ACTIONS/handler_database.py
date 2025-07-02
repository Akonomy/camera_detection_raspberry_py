import os
import sys



project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..','..'))
if project_root not in sys.path:
    sys.path.append(project_root)


from SOURCES.WEB.handler_path_tasks import retrieve_task
from SOURCES.WEB.handler_container import request_box


from DATABASE import db






def get_task_info(task_id):
    return db.GET_OBJECT("task", task_id)

def get_box_info(box_id):
    return db.GET_OBJECT("box", box_id)

def get_path_info(path_id):
    return db.GET_OBJECT("path", path_id)

# Get nested parameter based on task ID
def get_param_task(task_id, target_param):
    task = get_task_info(task_id)
    if not task:
        return f"Task '{task_id}' not found."

    if target_param in task:
        return task.get(target_param)

    box_id = task.get("box_id")
    path_id = task.get("path_id")

    if target_param in ["color", "letters", "zone_id"]:
        box = get_box_info(box_id)
        return box.get(target_param) if box else f"Box '{box_id}' not found."

    if target_param in ["path_human", "path_stm32", "active_path", "tags_possible"]:
        path = get_path_info(path_id)
        return path.get(target_param) if path else f"Path '{path_id}' not found."

    return f"Parameter '{target_param}' not found."

# Set task or nested data based on task ID
def set_param_task(task_id, param_name, value):
    task = get_task_info(task_id)
    if not task:
        raise ValueError(f"Task '{task_id}' not found.")

    if param_name in task:
        db.MODIFY_OBJECT(task_id, **{param_name: value})
        return

    box_id = task.get("box_id")
    path_id = task.get("path_id")

    if param_name in ["color", "letters", "zone_id"]:
        if not box_id:
            raise ValueError("Box ID missing in task.")
        db.MODIFY_OBJECT(box_id, **{param_name: value})
        return

    if param_name in ["path_human", "path_stm32", "active_path", "tags_possible"]:
        if not path_id:
            raise ValueError("Path ID missing in task.")
        db.MODIFY_OBJECT(path_id, **{param_name: value})
        return

    raise ValueError(f"Parameter '{param_name}' not recognized or unsupported for setting.")
