import cv2
import time
from picamera2 import Picamera2


# Importă funcția de comunicare
from USART_COM.serial_module import process_command



# Module de detecție
from BOX_DETECT.letter_detect import detect_letters
from BOX_DETECT.box_detect import detect_objects

# Funcții utilitare din BOX_DETECT/utils.py
from BOX_DETECT.utils import (
    assign_letters_to_packages,
    calculate_box_distance,
    build_session_data,
    get_high_priority_package,
    update_tracked_package,
    compute_movement_command,
    fine_adjustment_command
)

# Importul modulului USART (presupunem că fișierul usart.py este în directorul USART_COM)
from USART_COM import usart

# --------------------------------------------------
# CONFIGURAREA CAMEREI ȘI A ZONEI
# --------------------------------------------------
picam2 = Picamera2()
picam2.configure(picam2.create_still_configuration())
picam2.start()

zone_top_left = (200, 40)
zone_bottom_right = (295, 160)
zone_center = ((zone_top_left[0] + zone_bottom_right[0]) // 2,
               (zone_top_left[1] + zone_bottom_right[1]) // 2)

# --------------------------------------------------
# FUNCȚII PENTRU DESENAREA PE CADRU
# --------------------------------------------------
def add_grid(image, grid_size=64):
    h, w = image.shape[:2]
    for x in range(0, w, grid_size):
        cv2.line(image, (x, 0), (x, h), (255, 255, 255), 1)
    for y in range(0, h, grid_size):
        cv2.line(image, (0, y), (w, y), (255, 255, 255), 1)

def mark_zone(image, top_left, bottom_right, label="Zone", color=(0, 0, 255), thickness=2):
    cv2.rectangle(image, top_left, bottom_right, color, thickness)
    label_position = (top_left[0], top_left[1] - 10)
    cv2.putText(image, label, label_position, cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

def draw_detections(image, detections, color_map):
    for obj in detections:
        x, y = obj["x"], obj["y"]
        w, h = obj["width"], obj["height"]
        label = obj["label"]
        color = color_map.get(label, (255, 255, 255))

        # Desenează chenarul
        top_left = (x - w // 2, y - h // 2)
        bottom_right = (x + w // 2, y + h // 2)
        cv2.rectangle(image, top_left, bottom_right, color, 2)
        cv2.putText(image, label, (x + 5, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

def draw_tracked_package(image, tracked_pkg, color=(255, 255, 0)):
    x, y = tracked_pkg["position"]
    w, h = tracked_pkg["size"]
    box_label = f"TRACKED: {tracked_pkg['box_color']} / {tracked_pkg['letters']}"

    if w is None or h is None:
        cv2.circle(image, (x, y), 10, color, -1)
        cv2.putText(image, box_label, (x + 5, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        return

    top_left = (x - w // 2, y - h // 2)
    bottom_right = (x + w // 2, y + h // 2)
    cv2.rectangle(image, top_left, bottom_right, color, 3)
    cv2.putText(image, box_label, (x + 5, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

# --------------------------------------------------
# HARTĂ DE CULORI PENTRU DESEN
# --------------------------------------------------
color_map = {
    "A": (0, 255, 0),      # Verde
    "K": (255, 0, 255),    # Magenta
    "O": (255, 255, 255),  # Alb
    "Green": (0, 255, 0),
    "Red": (255, 0, 0),
    "Sample": (255, 255, 255),
    "Blue": (0, 0, 255)
}

# --------------------------------------------------
# VARIABILE PENTRU URMĂRIRE ȘI CONTROL USART
# --------------------------------------------------
tracked_package = None      # Pachetul curent urmărit
MISS_THRESHOLD = 5          # După 5 sesiuni fără detecție, se renunță la urmărire
DISTANCE_JUMP_THRESHOLD = 150  # Salt maxim permis în distanță

# Flag pentru accesul la mașină prin USART
machine_access_granted = False

# --------------------------------------------------
# MAIN LOOP
# --------------------------------------------------
while True:
    # 1) Capturează imaginea, redimensionează și rotește
    image = picam2.capture_array()
    image = cv2.resize(image, (512, 512))
    image = cv2.rotate(image, cv2.ROTATE_180)

    # 2) Detectează litere și pachete
    detections_letters = detect_letters(picam2)
    detections_boxes   = detect_objects(picam2)

    # 3) Asociază literele cu pachetele și calculează distanțele față de centru
    matched_packages = assign_letters_to_packages(detections_letters, detections_boxes, threshold=5)
    box_distances    = calculate_box_distance(detections_boxes, zone_center, pass_threshold=20, max_distance=30)

    # 4) Construiește datele de sesiune
    session_data = build_session_data(matched_packages, box_distances, detections_boxes)

    # 5) Alege sau actualizează pachetul urmărit
    if tracked_package is None:
        high_pkg_key, high_pkg_info = get_high_priority_package(session_data)
        if high_pkg_key is not None:
            high_pkg_info["miss_detections"] = 0
            tracked_package = high_pkg_info
    else:
        result = update_tracked_package(
            tracked_package, 
            session_data, 
            distance_threshold=DISTANCE_JUMP_THRESHOLD
        )
        if result is False:
            if not tracked_package["letters"]:
                print("Pachetul fără litere nu mai este detectat => alegem un alt pachet.")
                high_pkg_key, high_pkg_info = get_high_priority_package(session_data)
                tracked_package = high_pkg_info if high_pkg_key is not None else None
            else:
                tracked_package["miss_detections"] += 1
                if tracked_package["miss_detections"] > MISS_THRESHOLD:
                    print("Pachetul urmărit a lipsit prea mult => renunțăm la urmărire.")
                    tracked_package = None
        elif result == "TOO_FAR":
            print("Salt mare de distanță => renunțăm la urmărire și alegem un nou pachet.")
            tracked_package = None
            high_pkg_key, high_pkg_info = get_high_priority_package(session_data)
            tracked_package = high_pkg_info if high_pkg_key is not None else None
        else:
            tracked_package = result

    # 6) Desenează toate detecțiile pe imagine
    draw_detections(image, detections_boxes, color_map)

    # 7) Dacă există un pachet urmărit, îl desenăm și trimitem comenzile către mașină
    if tracked_package is not None:
        draw_tracked_package(image, tracked_package, color=(255, 255, 0))
        status = tracked_package["status"]

       

    # 8) Desenează zona definită și grid-ul
    mark_zone(image, zone_top_left, zone_bottom_right, label="Defined Zone")
    add_grid(image)

    # 9) (Opțional) Afișează datele de sesiune în consolă
    print("\n--- SESSION DATA ---")
    for pkg_key, pkg_info in session_data.items():
        print(f"{pkg_key} => {pkg_info}")
    print("--- END SESSION DATA ---")

    # 10) Afișează cadrul final
    cv2.imshow("Detection Output", cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Cleanup la final
picam2.stop()
cv2.destroyAllWindows()
