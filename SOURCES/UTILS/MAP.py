#!/usr/bin/env python3
"""
Module: box_map_interface
Descriere: Primește un dicționar cu informații despre cutii (culoare, literă, poziție, dimensiune, etc.),
           convertește coordonatele detectate (pixeli) în coordonate reale (cm) folosind funcțiile de
           conversie și desenează o interfață Tkinter fixă cu un grid (de la -25 la 25 pe axa X și -10 la 30 pe axa Y).
           Pe hartă se afișează etichete cu coordonate (ex. -25 cm, -24 cm, …, 25 cm pe X și -10, -9, …, 30 cm pe Y).
           Se permite click pe hartă pentru afișarea coordonatelor reale și, după selectarea unei cutii,
           se pot vizualiza zonele relative desenate ca dreptunghiuri filled cu transparență.
           
           Zonele existente sunt:
             - Danger: cu două subzone (Danger A și Danger B)
             - Warning: zone laterale
             - Safe: zona centrală plus zone laterale complete
             
           Noua funcționalitate este introducerea zonei **proximity**, definită astfel:
             - Proximity zone (culoare: purple): 
                 • pe verticală de la [by - 1.5, by + 2]
                 • pe orizontală: de la [bx - 3, bx - 1.5] (zona stângă) și [bx + 1.5, bx + 3] (zona dreaptă)
           Logica de clasificare devine:
             1. Dacă o cutie intersectează zona Danger (≥0.5 cm suprapunere verticală) → "Danger"
             2. Altfel, dacă are marginea în zona proximity → "Proximity"
             3. Altfel, dacă are suprapunere cu zona Warning (≥1 cm) → "Warning"
             4. În caz contrar → "Safe" (și nu este afișată la "Show Zones")
           
           Se introduce și funcția analyze_session_boxes care, pe baza unui target (dacă nu se furnizează se alege automat),
           returnează o listă de ID-uri (sortată crescător după diferența verticală față de target) și trei flaguri:
             - "target_in_first": 1 dacă primul element din listă este targetul solicitat,
             - "danger_neighbor_count": numărul de vecini clasificați ca Danger,
             - "target_specified_in_session": 1 dacă targetul a fost furnizat și găsit, 0 altfel.
"""

import tkinter as tk
import random
import math

# --- Funcții de conversie ---
def round_to_half(value):
    """Rotunjește valoarea la cel mai apropiat 0.5 cm."""
    return round(value * 2) / 2

def get_real_y(detected_y):
    return 0.05587 * detected_y - 4.47

def get_center_x(detected_y):
	
    return 0.0203 * detected_y + 230.38

def get_scale_x(detected_y):
    return 0.0000608 * detected_y + 0.046936
    
    
def get_effective_margin(box):
    """
    Pentru o cutie cu dimensiuni reale (w, h) și un unghi de rotație (angle, în grade),
    dacă abs(angle) > 15, se consideră că marginea efectivă este distanța de la centru la colț,
    adică sqrt((w/2)**2 + (h/2)**2). Altfel se folosește distanța minimă (min(w, h)/2).
    """
    w, h = box.get("real_size", (3, 3))  # presupunem implicit 3 cm dacă nu e specificat
    if abs(box.get("angle", 0)) > 25:
        return math.sqrt((w/2)**2 + (h/2)**2)
    else:
        return min(w, h) / 2
        


def getRealCoordinates(detected_x, detected_y):


    # Dimensiunile imaginii
    width, height = 512, 512
    
    # Conversia coordonatelor pentru rotația de 180°:
    # Noua coordonată x este (width - 1) - detected_x
    # Noua coordonată y este (height - 1) - detected_y
    rotated_x = (width - 1) - detected_x
    rotated_y = (height - 1) - detected_y

    # Folosim coordonatele rotite pentru a calcula coordonatele reale
    center_x = get_center_x(rotated_y)
    scale_x = get_scale_x(rotated_y)
    
    # Calculul real_x: diferența de la centru, scalată
    real_x = (rotated_x - center_x) * scale_x  
    
    # Calculul real_y, se presupune că get_real_y primește valoarea rotită a lui y
    real_y = get_real_y(rotated_y)
    
    # Rotunjire la cel mai apropiat 0.5
    real_x = round_to_half(real_x)
    real_y = round_to_half(real_y)
    
    return real_x, real_y



# Factor pentru mărime: 10 pixeli = 1 cm
PIXELS_PER_CM = 10

def process_boxes(session_dict):
    """
    Primește un dicționar de sesiune și returnează un dicționar cu datele procesate,
    convertind coordonatele și dimensiunile din pixeli în cm (rotunjite la 0.5 cm).
    Dacă culoarea este "sample", se folosește "beige".
    """
    processed_boxes = {}
    for box_id, box in session_dict.items():
        detected_x, detected_y = box["position"]
        real_x, real_y = getRealCoordinates(detected_x, detected_y)
        if box.get("size"):
            width_px, height_px = box["size"]
            width_cm = round_to_half(width_px / PIXELS_PER_CM)
            height_cm = round_to_half(height_px / PIXELS_PER_CM)
        else:
            width_cm, height_cm = 2, 2
        col = box["box_color"].lower()
        if col == "sample":
            col = "beige"
        processed_boxes[box_id] = {
            "color": col,
            "letter": box["letters"][0] if box.get("letters") else "",
            "real_position": (real_x, real_y),
            "real_size": (width_cm, height_cm),
            "angle": box["angle"]
        }
    return processed_boxes

def get_box_draw_size(box, default_min=2, default_max=3, scale=10):
    """
    Calculează dimensiunea de desen (în pixeli) a unei cutii,
    pe baza dimensiunii medii (în cm) clamped între default_min și default_max.
    """
    w_cm, h_cm = box.get("real_size", (default_min, default_min))
    avg_cm = (w_cm + h_cm) / 2
    clamped_cm = max(default_min, min(avg_cm, default_max))
    return int(clamped_cm * scale)





# --- Funcții de desenare și interfață Tkinter ---
class BoxMapApp:
    def __init__(self, boxes):
        self.boxes = boxes  # Dicționarul cu cutii procesate
        self.selected_box_id = None
        self.nearby_box_ids = []

        # Setăm sistemul de coordonate fix:
        self.min_x = -25
        self.max_x = 25
        self.min_y = -10
        self.max_y = 30

        self.scale = 10  # 10 pixeli per cm
        self.canvas_width = int((self.max_x - self.min_x) * self.scale)
        self.canvas_height = int((self.max_y - self.min_y) * self.scale)

        self.root = tk.Tk()
        self.root.title("Box Map Interface")

        self.canvas = tk.Canvas(self.root, width=self.canvas_width, height=self.canvas_height, bg="white")
        self.canvas.grid(row=0, column=0, columnspan=4)

        # Desenăm gridul și axele
        self.draw_grid()
        self.draw_axes()

        # Bind pentru click pe canvas
        self.canvas.bind("<Button-1>", self.on_canvas_click)

        # Widget-uri pentru threshold (opțional)
        tk.Label(self.root, text="dx_min (cm):").grid(row=1, column=0)
        self.dx_min_entry = tk.Entry(self.root)
        self.dx_min_entry.insert(0, "-5")
        self.dx_min_entry.grid(row=1, column=1)
        tk.Label(self.root, text="dx_max (cm):").grid(row=1, column=2)
        self.dx_max_entry = tk.Entry(self.root)
        self.dx_max_entry.insert(0, "5")
        self.dx_max_entry.grid(row=1, column=3)
        tk.Label(self.root, text="dy_min (cm):").grid(row=2, column=0)
        self.dy_min_entry = tk.Entry(self.root)
        self.dy_min_entry.insert(0, "-5")
        self.dy_min_entry.grid(row=2, column=1)
        tk.Label(self.root, text="dy_max (cm):").grid(row=2, column=2)
        self.dy_max_entry = tk.Entry(self.root)
        self.dy_max_entry.insert(0, "5")
        self.dy_max_entry.grid(row=2, column=3)

        # Butoane
        self.select_button = tk.Button(self.root, text="Select Random Box", command=self.select_random_box)
        self.select_button.grid(row=3, column=0, columnspan=2)
        self.find_nearby_button = tk.Button(self.root, text="Find Nearby Boxes", command=self.find_nearby_boxes)
        self.find_nearby_button.grid(row=3, column=2, columnspan=2)
        self.zone_button = tk.Button(self.root, text="Show Zones", command=self.draw_zones)
        self.zone_button.grid(row=4, column=0, columnspan=4)

        self.draw_map()

    def real_to_canvas(self, x, y):
        """Transformă coordonatele reale (cm) în coordonate de canvas (pixeli)."""
        canvas_x = (x - self.min_x) * self.scale
        canvas_y = (self.max_y - y) * self.scale
        return canvas_x, canvas_y

    def canvas_to_real(self, cx, cy):
        """Inversul funcției real_to_canvas."""
        x = cx / self.scale + self.min_x
        y = self.max_y - (cy / self.scale)
        return x, y

    def draw_grid(self):
        """Desenează gridul cu pas de 1 cm."""
        grid_step = 1
        x = self.min_x
        while x <= self.max_x:
            cx, _ = self.real_to_canvas(x, self.min_y)
            self.canvas.create_line(cx, 0, cx, self.canvas_height, fill="#cccccc")
            x += grid_step
        y = self.min_y
        while y <= self.max_y:
            _, cy = self.real_to_canvas(self.min_x, y)
            self.canvas.create_line(0, cy, self.canvas_width, cy, fill="#cccccc")
            y += grid_step

    def draw_axes(self):
        """Desenează axele cu etichete la fiecare 5 cm."""
        x0, y0 = self.real_to_canvas(self.min_x, 0)
        x1, y1 = self.real_to_canvas(self.max_x, 0)
        self.canvas.create_line(x0, y0, x1, y1, fill="black", width=2)
        for x in range(self.min_x, self.max_x+1, 5):
            cx, cy = self.real_to_canvas(x, 0)
            self.canvas.create_line(cx, cy-5, cx, cy+5, fill="black")
            self.canvas.create_text(cx, cy+15, text=f"{x} cm", font=("Arial", 8))
        x0, y0 = self.real_to_canvas(0, self.min_y)
        x1, y1 = self.real_to_canvas(0, self.max_y)
        self.canvas.create_line(x0, y0, x1, y1, fill="black", width=2)
        for y in range(self.min_y, self.max_y+1, 5):
            cx, cy = self.real_to_canvas(0, y)
            self.canvas.create_line(cx-5, cy, cx+5, cy, fill="black")
            self.canvas.create_text(cx-20, cy, text=f"{y} cm", font=("Arial", 8))

    def draw_map(self):
        self.canvas.delete("all")
        self.draw_grid()
        self.draw_axes()
        for box_id, box in self.boxes.items():
            x, y = box["real_position"]
            size_px = get_box_draw_size(box, scale=self.scale)
            half_px = size_px / 2
            cx, cy = self.real_to_canvas(x, y)
            left_c = cx - half_px
            top_c = cy - half_px
            right_c = cx + half_px
            bottom_c = cy + half_px
            fill_color = box["color"]
            self.canvas.create_rectangle(left_c, top_c, right_c, bottom_c,
                                         fill=fill_color, outline="black", width=2, tags=box_id)
            self.canvas.create_text(cx, cy, text=box["letter"], fill="white", font=("Arial", 12))
        if self.selected_box_id:
            sel_box = self.boxes[self.selected_box_id]
            bx, by = sel_box["real_position"]
            cx, cy = self.real_to_canvas(bx, by)
            size_px = get_box_draw_size(sel_box, scale=self.scale)
            half_px = size_px / 2
            self.canvas.create_rectangle(cx - half_px - 3, cy - half_px - 3,
                                         cx + half_px + 3, cy + half_px + 3,
                                         outline="blue", width=3, dash=(4,2), tags="selected")
        # Desenăm opțional indicatori pentru cutiile din nearby
        for nb in self.nearby_box_ids:
            if nb in self.boxes:
                bx, by = self.boxes[nb]["real_position"]
                cx, cy = self.real_to_canvas(bx, by)
                self.canvas.create_oval(cx-5, cy-5, cx+5, cy+5, outline="magenta", width=2)

    def update_map(self, new_boxes):
        self.boxes = new_boxes
        self.draw_map()

    def select_random_box(self):
        try:
            self.selected_box_id = random.choice(list(self.boxes.keys()))
            self.nearby_box_ids = []
            print("Selected box:", self.selected_box_id, self.boxes[self.selected_box_id])
            self.draw_map()
        except IndexError:
            print("No boxes available to select!")

    def find_nearby_boxes(self):
        if not self.selected_box_id:
            print("No box selected!")
            return
        try:
            dx_min = float(self.dx_min_entry.get())
            dx_max = float(self.dx_max_entry.get())
            dy_min = float(self.dy_min_entry.get())
            dy_max = float(self.dy_max_entry.get())
        except ValueError:
            print("Invalid threshold values!")
            return
        selected_box = self.boxes[self.selected_box_id]
        sx, sy = selected_box["real_position"]
        self.nearby_box_ids = []
        for box_id, box in self.boxes.items():
            if box_id == self.selected_box_id:
                continue
            x, y = box["real_position"]
            dx = x - sx
            dy = y - sy
            if dx_min <= dx <= dx_max and dy_min <= dy <= dy_max:
                self.nearby_box_ids.append(box_id)
                print(f"Box {box_id} is nearby relative to {self.selected_box_id}: dx={dx}, dy={dy}")
        self.draw_map()

    def on_canvas_click(self, event):
        cx, cy = event.x, event.y
        rx, ry = self.canvas_to_real(cx, cy)
        print(f"Canvas click at ({cx}, {cy}) => Real coordinates: ({rx:.2f} cm, {ry:.2f} cm)")
        self.canvas.create_text(cx, cy, text=f"({rx:.1f}, {ry:.1f})", fill="blue", font=("Arial", 8))

    def draw_zone(self, x_left, x_right, y_bottom, y_top, fill_color, stipple, tag):
        p_top_left = self.real_to_canvas(x_left, y_top)
        p_bottom_right = self.real_to_canvas(x_right, y_bottom)
        self.canvas.create_rectangle(p_top_left[0], p_top_left[1],
                                     p_bottom_right[0], p_bottom_right[1],
                                     fill=fill_color, stipple=stipple, outline="", tags=tag)

    def draw_zones(self):
        """
        Desenează zonele relative la cutia selectată conform partiționării definite:
          - Danger Zones (roșu): 
              • Danger A – x din [bx-10.5, bx+10.5], y din [min_y, by-7];
              • Danger B – x din [bx-5, bx+5], y din [by-7, by-1.5].
          - Proximity Zones (purple): 
              • Stânga – x din [bx-3, bx-1.5], y din [by-1.5, by+2];
              • Dreapta – x din [bx+1.5, bx+3], y din [by-1.5, by+2].
          - Warning Zones (portocaliu): x între [bx-10.5, bx-5] și [bx+5, bx+10.5], y din [by-7, by-1.5].
          - Safe Zones (verde): zona centrală de la [bx-10.5, bx+10.5] și y din [by-1.5, max_y],
                               plus zone laterale din [min_x, bx-10.5] și [bx+10.5, max_x].
        După desenarea zonelor se apelează analiza cutiilor (metoda analyze_boxes).
        Dacă o cutie intersectează mai multe zone, se consideră că aparține zonei cu prioritate:
            Danger > Proximity > Warning > Safe.
        """
        self.canvas.delete("zone")
        if not self.selected_box_id:
            print("No box selected to draw zones!")
            return

        sel_box = self.boxes[self.selected_box_id]
        bx, by = sel_box["real_position"]

        # Safe Zone
        safe_central_left = bx - 10.5
        safe_central_right = bx + 10.5
        safe_y_bottom = by - 1.5
        safe_y_top = self.max_y

        safe_left_left = self.min_x
        safe_left_right = bx - 10.5

        safe_right_left = bx + 10.5
        safe_right_right = self.max_x

        # Warning Zones
        warning_y_top = by - 1.5
        warning_y_bottom = by - 7
        warning_left_left = bx - 10.5
        warning_left_right = bx - 5
        warning_right_left = bx + 5
        warning_right_right = bx + 10.5

        # Danger Zones
        danger_A_left = bx - 10.5
        danger_A_right = bx + 10.5
        danger_A_y_top = by - 7
        danger_A_y_bottom = self.min_y

        danger_B_left = bx - 5
        danger_B_right = bx + 5
        danger_B_y_top = by - 1.5
        danger_B_y_bottom = by - 7

        # Proximity Zones
        proximity_y_bottom = by - 1.5
        proximity_y_top = by + 2
        proximity_left_left = bx - 3.5
        proximity_left_right = bx - 1.5
        proximity_right_left = bx + 1.5
        proximity_right_right = bx + 3.5

        # Desenăm zonele Danger
        self.draw_zone(danger_A_left, danger_A_right, danger_A_y_bottom, danger_A_y_top, "red", "gray50", "zone")
        self.draw_zone(danger_B_left, danger_B_right, danger_B_y_bottom, danger_B_y_top, "red", "gray50", "zone")

        # Desenăm zonele Warning
        self.draw_zone(warning_left_left, warning_left_right, warning_y_bottom, warning_y_top, "orange", "gray50", "zone")
        self.draw_zone(warning_right_left, warning_right_right, warning_y_bottom, warning_y_top, "orange", "gray50", "zone")

        # Desenăm zonele Safe (se poate suprapune peste safe)
        self.draw_zone(safe_central_left, safe_central_right, safe_y_bottom, safe_y_top, "green", "gray50", "zone")
        self.draw_zone(safe_left_left, safe_left_right, self.min_y, self.max_y, "green", "gray50", "zone")
        self.draw_zone(safe_right_left, safe_right_right, self.min_y, self.max_y, "green", "gray50", "zone")



        # Desenăm zonele Proximity
        self.draw_zone(proximity_left_left, proximity_left_right, proximity_y_bottom, proximity_y_top, "purple", "gray50", "zone")
        self.draw_zone(proximity_right_left, proximity_right_right, proximity_y_bottom, proximity_y_top, "purple", "gray50", "zone")


        print("Filled zones drawn relative to selected box:", self.selected_box_id)
        self.analyze_boxes()

    def classify_box(self, box, target_box):
        """
        Clasifică o cutie (box) relativ la cutia target (target_box) considerând că fiecare cutie este un pătrat de 3 cm.
        Prioritatea: Danger > Proximity > Warning > Safe.
        Returnează:
           - "Danger" dacă intersecția verticală cu zona Danger este >= 0.5 cm,
           - "Proximity" dacă cutia intersectează zona proximity,
           - "Warning" dacă intersecția cu zona Warning este >= 1 cm (și nu e în Danger sau Proximity),
           - altfel "Safe".
        """
        x, y = box["real_position"]
        bx, by = target_box["real_position"]
        left = x - 1.5
        right = x + 1.5
        top = y + 1.5
        bottom = y - 1.5
        
        

        # Calcul Danger (la fel ca înainte)
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

        # Verificare zonă Proximity: se verifică dacă există intersecție nenulă
        prox_bottom = by - 1.5
        prox_top = by + 2
        prox_left_left = bx - 3.5
        prox_left_right = bx - 1.5
        prox_right_left = bx + 1.5
        prox_right_right = bx + 3.5

        def intersects(zone_left, zone_right, zone_bottom, zone_top, rect_left, rect_right, rect_bottom, rect_top):
            horiz_overlap = min(zone_right, rect_right) - max(zone_left, rect_left)
            vert_overlap = min(zone_top, rect_top) - max(zone_bottom, rect_bottom)
            return horiz_overlap > 0 and vert_overlap > 0

        in_proximity = (intersects(prox_left_left, prox_left_right, prox_bottom, prox_top, left, right, bottom, top) or
                        intersects(prox_right_left, prox_right_right, prox_bottom, prox_top, left, right, bottom, top))
        if in_proximity:
            return "Proximity"

        # Calcul Warning (la fel ca înainte)
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

    def analyze_boxes(self):
        """
        Parcurge toate cutiile (exceptând cea selectată) și le clasifică relativ la cutia selectată,
        afișând în consolă liste separate pentru "Danger", "Proximity", "Warning" și "Safe".
        Se afișează doar cutiile din zonele Danger, Proximity și Warning.
        """
        if not self.selected_box_id:
            print("No box selected for analysis!")
            return
        sel_box = self.boxes[self.selected_box_id]
        danger_list = []
        proximity_list = []
        warning_list = []
        safe_list = []
        for box_id, box in self.boxes.items():
            if box_id == self.selected_box_id:
                continue
            cls = self.classify_box(box, sel_box)
            if cls == "Danger":
                danger_list.append((box_id, box))
            elif cls == "Proximity":
                proximity_list.append((box_id, box))
            elif cls == "Warning":
                warning_list.append((box_id, box))
            else:
                safe_list.append((box_id, box))
        print("Analysis of boxes relative to selected box:")
        print("Danger:", [(bid, b["color"], b["letter"]) for bid, b in danger_list])
        print("Proximity:", [(bid, b["color"], b["letter"]) for bid, b in proximity_list])
        print("Warning:", [(bid, b["color"], b["letter"]) for bid, b in warning_list])
        print("Safe:", [(bid, b["color"], b["letter"]) for bid, b in safe_list if False])  # Safe nu se afișează

# --- Funcții de analiză pentru sesiune (modul complet) ---

def classify_box_relative(other, target):
    """
    Funcție de clasificare similară cu metoda classify_box, dar la nivel de modul.
    Prioritatea: Danger > Proximity > Warning > Safe.
    Returnează "Danger", "Proximity", "Warning" sau "Safe" pentru cutia 'other' relativ la cutia 'target'.
    """
    x, y = other["real_position"]
    bx, by = target["real_position"]

    left = x - 1.5
    right = x + 1.5
    top = y + 1.5
    bottom = y - 1.5


    # Calcul Danger
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
    if danger_overlap >= 0.6:
        return "Danger"

    # Verificare zonă Proximity
    prox_bottom = by - 1.5
    prox_top = by + 2
    prox_left_left = bx - 3.6
    prox_left_right = bx - 1.5
    prox_right_left = bx + 1.5
    prox_right_right = bx + 3.6

    def intersects(zone_left, zone_right, zone_bottom, zone_top, rect_left, rect_right, rect_bottom, rect_top):
        horiz_overlap = min(zone_right, rect_right) - max(zone_left, rect_left)
        vert_overlap = min(zone_top, rect_top) - max(zone_bottom, rect_bottom)
        return horiz_overlap > 0 and vert_overlap > 0


    in_proximity = (intersects(prox_left_left, prox_left_right, prox_bottom, prox_top, left, right, bottom, top) or
                    intersects(prox_right_left, prox_right_right, prox_bottom, prox_top, left, right, bottom, top))
    if in_proximity:
        return "Proximity"

    # Calcul Warning
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
    """
    Selectează cutia candidate din sesiune.
    Dacă există cutii care, analizate ca target, NU au vecini în zona Danger, se alege cea mai apropiată de centru (0,0).
    Dacă nu, se alege cutia cu cel mai mic număr de vecini Danger (și, în caz de egalitate, cea mai apropiată de centru).
    Returnează un tuple (candidate_id, candidate_box).
    """
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

def analyze_target_zones(session, target_box_id=None):
    """
    Analizează zona în jurul unei cutii target din sesiune.
    
    Parametri:
      - session: dicționarul de sesiune cu cutii procesate (formatul este cel generat de process_boxes)
      - target_box_id: (opțional) ID-ul cutiei target. Dacă nu este furnizat sau nu se găsește,
          se returnează safe_flag = 1 și liste goale.
    
    Returnează un tuple format din:
      - safe_flag: 1 dacă nici o cutie nu se găsește în zonele Danger, Proximity sau Warning (adică targetul este considerat safe),
                    0 dacă există cel puțin o cutie în oricare dintre aceste zone.
      - danger_list: listă de tuple (ID, culoare, literă) pentru cutiile clasificate ca fiind în Danger
      - proximity_list: listă de tuple (ID, culoare, literă) pentru cutiile clasificate ca fiind în Proximity
      - warning_list: listă de tuple (ID, culoare, literă) pentru cutiile clasificate ca fiind în Warning
    """
    

    
    if target_box_id is None or target_box_id not in session:
        return 1, [], [], []
    
    candidate = session[target_box_id]
    danger_list = []
    proximity_list = []
    warning_list = []
    
    for box_id, box in session.items():
        if box_id == target_box_id:
            continue
        classification = classify_box_relative(box, candidate)
        if classification == "Danger":
            danger_list.append((box_id, box.get("color"), box.get("letter")))
        elif classification == "Proximity":
            proximity_list.append((box_id, box.get("color"), box.get("letter")))
        elif classification == "Warning":
            warning_list.append((box_id, box.get("color"), box.get("letter")))
    
    safe_flag = 1 if not danger_list and not proximity_list and not warning_list else 0
    return safe_flag, danger_list, proximity_list, warning_list

def analyze_session_boxes(session, target_box_id=None, mandatory=False):
    """
    Analizează sesiunea de cutii și returnează o listă de ID-uri ordonată crescător după diferența verticală față de target,
    împreună cu trei flaguri explicative:
      - "target_in_first": 1 dacă prima cutie din listă este targetul solicitat,
      - "danger_neighbor_count": numărul de vecini clasificați ca Danger,
      - "target_specified_in_session": 1 dacă targetul a fost furnizat și găsit, 0 altfel.
    
    Dacă target_box_id nu este furnizat sau nu se găsește în sesiune, se alege cea mai apropiată de centru care nu are vecini în Danger.
    Dacă mandatory este True, targetul este inclus în listă chiar dacă nu este clasificat ca non-safe.
    """
    

    
    target_specified = 1 if target_box_id in session else 0
    if target_box_id is None or target_box_id not in session:
        target_box_id, target_box = select_best_candidate(session)
    else:
        target_box = session[target_box_id]

    danger_count = 0
    neighbors = []
    for box_id, box in session.items():
        if box_id == target_box_id:
            continue
        cls = classify_box_relative(box, target_box)
        if cls == "Danger":
            danger_count += 1
        if cls in ["Danger", "Proximity", "Warning"]:
            diff = abs(box["real_position"][1] - target_box["real_position"][1])
            neighbors.append((box_id, diff))
    neighbors.sort(key=lambda x: x[1])
    neighbor_ids = [nid for nid, _ in neighbors]
    target_in_first = 0
    if mandatory:
        neighbor_ids.insert(0, target_box_id)
        target_in_first = 1
    else:
        if neighbor_ids and neighbor_ids[0] == target_box_id:
            target_in_first = 1
    flags = {
        "target_in_first": target_in_first,
        "danger_neighbor_count": danger_count,
        "target_specified_in_session": target_specified
    }
    return neighbor_ids, flags
    
    
    

def analyze_virtual_box(virtual_position, session, ghost_size=(3, 3), ghost_angle=0):
    """
    Primește:
      - virtual_position: un tuple (x, y) în centimetri,
      - session: dicționarul de cutii procesate (unde fiecare cutie are cel puțin cheile "real_position", "real_size" și "angle"),
      - ghost_size (opțional): dimensiunea virtuală a cutiei (default (3, 3) cm),
      - ghost_angle (opțional): unghiul cutiei virtuale (default 0).
      
    Creează o cutie virtuală (ghost box) la poziția dată și analizează cutiile din sesiune relativ la aceasta,
    folosind funcția de clasificare (classify_box_relative).
    
    Returnează un tuple format din:
      - safe_flag: 1 dacă nici o cutie din sesiune nu se găsește în zonele Danger, Proximity sau Warning relativ la ghost box,
                   0 altfel.
      - danger_list: listă de tuple (ID, culoare, literă) pentru cutiile clasificate ca fiind în Danger.
      - proximity_list: listă de tuple (ID, culoare, literă) pentru cutiile clasificate ca fiind în Proximity.
      - warning_list: listă de tuple (ID, culoare, literă) pentru cutiile clasificate ca fiind în Warning.
    """
    # Creează cutia virtuală (ghost box)
    ghost_box = {
        "real_position": virtual_position,
        "real_size": ghost_size,
        "angle": ghost_angle,
        "color": "ghost",  # sau orice altă etichetă pentru cutiile virtuale
        "letter": ""
    }
    
    danger_list = []
    proximity_list = []
    warning_list = []
    
    # Iterează peste toate cutiile din sesiune și le clasifică relativ la ghost_box
    for box_id, box in session.items():
        classification = classify_box_relative(box, ghost_box)
        if classification == "Danger":
            danger_list.append((box_id, box.get("color"), box.get("letter")))
        elif classification == "Proximity":
            proximity_list.append((box_id, box.get("color"), box.get("letter")))
        elif classification == "Warning":
            warning_list.append((box_id, box.get("color"), box.get("letter")))
    
    safe_flag = 1 if not danger_list and not proximity_list and not warning_list else 0
    return safe_flag, danger_list, proximity_list, warning_list
    
    
    
    
    
# --- Exemplu de utilizare a modulului complet ---
if __name__ == "__main__":
    # Exemplu de dicționar de sesiune cu două cutii: "K" (albastră) și "A" (roșie)
    session = {
        "K": {
            "position": (250, 150),  # valori în pixeli
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
    boxes = process_boxes(session)
    
    # Pornim interfața grafică
    app = BoxMapApp(boxes)
    # Apăsând pe "Show Zones" se vor desena zonele și se va apela analiza cutiilor (metoda analyze_boxes din interfață)
    app.root.mainloop()

    # Exemplu de apelare a funcției de analiză fără interfață:
    result_list, flags = analyze_session_boxes(boxes, target_box_id="K", mandatory=True)
    print("Analysis result (mandatory):", result_list)
    print("Flags:", flags)
