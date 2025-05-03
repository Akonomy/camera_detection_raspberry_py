import os
import sys
import json

# Adaugă directorul curent (unde se află robot_api_client.py) în sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from robot_api_client import RobotAPIClient

def debug_task_handler():
    """Afișează toate taskurile disponibile cu detalii complete (pentru analiză și debugging)."""
    client = RobotAPIClient()
    tasks = client.fetch_tasks()

    if not tasks:
        print("⚠️ Nu s-au găsit taskuri.")
        return

    print(f"\n🔍 {len(tasks)} taskuri primite:\n")
    for idx, task in enumerate(tasks, 1):
        print(f"\n=== TASK #{idx} ===")
        print(json.dumps(task, indent=4))

def retrieve_task():
    """
    Obține primul task și returnează structura procesabilă:
    {
        'id': <task_id>,
        'type': <task_type>,
        'info': <dict sau None>
    }
    """
    client = RobotAPIClient()
    task = client.fetch_first_task()

    if not task or 'task' not in task:
        return None

    task_data = task['task']
    task_id = task_data.get('id')
    task_type = task_data.get('task_type')
    box_code = task_data.get('box_code')
    source = task_data.get('source_section')
    target = task_data.get('target_section')
    action = task_data.get('custom_action')

    info = None

    if task_type == 'move_box':
        info = {
            'source': source,
            'target': target,
            'box_code': box_code
        }
    elif task_type == 'add_box':
        info = {
            'target': target,
            'box_code': box_code
        }
    elif task_type == 'custom_action':
        info = {
            'action': action,
            'box_code': box_code
        }
    elif task_type in ('emergency', 'park'):
        info = {
            'box_code': box_code
        }

    return {
        'id': task_id,
        'type': task_type,
        'info': info
    }

if __name__ == "__main__":
    debug_task_handler()
    result = retrieve_task()
    if result:
        print("\n=== FIRST TASK STRUCTURED ===")
        print(json.dumps(result, indent=4))
    else:
        print("\nNu există taskuri valide de procesat.")
