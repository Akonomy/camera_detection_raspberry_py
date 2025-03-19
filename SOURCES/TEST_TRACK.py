#!/usr/bin/env python3
"""
Modul: box_session_processor
Descriere: Captură, procesare și afișare imagine cu OpenCV.
Se detectează cutiile, se calculează datele și se creează un dicționar de sesiune,
care este printat și trimis către interfața Tkinter (din UTILS/MAP) pentru afișarea hărții.
Camera rulează într-un thread separat, iar interfața Tkinter rulează în firul principal.
"""

import cv2
import time
import math
import logging
import threading
import numpy as np
from picamera2 import Picamera2

from BOX_DETECT.letter_detect import detect_letters
from BOX_DETECT.box_detect import detect_objects
from BOX_DETECT.utils import assign_letters_to_packages, calculate_box_distance, build_session_data
from BOX_DETECT.angle_analysis import get_box_inclination_angle

from UTILS.MAP import process_boxes, BoxMapApp,analyze_target_zones

logging.basicConfig(filename="session_log.txt", level=logging.INFO,
                    format="%(asctime)s - %(message)s")

MERGE_DISTANCE_THRESHOLD = 50

picam2 = Picamera2()
picam2.configure(picam2.create_still_configuration())
picam2.start()

zone_top_left = (200, 40)
zone_bottom_right = (295, 160)
zone_center = ((zone_top_left[0] + zone_bottom_right[0]) // 2,
               (zone_top_left[1] + zone_bottom_right[1]) // 2)

def round_to_half(value):
    return round(value * 2) / 2

def get_real_y(detected_y):
    return 0.05587 * detected_y - 4.47

def get_center_x(detected_y):
    return 0.0203 * detected_y + 230.38

def get_scale_x(detected_y):
    return 0.0000608 * detected_y + 0.046936

def getRealCoordinates(detected_x, detected_y):
    center_x = get_center_x(detected_y)
    scale_x = get_scale_x(detected_y)
    real_x = (detected_x - center_x) * scale_x
    real_y = get_real_y(detected_y)
    return round_to_half(real_x), round_to_half(real_y)

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
    merged_list = []
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
                new_center = (sum(xs) / len(xs), sum(ys) / len(ys))
                boxes = []
                for pkg in cluster["packages"]:
                    pos = pkg.get("position")
                    size = pkg.get("size")
                    if size is not None and None not in size:
                        w, h = size
                        top_left = (pos[0] - w / 2, pos[1] - h / 2)
                        bottom_right = (pos[0] + w / 2, pos[1] + h / 2)
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
            merged_list.append(merged_pkg)
    # Generăm ID-uri din culoare și literă
    new_merged = {}
    id_counts = {}
    for pkg in merged_list:
        color = pkg["box_color"].capitalize()
        if pkg.get("letters"):
            letter = pkg["letters"][0].upper()
            base = f"{color}{letter}"
        else:
            base = f"{color}"
        if base in id_counts:
            id_counts[base] += 1
            new_id = f"{base}{id_counts[base]}"
        else:
            id_counts[base] = 1
            # Dacă nu are literă, chiar și prima apariție primește numărul 1
            new_id = f"{base}{id_counts[base]}" if not pkg.get("letters") else base
        new_merged[new_id] = pkg
    return new_merged

def add_grid(image, grid_size=64):
    h, w = image.shape[:2]
    for x in range(0, w, grid_size):
        cv2.line(image, (x,0), (x,h), (255,255,255), 1)
    for y in range(0, h, grid_size):
        cv2.line(image, (0,y), (w,y), (255,255,255), 1)

def mark_zone(image, top_left, bottom_right, label="Zone", color=(0,0,255), thickness=2):
    cv2.rectangle(image, top_left, bottom_right, color, thickness)
    label_position = (top_left[0], top_left[1]-10)
    cv2.putText(image, label, label_position, cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

def draw_detections(image, detections, color_map):
    for obj in detections:
        x, y = obj["x"], obj["y"]
        w, h = obj["width"], obj["height"]
        label = obj["label"]
        color = color_map.get(label, (255,255,255))
        top_left = (x - w//2, y - h//2)
        bottom_right = (x + w//2, y + h//2)
        cv2.rectangle(image, top_left, bottom_right, color, 2)
        cv2.putText(image, label, (x+5, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

def draw_tracked_package(image, tracked_pkg, color=(255,255,0)):
    x, y = tracked_pkg["position"]
    w, h = tracked_pkg.get("size", (None,None))
    box_label = f"TRACKED: {tracked_pkg.get('box_color')} / {tracked_pkg.get('letters')}"
    if w is None or h is None:
        cv2.circle(image, (x,y), 10, color, -1)
        cv2.putText(image, box_label, (x+5, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    else:
        top_left = (x - w//2, y - h//2)
        bottom_right = (x + w//2, y + h//2)
        cv2.rectangle(image, top_left, bottom_right, color, 3)
        cv2.putText(image, box_label, (x+5, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

color_map = {
    "A": (0,255,0),
    "K": (255,0,255),
    "O": (255,255,255),
    "Green": (0,255,0),
    "Red": (255,0,0),
    "Sample": (255,255,255),
    "Blue": (0,0,255)
}

# --- Funcții noi pentru analiză sesiune ---

def classify_box_relative(other, target):
    x, y = other["real_position"]
    bx, by = target["real_position"]
    left = x - 1.5
    right = x + 1.5
    top = y + 1.5
    bottom = y - 1.5
    danger_A = 0.0
    if right > (bx - 10.5) and left < (bx + 10.5):
        if bottom < (by - 7):
            danger_A = min(top, by - 7) - bottom
    danger_B = 0.0
    horiz_overlap_B = max(0, min(right, bx + 5) - max(left, bx - 5))
    if horiz_overlap_B > 0:
        vertical_overlap_B = max(0, min(top, by - 1.5) - max(bottom, by - 7))
        danger_B = vertical_overlap_B
    danger_overlap = max(danger_A, danger_B)
    if danger_overlap >= 0.5:
        return "Danger"
    warning_left = 0.0
    horiz_overlap_left = max(0, min(right, bx - 5) - max(left, bx - 10.5))
    if horiz_overlap_left > 0:
        vertical_overlap_left = max(0, min(top, by - 1.5) - max(bottom, by - 7))
        warning_left = vertical_overlap_left
    warning_right = 0.0
    horiz_overlap_right = max(0, min(right, bx + 10.5) - max(left, bx + 5))
    if horiz_overlap_right > 0:
        vertical_overlap_right = max(0, min(top, by - 1.5) - max(bottom, by - 7))
        warning_right = vertical_overlap_right
    warning_overlap = max(warning_left, warning_right)
    if warning_overlap >= 1.0:
        return "Warning"
    return "Safe"

def select_best_candidate(boxes):
    best_candidate_id = None
    best_candidate = None
    best_danger_count = float('inf')
    best_dist = float('inf')
    for box_id, box in boxes.items():
        danger_count = 0
        for other_id, other in boxes.items():
            if other_id == box_id:
                continue
            if classify_box_relative(other, box) == "Danger":
                danger_count += 1
        x, y = box["real_position"]
        d = math.sqrt(x*x + y*y)
        if danger_count == 0:
            if d < best_dist:
                best_candidate_id = box_id
                best_candidate = box
                best_dist = d
                best_danger_count = 0
        else:
            if best_candidate is None or best_danger_count > danger_count or (best_danger_count == danger_count and d < best_dist):
                best_candidate_id = box_id
                best_candidate = box
                best_danger_count = danger_count
                best_dist = d
    return best_candidate_id, best_candidate

def analyze_session_boxes(session, target_box_id=None, mandatory=False):
    if target_box_id is not None and target_box_id in session:
        candidate_id = target_box_id
        candidate = session[target_box_id]
        target_specified = True
    else:
        candidate_id, candidate = select_best_candidate(session)
        target_specified = False

    danger_list = []
    warning_list = []
    for box_id, box in session.items():
        if box_id == candidate_id:
            continue
        cls = classify_box_relative(box, candidate)
        if cls == "Danger":
            danger_list.append((box_id, box))
        elif cls == "Warning":
            warning_list.append((box_id, box))
    candidate_y = candidate["real_position"][1]
    danger_list.sort(key=lambda item: abs(item[1]["real_position"][1] - candidate_y))
    warning_list.sort(key=lambda item: abs(item[1]["real_position"][1] - candidate_y))

    if mandatory:
        if danger_list:
            result_list = [item[0] for item in danger_list]
        elif warning_list:
            result_list = [item[0] for item in warning_list]
        else:
            result_list = [candidate_id]
    else:
        if danger_list or warning_list:
            result_list = [item[0] for item in danger_list] + [item[0] for item in warning_list]
        else:
            result_list = [candidate_id]

    target_in_first = 1 if result_list[0] == candidate_id else 0
    danger_count = len(danger_list)
    target_specified_in_session = 1 if (target_specified and candidate_id == target_box_id) else 0

    flags = {
        "target_in_first": target_in_first,
        "danger_neighbor_count": danger_count,
        "target_specified_in_session": target_specified_in_session
    }
    return result_list, flags

MAP_UPDATE_INTERVAL = 5
last_map_update = 0

# Global instanță a interfeței Tkinter
map_app = None

def camera_loop():
    global last_map_update, picam2, map_app
    session_number = 1

    while True:
        image = picam2.capture_array()
        image = cv2.resize(image, (512,512))
        image = cv2.rotate(image, cv2.ROTATE_180)
        original_image = image.copy()

        detections_letters = detect_letters(picam2)
        detections_boxes = detect_objects(picam2)

        matched_packages = assign_letters_to_packages(detections_letters, detections_boxes, threshold=5)
        box_distances = calculate_box_distance(detections_boxes, zone_center, pass_threshold=20, max_distance=30)
        session_data = build_session_data(matched_packages, box_distances, detections_boxes)
        session_data = merge_similar_packages(session_data, merge_distance_threshold=MERGE_DISTANCE_THRESHOLD)
        tracked_package = None
        if session_data:
            tracked_package = list(session_data.values())[0]

        draw_detections(image, detections_boxes, color_map)
        if tracked_package is not None:
            draw_tracked_package(image, tracked_package, color=(255,255,0))
        mark_zone(image, zone_top_left, zone_bottom_right, label="Defined Zone")
        add_grid(image)

        session_dict = {}
        if session_data:
            
            
           
            for box_id, pkg in session_data.items():
                pkg_position = pkg.get("position", (0,0))
                distance = math.sqrt((pkg_position[0]-zone_center[0])**2 + (pkg_position[1]-zone_center[1])**2)
                try:
                    angle = get_box_inclination_angle(original_image, pkg, margin=5, debug=False)
                except Exception:
                    angle = 0
                session_dict[box_id] = {
                    "box_color": pkg.get("box_color"),
                    "letters": pkg.get("letters"),
                    "position": pkg_position,
                    "size": pkg.get("size"),
                    "distance_from_center": round(distance,2),
                    "angle": angle
                }

        print(f"Session {session_number}:")
        # for box_id, details in session_dict.items():
            # print(f"{box_id}: {details}")
        # print("-"*50)
        session_number += 1
        
        

        if session_data and (time.time()-last_map_update) > MAP_UPDATE_INTERVAL:
            try:
                map_data = process_boxes(session_dict)
                
              
                safe_flag, danger_list,proxi_list, warning_list = analyze_target_zones(map_data, target_box_id="BlueK")
                print("[.DANGER.]\n",danger_list,"\n[.WARNING.]\n" ,warning_list, "\n[.PROXI.]\n" ,proxi_list)
                if map_app is not None:
                    map_app.root.after(0, lambda: map_app.update_map(map_data))
                last_map_update = time.time()
                
            except Exception as e:
                logging.error("Eroare la actualizarea hărții: " + str(e))

        cv2.imshow("Detection Output", cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    picam2.stop()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    DEBUG = True  # setează la True pentru a afișa interfața, sau False pentru a o dezactiva

    initial_data = {}  # începe cu dicționar gol

    if DEBUG:
        map_app = BoxMapApp(initial_data)
        camera_thread = threading.Thread(target=camera_loop, daemon=True)
        camera_thread.start()
        map_app.root.mainloop()
    else:
        # Nu se afișează interfața Tkinter; rulează direct camera_loop
        camera_loop()
