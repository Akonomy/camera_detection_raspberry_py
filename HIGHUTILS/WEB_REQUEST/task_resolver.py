import os
import sys



project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..','..'))
if project_root not in sys.path:
    sys.path.append(project_root)


from SOURCES.WEB.handler_path_tasks import retrieve_task
from SOURCES.WEB.handler_container import request_box

from SOURCES.TRASEU.normalizare_zone import normalize_move_task
from SOURCES.TRASEU.get_route import analyze_route
from DATABASE import db

# Variabilă globală pentru taskul curent
current_task_data = {}











def save_box_from_container_info(container_data):
    """
    Primește un container dictionary și salvează informațiile relevante ca obiect de tip 'box'.
    """
    container = container_data.get("container")
    if not container:
        print("❌ Structura dată nu conține cheia 'container'.")
        return

    box_id = container.get("code")
    color = container.get("color")
    letters = container.get("symbol")
    zone_id = container.get("zone")

    if not all([box_id, color, letters, zone_id]):
        print("❌ Unele câmpuri lipsesc. Verifică datele containerului.")
        print(f"➡️ code: {box_id}, color: {color}, symbol: {letters}, zone: {zone_id}")
        return

    try:
        db.ADD_OBJECT("box", box_id,
                      id=box_id,
                      color=color,
                      letters=letters,
                      zone_id=zone_id,
                      force=True)
        print(f"✅ Obiectul box '{box_id}' a fost salvat cu succes.")
    except Exception as e:
        print(f"💥 Eroare la salvarea obiectului box: {e}")




def process_and_resolve_move_task():
    # Obținem un task
    task = retrieve_task()
    if not task or task.get("type") != "move_box":
        print("Taskul nu este de tip move_box sau nu există.")
        return None

    # Verificăm dacă e disponibil un tag valid
    if not db.GET_FLAG("isTagAvailable"):
        print("⚠️ Niciun tag disponibil. Oprire.")
        return None

    tag = db.GET_VAR("tag")
    if not tag:
        print("⚠️ Tagul e None. Oprire.")
        return None

    # Normalizare și extragere task
    normalized = normalize_move_task(task)
    if not normalized:
        print("Eroare la normalizarea taskului.")
        return None

    task_id = normalized["task_id"]
    box_code = normalized["box_code"]
    zone_start = normalized["zone_start"]
    zone_target = normalized["zone_target"]

    # Calculează rutele
    route_data = analyze_route(zone_start, zone_target)
    route_tag = analyze_route(tag, zone_start)

    # Creează obiecte în DB
        # Creează obiecte în DB
    db.ADD_OBJECT("box", box_code,
                  id=box_code,
                  force=True)

    db.ADD_OBJECT("task", f"task_{task_id}", 
                  id=f"task_{task_id}", 
                  from_zone=zone_start,
                  to_zone=zone_target,
                  box_id=box_code,
                  path_id=f"path_{task_id}",
                  status="in_progress",
                  progress=0,
                  force=True)

    db.ADD_OBJECT("path", f"path_{task_id}",
                  id=f"path_{task_id}",
                  path_human=[route_tag["full_path"], route_data["full_path"]],
                  path_stm32=[route_tag["directions_numeric"], route_data["directions_numeric"]],
                  active_path=1,
                  tags_possible=route_data.get("possible_tags", {}),
                  force=True)

        # Setează flaguri de disponibilitate cu ultimele ID-uri
    db.SET_FLAG("isTaskAvailable", f"task_{task_id}")
    db.SET_FLAG("isPathAvailable", f"path_{task_id}")



    #ACUM ADAUGA SI CUTIA


    container_data=request_box(box_code)
    
    
    
    save_box_from_container_info(container_data)


'''
    return {
        "task_id": task_id,
        "box_code": box_code,
        "zone_start": zone_start,
        "zone_target": zone_target,
        "route_zone": route_data,
        "route_tag": route_path
    }
'''



if __name__ == "__main__":
    # Rulează taskul, nu returnează nimic
    process_and_resolve_move_task()

    from pprint import pprint

    # Extrage ultimele ID-uri din flaguri
    latest_task_id = db.GET_FLAG("isTaskAvailable")
    latest_path_id = db.GET_FLAG("isPathAvailable")
    latest_box_id = db.GET_OBJECT("task", latest_task_id).get("box_id") if latest_task_id else None

    print("\n📦 Obiect BOX salvat:")
    pprint(db.GET_OBJECT("box", latest_box_id))

    print("\n🧠 Obiect TASK salvat:")
    pprint(db.GET_OBJECT("task", latest_task_id))

    print("\n🗺️ Obiect PATH salvat:")
    pprint(db.GET_OBJECT("path", latest_path_id))

    print("\n🚩 FLAGURI ACTUALE:")
    print("isTaskAvailable:", latest_task_id)
    print("isPathAvailable:", latest_path_id)
