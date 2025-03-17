#!/usr/bin/env python3
"""
Module: box_map_interface
Descriere: Primește un dicționar cu informații despre cutii (culoare, literă, poziție, dimensiune, etc.),
           convertește coordonatele detectate (pixeli) în coordonate reale (cm) folosind funcțiile de
           conversie și desenează o interfață Tkinter fixă cu un grid (de la -25 la 25 pe axa X și -10 la 30 pe axa Y).
           Pe hartă se afișează etichete cu coordonate (ex. -25 cm, -24 cm, …, 25 cm pe X și -10, -9, …, 30 cm pe Y).
           De asemenea, se permite click pe hartă pentru afișarea coordonatelor reale.
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

def getRealCoordinates(detected_x, detected_y):
    center_x = get_center_x(detected_y)
    scale_x = get_scale_x(detected_y)
    real_x = (detected_x - center_x) * scale_x
    real_y = get_real_y(detected_y)
    return round_to_half(real_x), round_to_half(real_y)

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

# --- Clasa pentru interfața Tkinter ---
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

        # Desenăm gridul cu patratele și etichete
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

        # Butoane (opționale)
        self.select_button = tk.Button(self.root, text="Select Random Box", command=self.select_random_box)
        self.select_button.grid(row=3, column=0, columnspan=2)
        self.find_nearby_button = tk.Button(self.root, text="Find Nearby Boxes", command=self.find_nearby_boxes)
        self.find_nearby_button.grid(row=3, column=2, columnspan=2)

        self.draw_map()

    def real_to_canvas(self, x, y):
        """Transformă coordonatele reale (cm) în coordonate de canvas (pixeli)."""
        canvas_x = (x - self.min_x) * self.scale
        # Inversează axa Y: valorile mai mari de y se vor afișa mai sus
        canvas_y = (self.max_y - y) * self.scale
        return canvas_x, canvas_y

    def canvas_to_real(self, cx, cy):
        """Inversul funcției real_to_canvas."""
        x = cx / self.scale + self.min_x
        y = self.max_y - (cy / self.scale)
        return x, y

    def draw_grid(self):
        """Desenează gridul cu pas de 1 cm (patratele)."""
        grid_step = 1  # 1 cm
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
        # Axa X (y=0)
        x0, y0 = self.real_to_canvas(self.min_x, 0)
        x1, y1 = self.real_to_canvas(self.max_x, 0)
        self.canvas.create_line(x0, y0, x1, y1, fill="black", width=2)
        for x in range(self.min_x, self.max_x+1, 5):
            cx, cy = self.real_to_canvas(x, 0)
            self.canvas.create_line(cx, cy-5, cx, cy+5, fill="black")
            self.canvas.create_text(cx, cy+15, text=f"{x} cm", font=("Arial", 8))
        # Axa Y (x=0)
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
        """La click pe canvas, afișează coordonatele reale (în cm)."""
        cx, cy = event.x, event.y
        rx, ry = self.canvas_to_real(cx, cy)
        print(f"Canvas click at ({cx}, {cy}) => Real coordinates: ({rx:.2f} cm, {ry:.2f} cm)")
        # Opțional: poți afișa coordonatele pe canvas
        self.canvas.create_text(cx, cy, text=f"({rx:.1f}, {ry:.1f})", fill="blue", font=("Arial", 8))

    def canvas_to_real(self, cx, cy):
        """Transformă coordonatele din canvas (pixeli) în coordonate reale (cm)."""
        x = cx / self.scale + self.min_x
        y = self.max_y - (cy / self.scale)
        return x, y
