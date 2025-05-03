import os
import sys





sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from SOURCES.WEB.handler_path_tasks import retrieve_task
from SOURCES.TRASEU.normalizare_zone import normalize_move_task
from SOURCES.TRASEU.get_route import analyze_route

# Variabilă globală pentru taskul curent
current_task_data = {}

def process_and_resolve_move_task():
    """
    Obține și procesează un task de tip move_box:
    - Extrage primul task
    - Normalizează zonele
    - Generează traseul
    - Returnează toate datele utile
    """
    task = retrieve_task()
    if not task or task.get("type") != "move_box":
        print("Taskul nu este de tip move_box sau nu există.")
        return None



    normalized = normalize_move_task(task)
    if not normalized:
        print("Eroare la normalizarea taskului.")
        return None

    task_id = normalized["task_id"]
    box_code = normalized["box_code"]
    zone_start = normalized["zone_start"]
    zone_target = normalized["zone_target"]

    route_data = analyze_route(zone_start, zone_target)

    # Salvăm în globală dacă vrem acces ulterior
    global current_task_data
    current_task_data = {
        "task_id": task_id,
        "box_code": box_code,
        "zone_start": zone_start,
        "zone_target": zone_target
    }

    return {
        "task_id": task_id,
        "box_code": box_code,
        "zone_start": zone_start,
        "zone_target": zone_target,
        "route_data": route_data
    }

if __name__ == "__main__":
    result = process_and_resolve_move_task()
    if result:
        from pprint import pprint
        pprint(result)
