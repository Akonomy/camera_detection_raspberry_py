

from CAMERA.camera_session import init_camera, stop_camera, capture_raw_image, capture_and_process_session
from UTILS.MAP import process_boxes

def update_map_callback(processed_image, session_data):
    # Convertim datele din sesiune (din pixeli) în informații procesate (cu coordonate reale)
    new_boxes = process_boxes(session_data)
    # Actualizăm interfața cu noile cutii
    map_app.update_map(new_boxes)




#!/usr/bin/env python3
import threading
from CAMERA.camera_session import camera_loop
from UTILS.MAP import BoxMapApp

DEBUG = True  # setează la True pentru a afișa interfața, sau False pentru a rula doar bucla de captură

initial_data = {}  # Inițial, nu avem date procesate

if DEBUG:
    init_camera();
    # Inițializează interfața Tkinter cu datele inițiale
    map_app = BoxMapApp(initial_data)
    # Pornește camera_loop într-un thread separat și trece callback-ul
    camera_thread = threading.Thread(target=camera_loop, args=(update_map_callback,), daemon=True)
    camera_thread.start()
    # Rulează interfața Tkinter în firul principal
    map_app.root.mainloop()
else:
    # Fără interfață, doar rulează bucla de captură
    camera_loop()



