#!/usr/bin/env python3
import tkinter as tk
from ZONE_DETECT.detect_zona import detect_rotated_lines_in_mosaic

def analyze_zone(coords, x_min=-25, x_max=25, y_min=-10, y_max=30, margin=1):
    """
    Primește o listă de coordonate (x_cm, y_cm) (ideal deduplicate prin snap la întreg)
    și returnează un dicționar cu limitele zonei:
      - left: minimul x - margin (clamped la x_min)
      - right: maximul x + 1 + margin (clamped la x_max)
      - bottom: minimul y - margin (clamped la y_min)
      - top: maximul y + 1 + margin (clamped la y_max)
    Dacă lista este goală, se returnează 999 pentru toate limitele.
    """
    if not coords:
        return {"left": 999, "right": 999, "top": 999, "bottom": 999}
    xs = [round(x) for (x, y) in coords]
    ys = [round(y) for (x, y) in coords]
    left_bound = max(min(xs) - margin, x_min)
    right_bound = min(max(xs) + 1 + margin, x_max)
    bottom_bound = max(min(ys) - margin, y_min)
    top_bound = min(max(ys) + 1 + margin, y_max)
    return {"left": left_bound, "right": right_bound, "top": top_bound, "bottom": bottom_bound}

def main():
    # 1) Obținem coordonatele (x_cm, y_cm) fără să afișăm interfețele suplimentare (debug=False)
    # Funcția importată poate returna fie o listă, fie un dicționar. Presupunem că returnează lista de celule.
    result = detect_rotated_lines_in_mosaic(debug=False)
    coords = result if isinstance(result, list) else result["cells"]
    
    # Pentru o analiză robustă, deduplicăm coordonatele prin "snap" la întreg
    deduped_coords = {(round(x), round(y)) for (x, y) in coords}
    deduped_coords = list(deduped_coords)
    
    # 2) Analizăm zona de interes pe baza celulelor deduplicate
    zone = analyze_zone(deduped_coords)
    
    print("Coordonate detectate:", deduped_coords)
    print("Limitele zonei detectate:", zone)
    
    # 3) Construim interfața Tkinter pentru afișare
    x_min, x_max = -25, 25
    y_min, y_max = -10, 30
    scale = 20  # 1 cm -> 20 pixeli
    width = (x_max - x_min) * scale
    height = (y_max - y_min) * scale

    root = tk.Tk()
    root.title("Test coordonate și zonă detectată")
    canvas = tk.Canvas(root, width=width, height=height, bg="white")
    canvas.pack()

    def to_canvas_coords(real_x, real_y):
        """Transformă coordonatele (cm) în coordonate canvas (pixeli)."""
        cx = (real_x - x_min) * scale
        cy = height - (real_y - y_min) * scale
        return cx, cy

    # Desenăm grid-ul (linii verticale/orizontale și etichete)
    for x in range(x_min, x_max + 1):
        cx, _ = to_canvas_coords(x, y_min)
        canvas.create_line(cx, 0, cx, height, fill="lightgray")
        canvas.create_text(cx, height - 10, text=str(x), fill="black", font=("Arial", 10))
    for y in range(y_min, y_max + 1):
        _, cy = to_canvas_coords(x_min, y)
        canvas.create_line(0, cy, width, cy, fill="lightgray")
        canvas.create_text(20, cy, text=str(y), fill="black", font=("Arial", 10))
    cx0, _ = to_canvas_coords(0, y_min)
    canvas.create_line(cx0, 0, cx0, height, fill="black", width=2)
    _, cy0 = to_canvas_coords(x_min, 0)
    canvas.create_line(0, cy0, width, cy0, fill="black", width=2)

    # Desenăm celulele detectate (deduplicate) ca pătrate cyan
    for (x_cm, y_cm) in deduped_coords:
        left = x_cm - 0.5
        right = x_cm + 0.5
        bottom = y_cm - 0.5
        top = y_cm + 0.5
        cx1, cy1 = to_canvas_coords(left, top)
        cx2, cy2 = to_canvas_coords(right, bottom)
        canvas.create_rectangle(cx1, cy1, cx2, cy2, fill="#00ffff", outline="black")
    
    # Desenăm zona detectată: colorăm toate celulele din interiorul limitelor cu verde
    zb = zone
    for x in range(zb["left"], zb["right"]):
        for y in range(zb["bottom"], zb["top"]):
            cx1, cy1 = to_canvas_coords(x, y+1)
            cx2, cy2 = to_canvas_coords(x+1, y)
            canvas.create_rectangle(cx1, cy1, cx2, cy2, fill="green", outline="black")
    
    root.mainloop()

if __name__ == "__main__":
    main()
