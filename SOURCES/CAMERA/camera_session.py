#!/usr/bin/env python3
"""
Module: camera_session.py
Descriere: Modul generalizat pentru capturarea și procesarea datelor de la cameră.
  - Capturează o imagine de la cameră.
  - Preprocesează imaginea (resize, rotire etc.) fără a adăuga desene finale.
  - Detectează cutiile folosind funcțiile din BOX_DETECT.
  - Realizează îmbinarea cutiilor similare.
  - Asigură că fiecare cutie are cheia "angle" (calculată sau implicit 0).
  - Oferă două funcții:
      • capture_and_process_session() – capturează o singură imagine și returnează (image, session_data)
      • camera_loop(callback=None) – rulează continuu, apelând callback-ul pentru fiecare cadru.
"""

import os
import sys
# Adaugă directorul părinte la sys.path pentru a putea importa modulele din BOX_DETECT și UTILS
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)
    
import cv2
import math
import numpy as np
from picamera2 import Picamera2

# Importurile pentru detecție și procesare
from BOX_DETECT.letter_detect import detect_letters
from BOX_DETECT.box_detect import detect_objects
from BOX_DETECT.utils import assign_letters_to_packages, calculate_box_distance, build_session_data
from BOX_DETECT.angle_analysis import get_box_inclination_angle

# Setări implicite
ZONE_TOP_LEFT = (200, 40)
ZONE_BOTTOM_RIGHT = (295, 160)
ZONE_CENTER = ((ZONE_TOP_LEFT[0] + ZONE_BOTTOM_RIGHT[0]) // 2,
               (ZONE_TOP_LEFT[1] + ZONE_BOTTOM_RIGHT[1]) // 2)
MERGE_DISTANCE_THRESHOLD = 50

def merge_similar_packages(session_data, merge_distance_threshold=50):
    """Îmbină cutiile similare (implementare similară cu versiunea anterioară)."""
    def euclidean_distance(p1, p2):
        return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)
    
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
            merged_list.append(merged_pkg)
    
    # Generăm ID-uri unice
    new_merged = {}
    id_counts = {}
    for pkg in merged_list:
        color = pkg.get("box_color", "Unknown").capitalize()
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
            new_id = f"{base}{id_counts[base]}" if not pkg.get("letters") else base
        new_merged[new_id] = pkg
    return new_merged

def capture_and_process_session():
    """
    Capturează o imagine de la cameră și procesează datele:
      - Preprocesează (resize, rotire) fără desene finale.
      - Detectează cutiile și construiește dicționarul de sesiune.
    Returnează (processed_image, session_data).
    """
    picam = Picamera2()
    picam.configure(picam.create_still_configuration())
    picam.start()
    
    # Capturează și preprocesează imaginea
    image = picam.capture_array()
    image = cv2.resize(image, (512, 512))
    image = cv2.rotate(image, cv2.ROTATE_180)
    processed_image = image.copy()  # Copie fără desene
    
    # Detectare cutii
    detections_letters = detect_letters(picam)
    detections_boxes = detect_objects(picam)
    
    matched_packages = assign_letters_to_packages(detections_letters, detections_boxes, threshold=5)
    box_distances = calculate_box_distance(detections_boxes, ZONE_CENTER, pass_threshold=20, max_distance=30)
    session_data = build_session_data(matched_packages, box_distances, detections_boxes)
    session_data = merge_similar_packages(session_data, merge_distance_threshold=MERGE_DISTANCE_THRESHOLD)
    
    # Asigură-te că fiecare cutie are cheia "angle"
    for pkg in session_data.values():
        if "angle" not in pkg:
            try:
                pkg["angle"] = get_box_inclination_angle(processed_image, pkg, margin=5, debug=False)
            except Exception:
                pkg["angle"] = 0
                
    picam.stop()
    return processed_image, session_data

def camera_loop(callback=None):
    """
    Rulează un loop continuu care capturează un cadru, îl procesează și returnează
    (processed_image, session_data) prin apelarea callback-ului dacă este definit.
    Dacă callback este None, afișează pur și simplu imaginea procesată într-o fereastră OpenCV.
    """
    picam = Picamera2()
    picam.configure(picam.create_still_configuration())
    picam.start()
    
    while True:
        image = picam.capture_array()
        image = cv2.resize(image, (512, 512))
        image = cv2.rotate(image, cv2.ROTATE_180)
        processed_image = image.copy()
        
        # Detectare cutii
        detections_letters = detect_letters(picam)
        detections_boxes = detect_objects(picam)
        
        matched_packages = assign_letters_to_packages(detections_letters, detections_boxes, threshold=5)
        box_distances = calculate_box_distance(detections_boxes, ZONE_CENTER, pass_threshold=20, max_distance=30)
        session_data = build_session_data(matched_packages, box_distances, detections_boxes)
        session_data = merge_similar_packages(session_data, merge_distance_threshold=MERGE_DISTANCE_THRESHOLD)
        # Asigură cheia "angle"
        for pkg in session_data.values():
            if "angle" not in pkg:
                try:
                    pkg["angle"] = get_box_inclination_angle(processed_image, pkg, margin=5, debug=False)
                except Exception:
                    pkg["angle"] = 0
        
        if callback:
            callback(processed_image, session_data)
        else:
            cv2.imshow("Processed Image", cv2.cvtColor(processed_image, cv2.COLOR_RGB2BGR))
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    picam.stop()
    cv2.destroyAllWindows()
def capture_raw_image():
    """
    Capturează o imagine de la cameră și aplică doar:
      - Redimensionare la 512x512.
      - Conversie de la BGR la RGB.
    
    Această funcție sare peste orice procesare suplimentară (ex.: detecția cutiilor sau a literelor)
    și returnează direct imaginea preprocesată.
    
    Returnează:
      - raw_image: imaginea capturată și preprocesată.
    """
    picam = Picamera2()
    picam.configure(picam.create_still_configuration())
    picam.start()
    image = picam.capture_array()
    image = cv2.resize(image, (512, 512))
    #image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    picam.stop()
    return image
    
    
    
if __name__ == "__main__":
    # Exemplu de rulare continuă: se afișează fereastra cu imaginea procesată
    camera_loop()
