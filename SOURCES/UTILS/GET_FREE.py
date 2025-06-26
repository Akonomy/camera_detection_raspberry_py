#!/usr/bin/env python3
"""
Module: zone_box_analyzer
Descriere: Acest modul importă funcționalitățile din UTILS.MAP și ZONE_DETECT.get_zone și implementează o funcție
          principală care, pe baza unei imagini (o copie a camerei), a unei sesiuni (neprocesate) și a unui număr maxim de cutii,
          analizează zona detectată, numără cutiile din interiorul acesteia și, dacă nu este FULL, caută o poziție liberă
          (respectând regulile de proximitate și siguranță).
          
          Pentru debug se desenează o interfață Tkinter în care se vizualizează conturul zonei (poligonul convex),
          cutiile existente și eventual poziția candidat găsită.
"""

import tkinter as tk
import random
import math

# Importăm funcțiile din UTILS.MAP
from .MAP import process_boxes, classify_box_relative,  analyze_virtual_box

import os
import sys
# Adaugă directorul părinte la sys.path pentru a putea importa modulele din BOX_DETECT și UTILS
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)
    
# Importăm funcția de detectare a zonei din ZONE_DETECT.get_zone
# Această versiune modificată de detect_zone returnează acum și poligonul (lista de puncte hull)
from ZONE_DETECT.get_zone import detect_zone


def is_position_free(candidate_box, boxes, ignore_box_id=None):
    """
    Verifică dacă poziția candidat este "Safe" relativ la toate cutiile din boxes.
    candidate_box: dict cu "real_position", "real_size" (ex: (3,3)) și "angle" (ex: 0)
    ignore_box_id: dacă este specificat, cutia cu acest id este ignorată la verificare.
    
    Returnează True dacă, pentru fiecare box (cu excepția celei din ignore_box_id):
      - Poziția candidatului nu coincide exact cu poziția box-ului.
      - Poziția candidatului nu este în interiorul unei zone de ±3 cm în ambele direcții față de poziția box-ului.
      - Clasificarea (în ambele direcții) este "Safe".
    """
    candidate_pos = candidate_box["real_position"]
    candidate_x, candidate_y = candidate_pos
    for bid, box in boxes.items():
        if ignore_box_id is not None and bid == ignore_box_id:
            continue
        box_x, box_y = box["real_position"]
        # Verifică dacă poziția candidatului este exact aceeași cu poziția box-ului existent
        if candidate_pos == box["real_position"]:
            return False
        # Verifică dacă diferența pe ambele axe este mai mică de 3 cm
        if abs(candidate_x - box_x) < 3 and abs(candidate_y - box_y) < 3:
            return False
        # Verifică suprapunerea conform funcției de clasificare (în ambele direcții)
        if classify_box_relative(box, candidate_box) != "Safe" or classify_box_relative(candidate_box, box) != "Safe":
            return False
    return True



def find_free_position(boxes, zone_limits, max_boxes_allowed, 
                       min_spacing_x=7, min_spacing_y=6, 
                       min_boundary=3, 
                       grid_min_spacing_x=6, grid_min_spacing_y=5,
                       max_attempts=1000, ignore_box_id=None):
    """
    Algoritm extins pentru determinarea poziției libere (ca și înainte),
    dar care acum colectează în lista free_candidates toate pozițiile candidate
    care au fost verificate ca fiind "free".
    
    La final se întoarce un tuple: (candidate_position, free_candidates, error_details)
    unde candidate_position este poziția finală (sau None),
    free_candidates este lista tuturor pozițiilor libere verificate (pentru debug),
    iar error_details este None dacă s-a găsit cel puțin una.
    """
    error_details = []
    free_candidates = []
    
    # Calculăm dimensiunile zonei
    zone_width = zone_limits["right"] - zone_limits["left"]
    zone_height = zone_limits["top"] - zone_limits["bottom"]
    
    # Filtrăm cutiile care se află în zona (după coordonate)
    def in_zone(pos):
        x, y = pos
        return (zone_limits["left"] <= x <= zone_limits["right"] and
                zone_limits["bottom"] <= y <= zone_limits["top"])
    boxes_in_zone = {bid: box for bid, box in boxes.items() if in_zone(box["real_position"])}
    
    candidate_positions = []
    
    if boxes_in_zone:
        # --- Cazul în care există cutii în zonă ---
        y_values = [box["real_position"][1] for box in boxes_in_zone.values()]
        clusters = {}
        for y in y_values:
            key = round(y)  # grupare pe unitate
            clusters.setdefault(key, []).append(y)
        predominant_key = max(clusters, key=lambda k: len(clusters[k]))
        avg_y = sum(clusters[predominant_key]) / len(clusters[predominant_key])
        
        x_start = zone_limits["left"] + min_boundary
        x_end = zone_limits["right"] - min_boundary
        num_candidates = int(math.floor((x_end - x_start) / min_spacing_x)) + 1
        for i in range(num_candidates):
            candidate_x = x_start + i * min_spacing_x
            candidate_positions.append((candidate_x, avg_y))
    else:
        # --- Cazul în care nu există cutii în zonă ---
        spacing_x = min_spacing_x
        spacing_y = min_spacing_y
        x_start = zone_limits["left"] + min_boundary
        x_end = zone_limits["right"] - min_boundary
        y_start = zone_limits["bottom"] + min_boundary
        y_end = zone_limits["top"] - min_boundary
        
        def grid_positions(sp_x, sp_y):
            xs = []
            pos = x_start
            while pos <= x_end:
                xs.append(pos)
                pos += sp_x
            ys = []
            pos = y_end  # pornim de sus
            while pos >= y_start:
                ys.append(pos)
                pos -= sp_y
            grid = []
            for y in ys:
                for x in xs:
                    grid.append((x, y))
            return grid
        
        grid_candidates = grid_positions(spacing_x, spacing_y)
        if len(grid_candidates) > max_boxes_allowed + 3:
            factor = 1 + (len(grid_candidates) - (max_boxes_allowed + 3)) / len(grid_candidates)
            spacing_x = min(spacing_x * factor, spacing_x * 2)
            spacing_y = min(spacing_y * factor, spacing_y * 2)
            grid_candidates = grid_positions(spacing_x, spacing_y)
        candidate_positions.extend(grid_candidates)
    
    candidate_positions.sort(key=lambda pos: (-pos[1], pos[0]))
    
    # Verificăm candidații predefiniți
    chosen_candidate = None
    for candidate in candidate_positions:
        candidate_box = {"real_position": candidate, "real_size": (3, 3), "angle": 0}
        if is_position_free(candidate_box, boxes, ignore_box_id=ignore_box_id):
            free_candidates.append(candidate)
            # Prima poziție free din listă o considerăm candidate
            if chosen_candidate is None:
                chosen_candidate = candidate
    if chosen_candidate is not None:
        return chosen_candidate, free_candidates, None
    error_details.append("Candidații predefiniți nu au fost liberi.")
    
    # Dacă nu am găsit în sondajul structurat, căutare aleatorie
    for _ in range(max_attempts):
        candidate_x = random.uniform(zone_limits["left"] + min_boundary, zone_limits["right"] - min_boundary)
        candidate_y = random.uniform(zone_limits["bottom"] + min_boundary, zone_limits["top"] - min_boundary)
        candidate = (candidate_x, candidate_y)
        candidate_box = {"real_position": candidate, "real_size": (3, 3), "angle": 0}
        if is_position_free(candidate_box, boxes, ignore_box_id=ignore_box_id):
            free_candidates.append(candidate)
            return candidate, free_candidates, None
    error_details.append(f"Căutarea aleatorie (max_attempts={max_attempts}) nu a găsit un loc liber.")
    return None, free_candidates, error_details


def analyze_zone_and_find_spot(image_copy, session, max_boxes, ignore_box_id, debug=False):


    print(session)
    processed_boxes = process_boxes(session)
    print(processed_boxes)
    positions = [box["real_position"] for box in processed_boxes.values()]
    zone_limits, pos_flags, hull = detect_zone(image_copy, positions=positions, debug=False)
    count_in_zone = sum(pos_flags)
    if debug:
        print("Limitele zonei:", zone_limits)
        print("Flaguri poziții:", pos_flags)
        print("Număr cutii în zonă:", count_in_zone)
    
    if count_in_zone >= max_boxes:
        if debug:
            print("Zona este FULL.")
            debug_interface(processed_boxes, zone_limits, hull, candidate_spot=None, free_candidates=[])
        return "FULL"
    
    free_spot, free_candidates, errors = find_free_position(processed_boxes, zone_limits, max_boxes, ignore_box_id=ignore_box_id)
    if debug:
        if free_spot:
            print("Poziție liberă găsită:", free_spot)
        else:
            print("Nu s-a găsit poziție liberă.")
            if errors:
                print("Detalii eroare:")
                for msg in errors:
                    print(" -", msg)
        debug_interface(processed_boxes, zone_limits, hull, candidate_spot=free_spot, free_candidates=free_candidates)
    
    if free_spot is not None:
        return free_spot
    else:
        error_msg = "NU AVEM LOC. Detalii eroare: " + " | ".join(errors) if errors else "NU AVEM LOC."
        return error_msg


def debug_interface(boxes, zone_limits, hull, candidate_spot=None, free_candidates=None):
    """
    Funcție de debug care desenează:
      - Gridul cu coordonate,
      - Poligonul convex (sau dreptunghiul zonei),
      - Toate cutiile existente,
      - Toate pozițiile free verificate (free_candidates) cu marcaj verde,
      - Poziția finală (candidate_spot) cu marcaj magenta.
    """
    def real_to_canvas(x, y):
        cx = (x - min_x) * scale
        cy = (max_y - y) * scale
        return cx, cy

    def point_in_poly(x, y, poly):
        inside = False
        n = len(poly)
        if n == 0:
            return False
        p1x, p1y = poly[0]
        for i in range(1, n+1):
            p2x, p2y = poly[i % n]
            if min(p1y, p2y) < y <= max(p1y, p2y):
                if p1y != p2y:
                    xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                else:
                    xinters = p1x
                if x <= xinters:
                    inside = not inside
            p1x, p1y = p2x, p2y
        return inside

    min_x, max_x = -25, 25
    min_y, max_y = -10, 30
    scale = 10
    canvas_width = int((max_x - min_x) * scale)
    canvas_height = int((max_y - min_y) * scale)
    
    root = tk.Tk()
    root.title("Debug - Zona și Cutiile")
    canvas = tk.Canvas(root, width=canvas_width, height=canvas_height, bg="white")
    canvas.pack()
    
    for x in range(min_x, max_x+1):
        cx, _ = real_to_canvas(x, min_y)
        canvas.create_line(cx, 0, cx, canvas_height, fill="#e0e0e0")
    for y in range(min_y, max_y+1):
        _, cy = real_to_canvas(min_x, y)
        canvas.create_line(0, cy, canvas_width, cy, fill="#e0e0e0")
    
    if 0 >= min_x and 0 <= max_x:
        cx, _ = real_to_canvas(0, min_y)
        canvas.create_line(cx, 0, cx, canvas_height, fill="gray", width=2)
    if 0 >= min_y and 0 <= max_y:
        _, cy = real_to_canvas(min_x, 0)
        canvas.create_line(0, cy, canvas_width, cy, fill="gray", width=2)
    
    tick_length = 5
    for x in range(min_x, max_x+1):
        cx, _ = real_to_canvas(x, min_y)
        canvas.create_line(cx, canvas_height, cx, canvas_height - tick_length, fill="black")
        if x % 5 == 0:
            canvas.create_text(cx, canvas_height - tick_length - 10, text=str(x), fill="black", font=("Arial", 10))
    for y in range(min_y, max_y+1):
        cx, cy = real_to_canvas(min_x, y)
        canvas.create_line(0, cy, tick_length, cy, fill="black")
        if y % 5 == 0:
            canvas.create_text(tick_length + 15, cy, text=str(y), fill="black", font=("Arial", 10))
    
    if hull and len(hull) >= 3:
        hull_canvas_coords = [real_to_canvas(x, y) for x, y in hull]
        for i in range(len(hull_canvas_coords)):
            x1, y1 = hull_canvas_coords[i]
            x2, y2 = hull_canvas_coords[(i + 1) % len(hull_canvas_coords)]
            canvas.create_line(x1, y1, x2, y2, fill="blue", width=2)
    else:
        zx_left = zone_limits["left"]
        zx_right = zone_limits["right"]
        zy_top = zone_limits["top"]
        zy_bottom = zone_limits["bottom"]
        p1 = real_to_canvas(zx_left, zy_top)
        p2 = real_to_canvas(zx_right, zy_bottom)
        canvas.create_rectangle(p1[0], p1[1], p2[0], p2[1], outline="blue", width=2)
    
    for box in boxes.values():
        x, y = box["real_position"]
        size = 3
        half = size / 2
        cx, cy = real_to_canvas(x, y)
        left = cx - half * scale
        right = cx + half * scale
        top = cy - half * scale
        bottom = cy + half * scale
        canvas.create_rectangle(left, top, right, bottom, fill=box["color"], outline="black", width=2)
        canvas.create_text(cx, cy, text=box["letter"], fill="white", font=("Arial", 12))
    
    # Desenăm toate pozițiile free verificate cu verde
    if free_candidates:
        for pos in free_candidates:
            cx, cy = real_to_canvas(pos[0], pos[1])
            radius = 5  # 5 pixeli
            canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius,
                               outline="green", width=2)
    
    # Desenăm poziția returnată cu magenta
    if candidate_spot is not None:
        x, y = candidate_spot
        size = 3
        half = size / 2
        cx, cy = real_to_canvas(x, y)
        canvas.create_oval(cx - half*scale, cy - half*scale, cx + half*scale, cy + half*scale,
                           outline="magenta", width=3)
    
    def on_click(event):
        real_x = event.x / scale + min_x
        real_y = max_y - event.y / scale
        inside = False
        if hull and len(hull) >= 3:
            inside = point_in_poly(real_x, real_y, hull)
        else:
            if (zone_limits["left"] <= real_x <= zone_limits["right"] and
                zone_limits["bottom"] <= real_y <= zone_limits["top"]):
                inside = True
        
        size = 5
        fill_color = "magenta" if inside else "yellow"
        canvas.create_rectangle(event.x - size/2, event.y - size/2,
                                event.x + size/2, event.y + size/2,
                                fill=fill_color, outline=fill_color)
        print(f"Click la (real): ({real_x:.2f}, {real_y:.2f}) - {'inside' if inside else 'outside'}")
    
    canvas.bind("<Button-1>", on_click)
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
