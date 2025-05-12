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

color_map = {
    "A": (0, 255, 0),
    "K": (255, 0, 255),
    "O": (255, 255, 255),
    "Green": (0, 255, 0),
    "Red": (0, 0, 255),
    "Sample": (255, 255, 255),
    "Blue": (255, 0, 0)
}

# ---------------------------------------------------------------------------
# Funcții locale de procesare
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

# ---------------------------------------------------------------------------
# Funcții de desenare pe cadru
# ---------------------------------------------------------------------------
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

# Noua funcție pentru a desena un pătrat alb, rotit conform orientării calculate
def draw_orientation_square(image, tracked_pkg, orientation_angle):
    x, y = tracked_pkg["position"]
    if tracked_pkg.get("size") is not None and None not in tracked_pkg.get("size"):
        w, h = tracked_pkg["size"]
    else:
        w, h = 50, 50  # dimensiune implicită
    # Creăm un dreptunghi rotit cu centrul la (x,y)
    rect = ((x, y), (w, h), orientation_angle)
    box = cv2.boxPoints(rect)
    box = np.int0(box)
    cv2.drawContours(image, [box], 0, (255, 255, 255), 2)

# ---------------------------------------------------------------------------
# Funcții de analiză a zonei de interes (ROI) a pachetului urmărit
# ---------------------------------------------------------------------------
def threshold_orientation(angle):
    """
    Cuantizează unghiul detectat la una din valorile discrete: 0, 20 sau 45 grade.
    Dacă nu există rotație semnificativă => 0; dacă este moderat => 20; altfel => 45.
    """
    if angle is None:
        return None
    a = abs(angle)
    if a < 10:
        return 0
    elif a < 30:
        return 20
    else:
        return 45

def process_color_orientation(roi):
    """
    Analizează culorile din colțurile superioare ale ROI (ignorând partea de jos,
    care poate induce în eroare) și returnează o orientare presupusă:
       - Diferență mică => 0°
       - Diferență moderată => 20°
       - Diferență mare => 45°
    """
    h, w = roi.shape[:2]
    corner_w, corner_h = int(w * 0.1), int(h * 0.1)
    # Extragem colțurile superioare stânga și dreapta
    tl = roi[0:corner_h, 0:corner_w]
    tr = roi[0:corner_h, w - corner_w:w]
    avg_tl = cv2.mean(tl)[:3]
    avg_tr = cv2.mean(tr)[:3]
    diff = math.sqrt(sum((a - b) ** 2 for a, b in zip(avg_tl, avg_tr)))
    # Praguri arbitrare pentru diferență
    if diff < 10:
        return 0
    elif diff < 30:
        return 20
    else:
        return 45



from collections import Counter




def analyze_tracked_box(image, tracked_pkg, margin=10, debug=False):
    """
    Detectează liniile din bounding box + margin și
    cuantizează fiecare unghi la una din valorile discrete: 0, 15, 25, 35 sau 45 grade.
    Unghiul final este calculat ca modulul (efectiv) în intervalul 0-45, indiferent de direcție.
    Se returnează un dicționar cu parametrii ROI și orientarea finală determinată ca fiind nivelul
    cel mai frecvent în rândul liniilor detectate.
    """
    x, y = tracked_pkg["position"]
    if tracked_pkg.get("size") is not None and None not in tracked_pkg.get("size"):
        w, h = tracked_pkg["size"]
    else:
        w, h = 50, 50  # fallback

    # 1. Definim ROI cu un mic margin (ex. 10px)
    roi_x1 = max(0, int(x - w/2 - margin))
    roi_y1 = max(0, int(y - h/2 - margin))
    roi_x2 = min(image.shape[1], int(x + w/2 + margin))
    roi_y2 = min(image.shape[0], int(y + h/2 + margin))
    
    roi = image[roi_y1:roi_y2, roi_x1:roi_x2]
    roi_h, roi_w = roi.shape[:2]

    # --- (A) Preprocesare imagine pentru detectare linii ---
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)

    # --- (B) Detectare linii cu Hough ---
    lines = cv2.HoughLinesP(edges, 1, math.pi/180, threshold=30,
                             minLineLength=roi_w//4, maxLineGap=10)

    # Pentru debug, opțional: desenează liniile detectate
    if debug:
        debug_lines = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)

    raw_angles = []
    quantized_angles = []
    
    def quantize_angle(a):
        """
        Calculează un unghi efectiv în [0,45]:
          - Se folosește: effective = min(|a|, 90 - |a|)
          - Apoi se cuantizează după pragurile:
                < 7.5   => 0°
                [7.5,20)  => 15°
                [20,27.5) => 25°
                [27.5,37.5) => 35°
                ≥ 37.5  => 45°
        """
        a = abs(a)
        # Obținem unghiul efectiv în intervalul 0-45
        if a > 45:
            a = 90 - a
        if a < 7.5:
            return 0
        elif a < 20:
            return 15
        elif a < 27.5:
            return 25
        elif a < 37.5:
            return 35
        else:
            return 45

    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle_deg = math.degrees(math.atan2(y2 - y1, x2 - x1))
            # Convertim în intervalul -90..90
            if angle_deg > 90:
                angle_deg -= 180
            elif angle_deg < -90:
                angle_deg += 180

            raw_angles.append(angle_deg)
            quantized = quantize_angle(angle_deg)
            quantized_angles.append(quantized)

            if debug:
                cv2.line(debug_lines, (x1, y1), (x2, y2), (0, 255, 0), 2)
    else:
        if debug:
            debug_lines = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)

    if debug:
        cv2.imshow("ROI Edges", edges)
        cv2.imshow("ROI Lines", debug_lines)
        # Desenăm chenarul ROI pe imaginea originală (pentru referință)
        cv2.rectangle(image, (roi_x1, roi_y1), (roi_x2, roi_y2), (255, 255, 0), 2)
        cv2.waitKey(1)

    # --- (C) Determinăm orientarea finală pe baza cuantizării ---
    if quantized_angles:
        from collections import Counter
        counter = Counter(quantized_angles)
        final_orientation = counter.most_common(1)[0][0]
    else:
        final_orientation = 0  # dacă nu s-au detectat linii, considerăm 0°

    parameters = {
        "roi_top_left": (roi_x1, roi_y1),
        "roi_bottom_right": (roi_x2, roi_y2),
        "roi_width": roi_w,
        "roi_height": roi_h,
        "orientation_angle": final_orientation,
        "lines_count": len(raw_angles),
        "raw_angles": raw_angles,
        "quantized_angles": quantized_angles,
    }

    return parameters





def print_tracked_box_parameters(image, tracked_pkg):
    params = analyze_tracked_box(image, tracked_pkg, margin=45, debug=True)
    print("=== Tracked Box Parameters ===")
    print(f"ROI Top Left: {params['roi_top_left']}")
    print(f"ROI Bottom Right: {params['roi_bottom_right']}")
    print(f"ROI Width: {params['roi_width']} px")
    print(f"ROI Height: {params['roi_height']} px")
    if params['orientation_angle'] is not None:
        print(f"Orientation Angle (quantizat): {params['orientation_angle']}°")
    else:
        print("Orientation Angle: Not detected")
    print("===============================")
    return params.get("orientation_angle")

# ---------------------------------------------------------------------------
# Funcția de desenare a referinței (linia centrală) – păstrată, dar complementată cu pătratul alb
# ---------------------------------------------------------------------------
def draw_reference_and_orientation(image, tracked_pkg, orientation_angle, ref_color=(0,255,255), orient_color=(0,0,255)):
    img_h, img_w = image.shape[:2]
    cv2.line(image, (zone_center[0], 0), (zone_center[0], img_h), ref_color, 2)
    # Desenăm linia de orientare (exemplu)
    center = tracked_pkg["position"]
    L = 100
    if orientation_angle is not None:
        rad = math.radians(orientation_angle)
        end_point = (int(center[0] + L * math.cos(rad)), int(center[1] + L * math.sin(rad)))
        cv2.line(image, center, end_point, orient_color, 2)
        diff_angle = orientation_angle - 90
        cv2.putText(image, f"Diff: {diff_angle:.1f} deg", (center[0]+10, center[1]+10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, orient_color, 2)
    # Desenăm pătratul alb rotit conform orientării calculate
    draw_orientation_square(image, tracked_pkg, orientation_angle)

# ---------------------------------------------------------------------------
# BUCLEA PRINCIPALĂ: Captură și procesare imagine
# ---------------------------------------------------------------------------
def camera_loop():
    global current_orientation, smoothed_orientation
    tracked_package = None  # Pachetul pe care îl urmărim
    
    while True:
        # 1. Capture și preprocesare imagine
        image = picam2.capture_array()
        image = cv2.resize(image, (512, 512))
        image = cv2.rotate(image, cv2.ROTATE_180)
        
        # 2. Fă o copie a imaginii, pe care să nu desenăm nimic
        original_image = image.copy()

        # 3. Detectare litere și cutii (presupunem că detect_letters și detect_objects sunt definite)
        detections_letters = detect_letters(picam2)
        detections_boxes   = detect_objects(picam2)

        # 4. Construcție session_data, pachet urmărit etc.
        matched_packages = assign_letters_to_packages(detections_letters, detections_boxes, threshold=5)
        box_distances    = calculate_box_distance(detections_boxes, zone_center, pass_threshold=20, max_distance=30)
        session_data     = build_session_data(matched_packages, box_distances, detections_boxes)
        session_data     = merge_similar_packages(session_data, merge_distance_threshold=MERGE_DISTANCE_THRESHOLD)
        
        if session_data:
            tracked_package = list(session_data.values())[0]
        
        # 5. Desenăm pe 'image' (nu pe 'original_image')
        draw_detections(image, detections_boxes, color_map)
        
        if tracked_package is not None:
            draw_tracked_package(image, tracked_package, color=(255, 255, 0))
            
            # !!! Folosim original_image (fără desene) pentru analiză !!!
            raw_orientation = print_tracked_box_parameters(original_image, tracked_package)
            
            if raw_orientation is not None:
                current_orientation = raw_orientation
                if smoothed_orientation is None:
                    smoothed_orientation = raw_orientation
                else:
                    smoothed_orientation = alpha * raw_orientation + (1 - alpha) * smoothed_orientation

            # Desenăm orientarea pe 'image'
            draw_reference_and_orientation(image, tracked_package, smoothed_orientation)

        mark_zone(image, zone_top_left, zone_bottom_right, label="Defined Zone")
        add_grid(image)
        
        # 6. Afișăm imaginea pe care am desenat
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

    # Definim colțurile inițiale ale pătratului (fără rotație)
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

def calibrate():
    global calibration_offset, current_orientation
    if current_orientation is not None:
        calibration_offset = current_orientation
        print(f"Calibration set to {calibration_offset:.2f} degrees")
    else:
        print("No orientation data to calibrate")

# Configurare fereastră Tkinter
root = tk.Tk()
root.title("Interfață Orientare Cutie")

canvas = tk.Canvas(root, width=300, height=300, bg="white")
canvas.pack()

calibrate_button = tk.Button(root, text="Calibrare", command=calibrate)
calibrate_button.pack()

root.after(100, update_canvas)

# Pornim bucla camerei într-un fir de execuție separat
camera_thread = threading.Thread(target=camera_loop, daemon=True)
camera_thread.start()

# Pornim interfața Tkinter
root.mainloop()
