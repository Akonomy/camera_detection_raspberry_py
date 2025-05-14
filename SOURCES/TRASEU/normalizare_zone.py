#!/usr/bin/env python3
import os
import sys

# Adaugă directorul părintelui în sys.path ca să putem importa din SOURCES
some_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if some_path not in sys.path:
    sys.path.append(some_path)

    
from TRASEU import find_route




def normalize_move_task(task):
    from TRASEU import find_route

    def normalize_name(name):
        return name.replace("_", "").replace("[", "").replace("]", "").upper()

    if not task or task.get('type') != 'move_box':
        return None

    info = task.get('info')
    if not info:
        return None

    source = info.get('source')
    target = info.get('target')
    box_code = info.get('box_code')

    if not source or not target or not box_code:
        return None

    source_name = source.get('name')
    target_name = target.get('name')

    if not source_name or not target_name:
        return None

    find_route.load_data()
    all_zones = find_route.getAll()

    src_norm = normalize_name(source_name)
    tgt_norm = normalize_name(target_name)

    zone_start = next((k for k, v in all_zones.items() if src_norm in normalize_name(v)), None)
    zone_target = next((k for k, v in all_zones.items() if tgt_norm in normalize_name(v)), None)

    if not zone_start or not zone_target:
        print(f"[DEBUG] zone_start={zone_start}, zone_target={zone_target}")
        return None

    return {
        "task_id": task.get("id"),
        "box_code": box_code,
        "zone_start": zone_start,
        "zone_target": zone_target
    }

