#!/usr/bin/env python3
"""
Script: test_session.py
Descriere: Scriptul importă modulul camera_session, draw_session și tracked_box.
Pentru fiecare cadru capturat de cameră, se procesează datele de sesiune și se obține
o copie a imaginii cu desene (bounding box-uri, litere, grilă, zonă definită) care este afișată.
Inițial nu se trackează nicio cutie; odată ce se identifică un candidat (cel mai apropiat),
acesta este memorat și urmat până când dispare (când se resetează tracked_box_id la None).
"""

import cv2
from CAMERA.camera_session import camera_loop
from CAMERA.draw_session import draw_session_data
from CAMERA.tracked_box import get_tracked_box

# Variabilă globală pentru ID-ul cutiei trackate
tracked_box_id = None

def process_frame(image, session_data):
    """
    Callback pentru camera_loop.
    - Dacă tracked_box_id este None, se selectează cel mai bun candidat din session_data.
    - Dacă tracked_box_id există, se verifică dacă încă este prezent în noile date.
      Dacă nu, se resetează la None.
    Se afișează apoi imaginea cu desene și se tipărește cutia trackată.
    """
    global tracked_box_id
    
    print("#"*20)
    print(f"/n {session_data} /n")
    print("_"*20)

    # Dacă nu avem deja o cutie trackată, selectăm una (cel mai bun candidat)
    if tracked_box_id is None:
        candidate = get_tracked_box(session_data)  # folosește logica internă din modulul tracked_box
        if candidate is not None:
            # Găsim ID-ul candidatului din session_data
            for box_id, box in session_data.items():
                if box == candidate:
                    tracked_box_id = box_id
                    break
    else:
        # Dacă avem un tracked_box_id, verificăm dacă acesta mai există în session_data
        if tracked_box_id not in session_data:
            tracked_box_id = None

    # Desenăm toate elementele pe imagine
    output_image = draw_session_data(image, session_data)
    cv2.imshow("Processed Image", cv2.cvtColor(output_image, cv2.COLOR_RGB2BGR))

    # Afișează rezultatul cutiei trackate (dacă există)
    if tracked_box_id is not None:
        print("Tracked box:", session_data[tracked_box_id])
    else:
        print("Tracked box: None")

def main():
    # Pornim camera_loop cu callback-ul definit
    camera_loop(callback=process_frame)

if __name__ == "__main__":
    main()
