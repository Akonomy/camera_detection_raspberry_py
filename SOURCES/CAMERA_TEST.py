#!/usr/bin/env python3
"""
Script: test_session.py
Descriere: Scriptul importă modulul camera_session și folosește camera_loop() pentru a
procesa continuu cadrele. Pentru fiecare cadru, analizează sesiunea de cutii pentru a determina:
  - Cutia țintă (tracked box)
  - Safe flag, danger list și warning list
Rezultatele sunt afișate în consolă.
"""

import cv2
from UTILS.MAP import analyze_target_zones, process_boxes
from CAMERA.camera_session import camera_loop

def process_frame(image, session_data):
    """
    Callback pentru camera_loop.
    Procesează session_data folosind process_boxes pentru a obține cheile necesare
    (ex. "real_position", "color", "letter", "angle"), apoi apelează analyze_target_zones
    pentru a obține safe_flag, danger_list și warning_list. Rezultatele sunt afișate în consolă.
    """
    if not session_data:
        print("Nu s-au detectat cutii.")
        return
    
    # Procesează datele pentru analiză
    processed_session = process_boxes(session_data)
    
    # Dacă există o cutie țintă specificată, de exemplu "BlueK", o folosim, altfel alegem primul
    target_id = "BlueK" if "BlueK" in processed_session else list(processed_session.keys())[0]
    
    safe_flag, danger_list, warning_list = analyze_target_zones(processed_session, target_box_id=target_id)
    
    print("Tracked (target) box ID:", target_id)
    print("Safe flag:", safe_flag)
    print("Danger list:", danger_list)
    print("Warning list:", warning_list)
    
    # Afișează imaginea procesată (fără desene suplimentare)
    cv2.imshow("Processed Image", cv2.cvtColor(image, cv2.COLOR_RGB2BGR))

def main():
    # Pornim camera_loop cu callback-ul definit
    camera_loop(callback=process_frame)

if __name__ == "__main__":
    main()
