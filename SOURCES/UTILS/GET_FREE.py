#!/usr/bin/env python3
"""
Module: zone_box_analyzer
Descriere: Acest modul importă funcționalitățile din UTILS.MAP și ZONE_DETECT.get_zone și implementează o funcție
          principală care, pe baza unei imagini (o copie a camerei), a unei sesiuni (neprocesate) și a unui număr maxim de cutii,
          analizează zona detectată, numără cutiile din interiorul acesteia și, dacă nu este FULL, caută o poziție liberă
          (respectând regulile de proximitate și siguranță).
          
          Pentru debug se desenează o interfață Tkinter în care se vizualizează limita zonei, cutiile existente și eventual
          poziția candidat găsită.
"""

import tkinter as tk
import random
import math

# Importăm funcțiile din UTILS.MAP
from .MAP import process_boxes, classify_box_relative

import os
import sys
# Adaugă directorul părinte la sys.path pentru a putea importa modulele din BOX_DETECT și UTILS
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)
    


# Importăm funcția de detectare a zonei din ZONE_DETECT.get_zone
from ZONE_DETECT.get_zone import detect_zone

# Funcție helper: verifică dacă o poziție candidat (ca virtual box 3x3 cm) este liberă față de toate cutiile existente.
def is_position_free(candidate_box, boxes):
    """
    Verifică dacă poziția candidat este "Safe" relativ la toate cutiile din boxes.
    candidate_box: dict cu "real_position", "real_size" (3x3) și "angle" (0)
    boxes: dicționar de cutii procesate.
    Returnează True dacă, pentru fiecare box, clasificarea (în ambele sensuri) este "Safe".
    """
    for box in boxes.values():
        # Se verifică în ambele direcții
        if classify_box_relative(candidate_box, box) != "Safe" or classify_box_relative(box, candidate_box) != "Safe":
            return False
    return True


def find_free_position(boxes, zone_limits, max_attempts=1000):
    import math, random
    
    # Calculăm centrul zonei
    center_x = (zone_limits["left"] + zone_limits["right"]) / 2
    center_y = (zone_limits["top"] + zone_limits["bottom"]) / 2

    candidate_points = []
    
    # 1. Adaugă centrul zonei
    candidate_points.append((center_x, center_y))
    
    # 2. Adaugă puncte la x-7 și x+7 (dacă se încadrează în zone)
    x_offsets = [-7, 7]
    for x_off in x_offsets:
        candidate_x = center_x + x_off
        if zone_limits["left"] <= candidate_x <= zone_limits["right"]:
            candidate_points.append((candidate_x, center_y))
    
    # 3. Ajustări pe axa y (de exemplu, -0.5 și -1) cu aceleași x ca la centru
    y_offsets = [-0.5, -1]
    for y_off in y_offsets:
        candidate_y = center_y + y_off
        if zone_limits["bottom"] <= candidate_y <= zone_limits["top"]:
            candidate_points.append((center_x, candidate_y))
    
    # 4. Poți combina offset-uri pe ambele axe pentru a acoperi mai multe cazuri:
    for x_off in x_offsets:
        for y_off in y_offsets:
            candidate_x = center_x + x_off
            candidate_y = center_y + y_off
            if (zone_limits["left"] <= candidate_x <= zone_limits["right"] and
                zone_limits["bottom"] <= candidate_y <= zone_limits["top"]):
                candidate_points.append((candidate_x, candidate_y))
    
    # 5. Verificăm candidații predefiniți
    for candidate in candidate_points:
        candidate_box = {"real_position": candidate, "real_size": (3, 3), "angle": 0}
        if is_position_free(candidate_box, boxes):
            return candidate

    # 6. Dacă niciunul nu a funcționat, căutare aleatorie
    for _ in range(max_attempts):
        candidate_x = random.uniform(zone_limits["left"] + 2, zone_limits["right"] - 2)
        candidate_y = random.uniform(zone_limits["bottom"] + 2, zone_limits["top"] - 2)
        candidate = (candidate_x, candidate_y)
        candidate_box = {"real_position": candidate, "real_size": (3, 3), "angle": 0}
        if is_position_free(candidate_box, boxes):
            return candidate
    return None




def analyze_zone_and_find_spot(image_copy, session, max_boxes, debug=False):
    """
    Funcția principală.
    
    Parametri:
      - image_copy: o copie a imaginii (de la cameră, 512x512) folosită pentru detect_area.
      - session: dicționarul de sesiune (formatul așteptat de process_boxes din MAP).
      - max_boxes: numărul maxim de cutii permis în interiorul zonei.
      - debug: flag (bool); dacă True se deschide o interfață Tkinter pentru debug.
      
    Pași:
      1. Se procesează sesiunea cu process_boxes.
      2. Se extrag pozițiile (în cm) din cutiile procesate.
      3. Se apelează detect_zone cu aceste poziții (debug=False) pentru a obține limitele zonei și o listă de flaguri.
      4. Se numără cutiile din interiorul zonei.
         - Dacă count >= max_boxes → return "FULL"
         - Altfel, se caută o poziție liberă (virtual box de 3x3 cm) în interiorul zonei.
      5. Dacă se găsește o poziție liberă, se returnează coordonatele (x, y) în cm.
      
    Pentru debug, se desenează interfața cu limita zonei, cutiile și (dacă există) poziția candidat.
    """
    # 1. Procesează sesiunea
    processed_boxes = process_boxes(session)
    
    # 2. Extrage pozițiile din cutiile procesate
    positions = [box["real_position"] for box in processed_boxes.values()]
    
    # 3. Folosește detect_zone pentru a obține zona (cu debug=False)
    zone_limits, pos_flags = detect_zone(image_copy, positions=positions, debug=False)
    
    # 4. Numără cutiile din interiorul zonei
    count_in_zone = sum(pos_flags)
    if debug:
        print("Limitele zonei:", zone_limits)
        print("Flaguri poziții:", pos_flags)
        print("Număr cutii în zonă:", count_in_zone)
    
    if count_in_zone >= max_boxes:
        if debug:
            print("Zona este FULL.")
            debug_interface(processed_boxes, zone_limits, candidate_spot=None)
        return "FULL"
    
    # 5. Caută o poziție liberă
    free_spot = find_free_position(processed_boxes, zone_limits)
    if debug:
        if free_spot:
            print("Poziție liberă găsită:", free_spot)
        else:
            print("Nu s-a găsit poziție liberă.")
        debug_interface(processed_boxes, zone_limits, candidate_spot=free_spot)
    
    if free_spot is not None:
        return free_spot
    else:
        return "FULL"

def debug_interface(boxes, zone_limits, candidate_spot=None):
    """
    Desenează o interfață Tkinter pentru debug:
      - Grid și coordonate (de la -25 la 25 pe X și de la -10 la 30 pe Y).
      - Limitele zonei (obținute din detect_zone) sunt desenate ca un dreptunghi.
      - Se desenează cutiile din sesiune (cu culoare și litera lor).
      - Dacă există, se desenează și candidate_spot ca un oval magenta.
    """
    # Setăm coordonatele de bază
    min_x, max_x = -25, 25
    min_y, max_y = -10, 30
    scale = 10  # 10 pixeli per cm
    canvas_width = int((max_x - min_x) * scale)
    canvas_height = int((max_y - min_y) * scale)
    
    root = tk.Tk()
    root.title("Debug - Zona și Cutiile")
    canvas = tk.Canvas(root, width=canvas_width, height=canvas_height, bg="white")
    canvas.pack()
    
    def real_to_canvas(x, y):
        cx = (x - min_x) * scale
        cy = (max_y - y) * scale
        return cx, cy
    
    # Desenăm grid (opțional)
    for x in range(min_x, max_x+1):
        cx, _ = real_to_canvas(x, min_y)
        canvas.create_line(cx, 0, cx, canvas_height, fill="#e0e0e0")
    for y in range(min_y, max_y+1):
        _, cy = real_to_canvas(min_x, y)
        canvas.create_line(0, cy, canvas_width, cy, fill="#e0e0e0")
    
    # Desenăm limita zonei detectate
    zx_left = zone_limits["left"]
    zx_right = zone_limits["right"]
    zy_top = zone_limits["top"]
    zy_bottom = zone_limits["bottom"]
    p1 = real_to_canvas(zx_left, zy_top)
    p2 = real_to_canvas(zx_right, zy_bottom)
    canvas.create_rectangle(p1[0], p1[1], p2[0], p2[1], outline="blue", width=2)
    
    # Desenăm cutiile procesate
    for box in boxes.values():
        x, y = box["real_position"]
        size = 3  # dimensiune standard: 3x3 cm
        half = size / 2
        cx, cy = real_to_canvas(x, y)
        left = cx - half * scale
        right = cx + half * scale
        top = cy - half * scale
        bottom = cy + half * scale
        canvas.create_rectangle(left, top, right, bottom, fill=box["color"], outline="black", width=2)
        canvas.create_text(cx, cy, text=box["letter"], fill="white", font=("Arial", 12))
    
    # Desenăm candidate_spot dacă există
    if candidate_spot is not None:
        x, y = candidate_spot
        size = 3
        half = size / 2
        cx, cy = real_to_canvas(x, y)
        canvas.create_oval(cx - half*scale, cy - half*scale, cx + half*scale, cy + half*scale,
                           outline="magenta", width=3)
    
    root.mainloop()

# Exemplu de rulare standalone
if __name__ == "__main__":
    # Exemplu de sesiune (similar cu cel din MAP.py)
    session_example = {
        "K": {
            "position": (250, 150),
            "size": (20, 20),
            "box_color": "blue",
            "letters": "K",
            "angle": 0
        },
        "A": {
            "position": (300, 200),
            "size": (30, 30),
            "box_color": "red",
            "letters": "A",
            "angle": 0
        }
    }
    
    # Creăm o imagine dummy (512x512) folosind Pillow
    from PIL import Image
    image_copy_dummy = Image.new("RGB", (512, 512), color="white")
    
    max_boxes_allowed = 3
    
    result = analyze_zone_and_find_spot(image_copy_dummy, session_example, max_boxes_allowed, debug=True)
    print("Rezultat:", result)
