import threading
import cv2
from CAMERA.camera_session import init_camera, stop_camera, capture_raw_image, camera_loop
from UTILS.MAP import process_boxes, BoxMapApp

DEBUG = True  # setează la True pentru a afișa interfața, sau False pentru a rula doar bucla de captură
initial_data = {}  # Inițial, nu avem date procesate

# Callback pentru actualizarea hărții

def update_map_callback(processed_image, session_data):
    new_boxes = process_boxes(session_data)
    map_app.update_map(new_boxes)

# Thread secundar pentru afișarea imaginii camerei

def camera_display_loop():
    while True:
        try:
            image = capture_raw_image()
            imageA = cv2.flip(image, 1)

            cv2.imshow("Camera View", cv2.cvtColor(imageA, cv2.COLOR_RGB2BGR))
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        except Exception as e:
            print("Eroare în camera_display_loop:", e)
            break
    cv2.destroyAllWindows()

# Main
if DEBUG:
    init_camera()
    map_app = BoxMapApp(initial_data)

    camera_thread = threading.Thread(target=camera_loop, args=(update_map_callback,), daemon=True)
    camera_thread.start()

    display_thread = threading.Thread(target=camera_display_loop, daemon=True)
    display_thread.start()

    map_app.root.mainloop()
    stop_camera()
else:
    camera_loop()
