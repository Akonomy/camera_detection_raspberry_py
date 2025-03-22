#!/usr/bin/env python3
"""
Module: camera_session.py
Descriere: Modul generalizat pentru capturarea și procesarea datelor de la cameră.
  - Se inițializează camera o singură dată cu init_camera().
  - Funcțiile de capturare (capture_and_process_session, camera_loop, capture_raw_image, camera_loop_raw)
    utilizează instanța inițializată.
  - Camera se oprește prin apelarea funcției stop_camera().
  
Funcții principale:
  • init_camera() – inițializează și pornește camera (se apelează o singură dată).
  • stop_camera() – oprește camera.
  • capture_and_process_session() – capturează o singură imagine și returnează (image, session_data).
  • camera_loop(callback=None, only_image=False) – rulează continuu, apelând callback-ul pentru fiecare cadru.
  • capture_raw_image() – capturează o imagine "raw" preprocesată.
  • camera_loop_raw(callback=None) – rulează continuu și returnează doar copia imaginii brute preprocesate.
"""

import os
import sys
import math
import cv2
import numpy as np
from picamera2 import Picamera2

# Adaugă directorul părinte la sys.path pentru a putea importa modulele din BOX_DETECT și UTILS
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

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

# Variabilă globală pentru instanța camerei
global_picam = None

def init_camera():
    """
    Inițializează și pornește camera, păstrând instanța într-o variabilă globală.
    Dacă o instanță existentă este detectată, aceasta este oprită mai întâi.
    """
    global global_picam
    if global_picam is not None:
        try:
            print("Camera este deja deschisă. Se încearcă închiderea acesteia înainte de reinițializare.")
            stop_camera()
        except Exception as e:
            print("Eroare la închiderea camerei: ", e)
    global_picam = Picamera2()
    global_picam.configure(global_picam.create_still_configuration())
    global_picam.start()
    print("Camera a fost inițializată și pornește.")


def stop_camera():
    """
    Oprește camera și resetează instanța globală.
    """
    global global_picam
    if global_picam is not None:
        global_picam.stop()
        global_picam = None
        print("Camera a fost oprită.")
    else:
        print("Camera nu a fost inițializată.")

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
    global global_picam
    if global_picam is None:
        raise Exception("Camera nu a fost inițializată. Apelează init_camera() înainte.")
    
    # Capturează și preprocesează imaginea
    image = global_picam.capture_array()
    image = cv2.resize(image, (512, 512))
    #image = cv2.rotate(image, cv2.ROTATE_180)
    processed_image = image.copy()  # Copie fără desene
    
    # Detectare cutii
    detections_letters = detect_letters(global_picam)
    detections_boxes = detect_objects(global_picam)
    
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
                
    return processed_image, session_data

def camera_loop(callback=None, only_image=False):
    """
    Rulează un loop continuu care capturează un cadru, îl procesează și returnează
    (processed_image, session_data) prin apelarea callback-ului dacă este definit.
    Dacă callback este None, afișează imaginea procesată într-o fereastră OpenCV.
    
    Parametrul only_image:
      - Dacă este True, se omite complet procesarea cutiilor și se returnează o sesiune goală.
      - Modul poate fi schimbat dinamic, de exemplu prin tasta 't'.
    """
    global global_picam
    if global_picam is None:
        raise Exception("Camera nu a fost inițializată. Apelează init_camera() înainte.")
    
    while True:
        image = global_picam.capture_array()
        image = cv2.resize(image, (512, 512))
        image = cv2.rotate(image, cv2.ROTATE_180)
        processed_image = image.copy()
        
        if only_image:
            # Sărim peste procesarea cutiilor
            session_data = {}
        else:
            # Detectare cutii și procesare
            detections_letters = detect_letters(global_picam)
            detections_boxes = detect_objects(global_picam)
            
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
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        if key == ord('t'):
            only_image = not only_image
            print("Modul only_image este acum setat la:", only_image)
            
    cv2.destroyAllWindows()

def capture_raw_image():
    """
    Capturează o imagine de la cameră și aplică doar:
      - Redimensionare la 512x512.
      - (Opțional) Conversie de la BGR la RGB.
    Această funcție sare peste orice procesare suplimentară și returnează imaginea preprocesată.
    Returnează:
      - raw_image: imaginea capturată și preprocesată.
    """
    global global_picam
    if global_picam is None:
        raise Exception("Camera nu a fost inițializată. Apelează init_camera() înainte.")
    
    image = global_picam.capture_array()
    image = cv2.resize(image, (512, 512))
    return image

def camera_loop_raw(callback=None):
    """
    Rulează un loop continuu care capturează o imagine "raw" (preprocesată, redimensionată la 512x512) de la cameră,
    fără a trece prin procesările din BOX_DETECT.
    Dacă callback este definit, acesta va fi apelat pentru fiecare cadru cu parametrul:
      - raw_image: copia imaginii brute preprocesate.
    Dacă callback este None, se afișează imaginea într-o fereastră OpenCV.
    Apăsați 'q' pentru a ieși.
    """
    global global_picam
    if global_picam is None:
        raise Exception("Camera nu a fost inițializată. Apelează init_camera() înainte.")
    
    while True:
        image = global_picam.capture_array()
        image = cv2.resize(image, (512, 512))
        raw_image = image.copy()
        
        if callback:
            callback(raw_image)
        else:
            cv2.imshow("Raw Image", raw_image)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    cv2.destroyAllWindows()

if __name__ == "__main__":
    # Exemplu de utilizare:
    # 1. Inițializarea camerei
    init_camera()
    
    # 2. Rulare loop raw pentru debug
    camera_loop_raw()
    
    # 3. Oprirea camerei
    stop_camera()
