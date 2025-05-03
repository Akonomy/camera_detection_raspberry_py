import os
import sys

# Adaugă root-ul proiectului pentru acces la tot
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from HIGHUTILS.MOTION_PATH.task_resolver import process_and_resolve_move_task
from pprint import pprint

def test_task_processing():
    result = process_and_resolve_move_task()
    if not result:
        print("❌ Eroare în procesarea taskului.")
    else:
        print("✅ Task procesat cu succes. Date extrase:")
        pprint(result)

if __name__ == "__main__":
    test_task_processing()
