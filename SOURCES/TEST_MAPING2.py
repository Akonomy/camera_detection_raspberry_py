#!/usr/bin/env python3
import time
from CAMERA.camera_session import capture_raw_image
from ZONE_DETECT.get_zone import detect_zone

if __name__ == "__main__":
    # Pozițiile de test (în cm)
    test_positions = [(-20, 5), (0, 0), (10, 20)]
    try:
            # Capturează o imagine (512x512)
            image_copy = capture_raw_image()
            
            # Apelează detect_zone pentru a verifica pozițiile în zonă
            limits, flags = detect_zone(image_copy, positions=test_positions, debug=True)
            
            print("Limitele zonei:", limits)
            print("Rezultatul verificării pozițiilor:", flags)
            
            # Pauză de 1 secundă între capturi (poți ajusta durata după nevoie)
            time.sleep(1)
    except KeyboardInterrupt:
        print("Execuția a fost oprită de utilizator.")
