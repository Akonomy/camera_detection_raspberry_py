import cv2
import time
import copy
import math
from picamera2 import Picamera2
import logging

# Configurare logare: logurile vor fi scrise în fișierul "session_log.txt"
logging.basicConfig(filename="session_log.txt", level=logging.INFO,
                    format="%(asctime)s - %(message)s")

# Parametru pentru pragul de îmbinare a pachetelor similare
MERGE_DISTANCE_THRESHOLD = 50

# Importul modulelor de detecție
from BOX_DETECT.letter_detect import detect_letters
from BOX_DETECT.box_detect import detect_objects
from BOX_DETECT.utils import (
    assign_letters_to_packages,
    calculate_box_distance,
    build_session_data,
    get_high_priority_package,
    update_tracked_package
)
# Funcții pentru coordonate reale și obținerea comenzii
from UTILS.REAL import getRealCoordinates
from UTILS.COARSE_DIRECTIONS import getFirstCommand

# Variabile globale pentru procesare
tracked_package = None       # Pachetul curent urmărit
last_session_data = {}       # Ultima sesiune de date

# Configurarea camerei
picam2 = Picamera2()
picam2.configure(picam2.create_still_configuration())
picam2.start()

# Definirea zonei pentru calculul distanței
zone_top_left = (200, 40)
zone_bottom_right = (295, 160)
zone_center = ((zone_top_left[0] + zone_bottom_right[0]) // 2,
               (zone_top_left[1] + zone_bottom_right[1]) // 2)

# Funcții pentru desenarea pe imagine
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
        top_left = (x - w // 2, y - h // 2)
        bottom_right = (x + w // 2, y + h // 2)
        cv2.rectangle(image, top_left, bottom_right, color, 2)
        cv2.putText(image, label, (x + 5, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

def draw_tracked_package(image, tracked_pkg, color=(255, 255, 0)):
    x, y = tracked_pkg["position"]
    w, h = tracked_pkg.get("size", (None, None))
    box_label = f"TRACKED: {tracked_pkg.get('box_color')} / {tracked_pkg.get('letters')}"
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

# Funcție pentru fuzionarea pachetelor similare
def euclidean_distance(p1, p2):
    return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

def merge_similar_packages(session_data, merge_distance_threshold=50):
    groups = {}
    for key, pkg in session_data.items():
        color = pkg.get("box_color")
        letters = pkg.get("letters", [])
        letter = letters[0] if letters else None
        group_key = (color, letter)
        groups.setdefault(group_key, []).append(pkg)

    merged_packages = {}
    merged_id = 1
    for group_key, pkg_list in groups.items():
        clusters = []
        for pkg in pkg_list:
            pos = pkg.get("position")
            added = False
            for cluster in clusters:
                cluster_centroid = (
                    sum([p[0] for p in cluster["positions"]]) / len(cluster["positions"]),
                    sum([p[1] for p in cluster["positions"]]) / len(cluster["positions"])
                )
                if euclidean_distance(pos, cluster_centroid) < merge_distance_threshold:
                    cluster["positions"].append(pos)
                    cluster["packages"].append(pkg)
                    added = True
                    break
            if not added:
                clusters.append({"positions": [pos], "packages": [pkg]})
        for cluster in clusters:
            if len(cluster["packages"]) == 1:
                merged_pkg = cluster["packages"][0]
            else:
                positions = [pkg.get("position") for pkg in cluster["packages"]]
                xs = [p[0] for p in positions]
                ys = [p[1] for p in positions]
                new_center = (sum(xs)/len(xs), sum(ys)/len(ys))
                boxes = []
                for pkg in cluster["packages"]:
                    pos = pkg.get("position")
                    size = pkg.get("size")
                    if size is not None and None not in size:
                        w, h = size
                        top_left = (pos[0] - w/2, pos[1] - h/2)
                        bottom_right = (pos[0] + w/2, pos[1] + h/2)
                        boxes.append((top_left, bottom_right))
                if boxes:
                    min_x = min([b[0][0] for b in boxes])
                    min_y = min([b[0][1] for b in boxes])
                    max_x = max([b[1][0] for b in boxes])
                    max_y = max([b[1][1] for b in boxes])
                    new_size = (int(max_x - min_x), int(max_y - min_y))
                else:
                    new_size = None
                merged_pkg = {
                    "box_color": group_key[0],
                    "letters": [group_key[1]] if group_key[1] is not None else [],
                    "position": (int(new_center[0]), int(new_center[1])),
                    "size": new_size
                }
            merged_packages[f"merged_{merged_id}"] = merged_pkg
            merged_id += 1
    return merged_packages

# Hartă de culori pentru desen
color_map = {
    "A": (0, 255, 0),
    "K": (255, 0, 255),
    "O": (255, 255, 255),
    "Green": (0, 255, 0),
    "Red": (255, 0, 0),
    "Sample": (255, 255, 255),
    "Blue": (0, 0, 255)
}

# Funcție pentru procesarea pachetului urmărit:
# Aceasta calculează coordonatele reale ale pachetului, obține prima comandă prin getFirstCommand
# și apoi printează informațiile relevante.
def process_tracked_package(tracked_pkg):
    x, y = tracked_pkg["position"]
    # Obține coordonate reale
    x_real, y_real = getRealCoordinates(x, y)
    # Obține prima comandă bazată pe coordonatele reale
    comanda = getFirstCommand(x_real, y_real)
    # Afișează informațiile despre pachetul detectat
    print(f"Tracked Package Position: {tracked_pkg['position']}")
    print(f"Real Coordinates: ({x_real}, {y_real})")
    print("Move Command:")
    print(comanda)
    logging.info("Tracked package info: position {} | real coordinates: {} | command: {}".format(
        tracked_pkg['position'], (x_real, y_real), comanda))

# Bucleul principal de procesare a camerei
def camera_loop():
    global tracked_package, last_session_data
    while True:
        image = picam2.capture_array()
        image = cv2.resize(image, (512, 512))
        image = cv2.rotate(image, cv2.ROTATE_180)

        # Detectează literele și cutiile din cadru
        detections_letters = detect_letters(picam2)
        detections_boxes   = detect_objects(picam2)

        # Asociază literele cu pachetele și calculează distanța până la cutii
        matched_packages = assign_letters_to_packages(detections_letters, detections_boxes, threshold=5)
        box_distances    = calculate_box_distance(detections_boxes, zone_center, pass_threshold=20, max_distance=30)

        session_data = build_session_data(matched_packages, box_distances, detections_boxes)
        # Fuzionează pachetele similare pentru a obține o singură detecție per obiect real
        session_data = merge_similar_packages(session_data, merge_distance_threshold=MERGE_DISTANCE_THRESHOLD)
        last_session_data = session_data

        # Logare și afișare a pachetelor detectate
        detected_packages_log = ", ".join([f"{key}: color {info['box_color']}, letter {info['letters']}, position {info['position']}" 
                                           for key, info in session_data.items()])
        logging.info("Detected packages: " + detected_packages_log)
        print("\nDetected packages:")
        for key, info in session_data.items():
            print(f"{key} => color: {info['box_color']}, letter: {info['letters']}, position: {info['position']}")

        # Alegerea sau actualizarea pachetului urmărit
        if tracked_package is None:
            high_pkg_key, high_pkg_info = get_high_priority_package(session_data)
            if high_pkg_key is not None:
                high_pkg_info["miss_detections"] = 0
                high_pkg_info["stable"] = False
                tracked_package = high_pkg_info
        else:
            result = update_tracked_package(tracked_package, session_data, distance_threshold=150)
            if result is False:
                print("Pachetul urmărit nu mai este detectat. Alegem alt pachet.")
                tracked_package = None
            elif result == "TOO_FAR":
                print("Salt mare de distanță detectat. Alegem alt pachet.")
                tracked_package = None
            else:
                tracked_package = result

        # Desenarea detecțiilor pe imagine
        draw_detections(image, detections_boxes, color_map)
        if tracked_package is not None:
            draw_tracked_package(image, tracked_package, color=(255, 255, 0))
            # Procesarea pachetului urmărit: calcularea coordonatelor reale și determinarea comenzii,
            # apoi afișarea acestor informații în consolă.
            process_tracked_package(tracked_package)

        mark_zone(image, zone_top_left, zone_bottom_right, label="Defined Zone")
        add_grid(image)

        cv2.imshow("Detection Output", cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    picam2.stop()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    camera_loop()
