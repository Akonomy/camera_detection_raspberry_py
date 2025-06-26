#!/usr/bin/env python3
"""
Module: get_free_from_camera
Descriere: Acest modul importă funcțiile din CAMERA.camera_session și din UTILS.GET_FREE.
         Funcția principală, get_free_spot_from_camera(), capturează o imagine și sesiunea de la cameră,
         apoi apelează funcția analyze_zone_and_find_spot() din UTILS.GET_FREE cu max_boxes=3 și debug=True.
         Rezultatul (pozitia liberă sau "FULL") este afișat în consolă.
         Modulul a fost modificat pentru a inițializa camera și a efectua 5 iterații de analiză.
"""

import time

def get_free_spot_from_camera():
    # Importăm funcția de captură și procesare din modulul camerei
    from CAMERA.camera_session import capture_and_process_session
    # Importăm funcția de analiză din UTILS.GET_FREE
    from UTILS.GET_FREE import analyze_zone_and_find_spot

    # Capturează imaginea și sesiunea
    image_copy, session_data = capture_and_process_session()
    
    # Apelează funcția de analiză pentru a căuta un loc liber, cu max_boxes=3 și debug=True
    result = analyze_zone_and_find_spot(image_copy, session_data, max_boxes=3, ignore_box_id="GreenA", debug=True)
    
    print("Rezultat:", result)
    return result

if __name__ == "__main__":
    from CAMERA.camera_session import init_camera, stop_camera
    
    # Inițializăm camera o singură dată
    init_camera()
    
    try:
        # Executăm un loop de 5 iterații
        for i in range(5):
            print(f"Iterația {i+1}:")
            get_free_spot_from_camera()
            # Pauză de 3 secunde între iterații
            time.sleep(3)
    except KeyboardInterrupt:
        print("Execuția a fost oprită de utilizator.")
    finally:
        stop_camera()
