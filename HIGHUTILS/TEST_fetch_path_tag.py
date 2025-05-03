import time
import re
import os
import sys

# Configurare mod DEBUG
DEBUG = True

# Adaugă directorul FINAL în sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importuri module
from SOURCES.WEB.robot_api_client import RobotAPIClient
from SOURCES.TRASEU import find_route, find_tag
from SOURCES.TRASEU.get_route import analyze_route
from SOURCES.TAG_RFID import mfrc_reader

# ======== ÎNCĂRCARE DATE =========
find_route.load_data()
find_tag.load_data()

# ======== OBȚINERE TASK DIN API =========
client = RobotAPIClient()
task = client.fetch_first_task()

if not task or 'task' not in task:
    print("Eroare: Niciun task disponibil.")
    exit(1)

def extract_task_info(task):
    task_data = task.get('task', {})
    task_id = task_data.get('id')
    source_section = task_data.get('source_section', {})
    target_section = task_data.get('target_section', {})

    source_name = (source_section.get('type', '') + re.search(r'_(\d+)', source_section.get('name', '')).group(1)).upper()
    target_name = (target_section.get('type', '') + re.search(r'_(\d+)', target_section.get('name', '')).group(1)).upper()

    return task_id, source_name, target_name

task_id, src, tgt = extract_task_info(task)
zones = find_route.getAll()

src_key = next((k for k, v in zones.items() if src in v), None)
tgt_key = next((k for k, v in zones.items() if tgt in v), None)

if not src_key or not tgt_key:
    print(f"Eroare: Nu se pot rezolva zonele {src} sau {tgt}.")
    exit(1)

if DEBUG:
    print(f"Task #{task_id}: {src_key} -> {tgt_key}")

# ======== ANALIZĂ TRASEU INIȚIAL =========
route_info = analyze_route(src_key, tgt_key)
prev_fast = route_info['fast_path']
ordered_tags = []

for inter, tags in route_info['possible_tags'].items():
    for tag_id in tags:
        tag_obj = next((t for t in find_tag._export_data.get("tags", []) if t.get("custom_id") == tag_id), None)
        if tag_obj:
            ordered_tags.append(tag_obj)

if DEBUG:
    print("Taguri utile ordonate:")
    for tag in ordered_tags:
        print(f" - {tag['custom_id']} @ {tag.get('assigned_to')} (entry: {tag.get('entry_direction')})")
    print("Traseu sugerat:")
    print(" -> ".join(prev_fast))

# ======== ETICHETE POTENȚIALE PE TRASEU =========
if DEBUG:
    tags_by_inter = dict(find_tag.getTags())
    for node in prev_fast:
        if node.startswith("I"):
            tags = tags_by_inter.get(node, [])
            if tags:
                print(f" - {node}: {[t['custom_id'] for t in tags]}")

# ======== LOOP DE SCANARE RFID =========
while True:
    uid, data = mfrc_reader.read_mifare_data()

    if data is None:
        if DEBUG:
            print("(Nimic citit. Aștept...)")
        time.sleep(1)
        continue

    if "Z" in data:
        if DEBUG:
            print(f"Zona detectată: {data}")
        continue

    tag = next((t for t in find_tag._export_data.get("tags", []) if t.get("custom_id") == data), None)
    if not tag:
        print(f"Eroare: Tagul {data} nu a fost găsit în datele încărcate.")
        continue

    cross = find_tag.getCross(tag)
    directions = find_tag.getDirections(tag)

    if DEBUG:
        print(f"Tag {data} la {cross}:")
        for k, v in directions.items():
            print(f"  {k}: {v}")

    # Recalculare traseu dacă e nevoie
    if cross:
        new_fast = find_route.getfastPath(cross, tgt_key)
        if new_fast != prev_fast:
            print("Traseu recalculat.")
            prev_fast = new_fast
            # Re-analizăm traseul
            route_info = analyze_route(cross, tgt_key)
            ordered_tags = []
            for inter, tags in route_info['possible_tags'].items():
                for tag_id in tags:
                    tag_obj = next((t for t in find_tag._export_data.get("tags", []) if t.get("custom_id") == tag_id), None)
                    if tag_obj:
                        ordered_tags.append(tag_obj)
            if DEBUG:
                print("Noul traseu:")
                print(" -> ".join(new_fast))
                print("Taguri utile ordonate:")
                for tag in ordered_tags:
                    print(f" - {tag['custom_id']} @ {tag.get('assigned_to')} (entry: {tag.get('entry_direction')})")
        else:
            if DEBUG:
                print("Traseul rămâne neschimbat.")

    time.sleep(1)
