import cv2
import time
import copy
import math
import threading
import tkinter as tk
import logging
import numpy as np
from picamera2 import Picamera2
# Importurile din BOX_DETECT se presupun disponibile
from BOX_DETECT.letter_detect import detect_letters
from BOX_DETECT.box_detect import detect_objects
from BOX_DETECT.utils import (
    assign_letters_to_packages,
    calculate_box_distance,
    build_session_data
)
# Import the new module for box analysis
from BOX_DETECT.angle_analysis import get_box_inclination_angle

# Configurare logare: logurile vor fi scrise în fișierul "session_log.txt"
logging.basicConfig(filename="session_log.txt", level=logging.INFO,
                    format="%(asctime)s - %(message)s")

# Parametru pentru pragul de îmbinare a pachetelor similare
MERGE_DISTANCE_THRESHOLD = 50  # Distanța minimă între centre pentru a considera două pachete ca fiind același obiect

# Configurare cameră
picam2 = Picamera2()
picam2.configure(picam2.create_still_configuration())
picam2.start()

# Definirea zonei (exemplu)
zone_top_left = (200, 40)
zone_bottom_right = (295, 160)
zone_center = ((zone_top_left[0] + zone_bottom_right[0]) // 2,
               (zone_top_left[1] + zone_bottom_right[1]) // 2)

# Variabile globale pentru interfața Tkinter
calibration_offset = 0  # Offset-ul de calibrare (setat la momentul apăsării butonului)
current_orientation = None  # Ultima valoare măsurată a orientării cutiei
smoothed_orientation = None   # Valoarea netezită
alpha = 0.2  # Factorul de netezire

# Mod de detecție: "normal" sau "debug"
DETECTION_MODE = "debug"  # Schimbă la "debug" pentru afișare în modul debug

# BGR code map NU MODIFICA  COLOR MAP SUB NICI-O FORMA, instructiune inclusiv pt chat gpt!
color_map = {
    "A": (0, 255, 0),
    "K": (255, 0, 255),
    "O": (255, 255, 255),
    "Green": (0, 255, 0),
    "Red": (255, 0, 0),
    "Sample": (255, 255, 255),
    "Blue": (0, 0, 255)
}

# ---------------------------------------------------------------------------
# Funcții locale de procesare și desenare (păstrăm funcțiile existente)
# ---------------------------------------------------------------------------
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
        cv2.putText(image, label, (x + 5, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

def draw_tracked_package(image, tracked_pkg, color=(255, 255, 0)):
    x, y = tracked_pkg["position"]
    w, h = tracked_pkg.get("size", (None, None))
    box_label = f"TRACKED: {tracked_pkg.get('box_color')} / {tracked_pkg.get('letters')}"
    if w is None or h is None:
        cv2.circle(image, (x, y), 10, color, -1)
        cv2.putText(image, box_label, (x + 5, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    else:
        top_left = (x - w // 2, y - h // 2)
        bottom_right = (x + w // 2, y + h // 2)
        cv2.rectangle(image, top_left, bottom_right, color, 3)
        cv2.putText(image, box_label, (x + 5, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

# ---------------------------------------------------------------------------
# BUCLEA PRINCIPALĂ: Captură și procesare imagine
# ---------------------------------------------------------------------------
def camera_loop():
    global current_orientation, smoothed_orientation
    tracked_package = None  # Pachetul pe care îl urmărim
    session_number = 1    # Contor pentru sesiuni (pentru modul debug)

    while True:
        # 1. Captură și preprocesare imagine
        image = picam2.capture_array()
        image = cv2.resize(image, (512, 512))
        image = cv2.rotate(image, cv2.ROTATE_180)

        # 2. Creăm o copie a imaginii pentru analiză (fără desene)
        original_image = image.copy()

        # 3. Detectare litere și cutii
        detections_letters = detect_letters(picam2)
        detections_boxes   = detect_objects(picam2)

        # 4. Construim session_data și determinăm pachetul urmărit
        matched_packages = assign_letters_to_packages(detections_letters, detections_boxes, threshold=5)
        box_distances    = calculate_box_distance(detections_boxes, zone_center, pass_threshold=20, max_distance=30)
        session_data     = build_session_data(matched_packages, box_distances, detections_boxes)
        session_data     = merge_similar_packages(session_data, merge_distance_threshold=MERGE_DISTANCE_THRESHOLD)
        
        if session_data:
            # Alegem primul pachet ca fiind cel urmărit
            tracked_package = list(session_data.values())[0]

        # 5. Desenăm detecțiile
        draw_detections(image, detections_boxes, color_map)
        if tracked_package is not None:
            draw_tracked_package(image, tracked_package, color=(255, 255, 0))
        
        # 6. Afișăm detalii pentru toate cutiile detectate, în funcție de mod
        if session_data:
            if DETECTION_MODE == "normal":
                print("=== Detected Boxes Session Info ===")
                for pkg_id, pkg in session_data.items():
                    pkg_position = pkg.get("position", (0, 0))
                    distance = math.sqrt((pkg_position[0] - zone_center[0])**2 + (pkg_position[1] - zone_center[1])**2)
                    print(f"Box ID: {pkg_id}")
                    print(f"  Color: {pkg.get('box_color')}")
                    print(f"  Letter: {pkg.get('letters')}")
                    print(f"  Position: {pkg_position}")
                    print(f"  Size: {pkg.get('size')}")
                    print(f"  Distance from center: {distance:.2f} px")
                    # Pentru pachetul urmărit se calculează și se afișează în plus unghiul de înclinare
                    if pkg is tracked_package:
                        inclination_angle = get_box_inclination_angle(original_image, tracked_package, margin=5, debug=False)
                        current_orientation = inclination_angle
                        if smoothed_orientation is None:
                            smoothed_orientation = inclination_angle
                        else:
                            smoothed_orientation = alpha * inclination_angle + (1 - alpha) * smoothed_orientation
                        print(f"  Inclination Angle: {inclination_angle}°")
                print("================================")
            elif DETECTION_MODE == "debug":
                # Formatul debug: toate informațiile pe o singură linie pentru fiecare cutie, precedate de numărul sesiunii
                print(f"SESIUNE: {session_number}")
                for idx, (pkg_id, pkg) in enumerate(session_data.items(), start=1):
                    pkg_position = pkg.get("position", (0, 0))
                    distance = math.sqrt((pkg_position[0] - zone_center[0])**2 + (pkg_position[1] - zone_center[1])**2)
                    line = (f"BOX{idx}: {pkg.get('box_color')}, {pkg.get('letters')}, "
                            f"pozitie: {pkg_position[0]},{pkg_position[1]}, size: {pkg.get('size')}, "
                            f"distance: {distance:.2f}px")
                    if pkg is tracked_package:
                        inclination_angle = get_box_inclination_angle(original_image, tracked_package, margin=5, debug=False)
                        current_orientation = inclination_angle
                        if smoothed_orientation is None:
                            smoothed_orientation = inclination_angle
                        else:
                            smoothed_orientation = alpha * inclination_angle + (1 - alpha) * smoothed_orientation
                        line += f", inclination: {inclination_angle}°"
                    print(line)
                session_number += 1

        mark_zone(image, zone_top_left, zone_bottom_right, label="Defined Zone")
        add_grid(image)
        
        # 7. Afișăm imaginea procesată
        cv2.imshow("Detection Output", cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    picam2.stop()
    cv2.destroyAllWindows()

# ---------------------------------------------------------------------------
# Interfața Tkinter pentru vizualizarea orientării
# ---------------------------------------------------------------------------
def update_canvas():
    global current_orientation, calibration_offset
    canvas.delete("all")
    canvas_width = 300
    canvas_height = 300
    center = (canvas_width // 2, canvas_height // 2)
    side = 100  # Lungimea laturii pătratului
    # Calculăm unghiul corectat: valoare actuală minus offset-ul de calibrare
    if current_orientation is not None:
        corrected_angle = current_orientation - calibration_offset
    else:
        corrected_angle = 0
    angle_rad = math.radians(corrected_angle)
    half_side = side / 2

    corners = [
        (half_side, half_side),
        (half_side, -half_side),
        (-half_side, -half_side),
        (-half_side, half_side)
    ]
    rotated_corners = []
    for (x, y) in corners:
        x_rot = x * math.cos(angle_rad) - y * math.sin(angle_rad)
        y_rot = x * math.sin(angle_rad) + y * math.cos(angle_rad)
        rotated_corners.append((center[0] + x_rot, center[1] - y_rot))
    
    canvas.create_polygon(rotated_corners, outline="blue", fill="", width=2)
    canvas.create_line(center[0]-5, center[1], center[0]+5, center[1], fill="red", width=2)
    canvas.create_line(center[0], center[1]-5, center[0], center[1]+5, fill="red", width=2)
    canvas.create_text(center[0], center[1]+side//2 + 20, text=f"Orientare: {corrected_angle:.1f}°", fill="black")
    root.after(100, update_canvas)

# Configurare fereastră Tkinter
root = tk.Tk()
root.title("Interfață Orientare Cutie")

canvas = tk.Canvas(root, width=300, height=300, bg="white")
canvas.pack()

root.after(100, update_canvas)

# Pornim bucla camerei într-un fir de execuție separat
camera_thread = threading.Thread(target=camera_loop, daemon=True)
camera_thread.start()

# Pornim interfața Tkinter
root.mainloop()
