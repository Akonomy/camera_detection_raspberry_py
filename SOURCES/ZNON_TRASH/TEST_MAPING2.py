#!/usr/bin/env python3
import time
import cv2
from CAMERA.camera_session import capture_raw_image, init_camera, stop_camera
from ZONE_DETECT.get_zone import detect_zone

if __name__ == "__main__":
    # Pozițiile de test (în cm)
    test_positions = [(-20, 5), (0, 0), (10, 20)]
    
    # Inițializăm camera o singură dată
    init_camera()
    
    # Creăm o fereastră de debug
    window_name = "Debug"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    
    try:
        # Executăm un loop de 5 apeluri la detect_zone
        for i in range(5):
            print(f"Iterația {i+1}:")
            # Capturează o imagine (512x512) folosind instanța globală
            image_copy = capture_raw_image()
            
            # Apelează detect_zone pentru a verifica pozițiile în zonă
            limits, flags, hull = detect_zone(image_copy, positions=test_positions, debug=True)
            
            print("Limitele zonei:", limits)
            print("Rezultatul verificării pozițiilor:", flags)
            print("Hull-ul zonei:", hull)
            

            
            # Pauză de 3 secunde între apeluri
            time.sleep(3)
    except KeyboardInterrupt:
        print("Execuția a fost oprită de utilizator.")
    finally:
        cv2.destroyAllWindows()
        stop_camera()
