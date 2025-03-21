#!/usr/bin/env python3
"""
Modul: zone_module.py

Acest modul procesează o imagine (de la cameră) pentru a detecta o zonă
definită de componente conexe și convex hull. Funcția principală, detect_zone,
primește:
  - image_copy: o copie a imaginii (512x512) (obligatoriu),
  - positions: o poziție (tuple) sau o listă de poziții (opțional),
  - debug: flag boolean; dacă True se afișează interfața Tkinter pentru vizualizare.

La final, funcția returnează:
  - zone_limits: un dicționar cu limitele zonei (left, right, top, bottom),
  - pos_flags: o listă de 1 sau 0, indicând pentru fiecare poziție dacă este în zonă (1) sau nu (0),
  - polygon_points: lista de tuple (x, y) reprezentând punctele care alcătuiesc poligonul (convex hull)
"""

import tkinter as tk
from collections import deque
from  .detect_zona import detect_rotated_lines_in_mosaic

##############################################################################
# Funcții helper pentru grid, BFS, filtrare
##############################################################################

def build_grid(coords, x_min=-25, x_max=25, y_min=-10, y_max=30):
    """
    Construiește un grid 2D (matrice) pe baza coordonatelor (în cm, integerizate).
    Returnează (grid, offset_x, offset_y).
    """
    offset_x = -x_min
    offset_y = -y_min
    width = x_max - x_min + 1
    height = y_max - y_min + 1
    
    # Inițializare grid cu 0
    grid = [[0]*width for _ in range(height)]
    
    # Marcare în grid (rotunjim coordonatele dacă sunt float)
    for (x, y) in coords:
        gx = int(round(x + offset_x))
        gy = int(round(y + offset_y))
        if 0 <= gx < width and 0 <= gy < height:
            grid[gy][gx] = 1
    
    return grid, offset_x, offset_y

def get_neighbors_8(x, y, width, height):
    """Returnează vecinii (8-direcții) ai celulei (x, y)."""
    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            if dx == 0 and dy == 0:
                continue
            nx = x + dx
            ny = y + dy
            if 0 <= nx < width and 0 <= ny < height:
                yield nx, ny

def find_connected_components(grid):
    """
    Găsește componentele conexe în grid (8-direcții).
    Returnează o listă de liste, fiecare sub-listă fiind coordonatele (x, y) ale unei componente.
    """
    height = len(grid)
    if height == 0:
        return []
    width = len(grid[0])
    visited = [[False]*width for _ in range(height)]
    components = []
    
    for y in range(height):
        for x in range(width):
            if grid[y][x] == 1 and not visited[y][x]:
                comp = []
                queue = deque()
                queue.append((x, y))
                visited[y][x] = True
                
                while queue:
                    cx, cy = queue.popleft()
                    comp.append((cx, cy))
                    for nx, ny in get_neighbors_8(cx, cy, width, height):
                        if grid[ny][nx] == 1 and not visited[ny][nx]:
                            visited[ny][nx] = True
                            queue.append((nx, ny))
                components.append(comp)
    return components

def filter_components(components, min_size=4, min_width=2, min_height=2):
    """
    Elimină componentele care:
      - au mai puțin de 'min_size' celule,
      - au un bounding box cu lățime < min_width sau înălțime < min_height.
    Returnează componentele acceptate.
    """
    filtered = []
    for comp in components:
        if len(comp) < min_size:
            continue
        xs = [p[0] for p in comp]
        ys = [p[1] for p in comp]
        w = max(xs) - min(xs) + 1
        h = max(ys) - min(ys) + 1
        if w < min_width or h < min_height:
            continue
        filtered.append(comp)
    return filtered

def reconstruct_coords(component, offset_x, offset_y):
    """
    Reconstruiește coordonatele reale (în cm) din coordonatele de grid (x, y)
    pentru o singură componentă.
    """
    coords = []
    for (gx, gy) in component:
        rx = gx - offset_x
        ry = gy - offset_y
        coords.append((rx, ry))
    return coords

##############################################################################
# Funcții pentru convex hull și testul de interior
##############################################################################

def cross(o, a, b):
    """Produsul vectorial pentru determinarea orientării."""
    return (a[0] - o[0])*(b[1] - o[1]) - (a[1] - o[1])*(b[0] - o[0])

def convex_hull(points):
    """Calculează coaja convexă a unei liste de puncte folosind algoritmul Monotone Chain."""
    points = sorted(set(points))
    if len(points) <= 1:
        return points
    lower = []
    for p in points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]

def point_in_poly(x, y, poly):
    """
    Verifică dacă punctul (x, y) se află în interiorul poligonului.
    (Implementare bazată pe algoritmul ray-casting)
    """
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

def adapt_hull_coordinates(hull, x_min, y_max):
    """Transformă coordonatele hull (în cm) astfel încât originea să fie în stânga sus.
    - x_adaptat = x - x_min
    - y_adaptat = y_max - y
    Returnează lista de puncte adaptate."""
    adapted = []
    for (x, y) in hull:
        adapted.append((x - x_min, y_max - y))
    return adapted

##############################################################################
# Funcția principală de procesare a zonei
##############################################################################

def detect_zone(image_copy, positions=None, debug=False):
    """
    Procesează imaginea pentru a detecta zona definită de blocurile identificate.
    
    Parametri:
      - image_copy: copie a imaginii (512x512) preprocesate.
      - positions: o poziție (tuple) sau o listă de poziții (tuple), fiecare în coordonate (cm),
                   pentru care se va verifica dacă se află în interiorul zonei.
      - debug: dacă True, se afișează interfața Tkinter pentru vizualizare.
    
    Proces:
      1. Se obțin coordonatele brute (în cm) folosind funcția detect_rotated_lines_in_mosaic.
      2. Se construiește un grid și se identifică componentele conexe.
      3. Se filtrează componentele mici, se selectează cea mai mare componentă și se calculează convex hull.
      4. Se determină limitele zonei (left, right, top, bottom) din convex hull.
      5. (Opțional) Se verifică, pentru fiecare poziție dată, dacă se află în interiorul zonei.
      6. Dacă debug==True, se afișează interfața Tkinter cu vizualizarea punctelor și conturului.
      7. Dacă debug==True, se deschide o nouă interfață pentru a desena poligonul hull "în cm"
         (fără scalări suplimentare, doar 1:1 convertit la pixeli pe baza unui canvas de 60x60 cm).
    
    Returnează:
      - zone_limits: dicționar cu cheile "left", "right", "top", "bottom".
      - pos_flags: listă de 1/0 pentru fiecare poziție (1 dacă este în zonă, 0 în caz contrar).
      - polygon_points: lista de tuple (x, y) reprezentând punctele care alcătuiesc poligonul (convex hull)
    """
    # 1) Obținem coordonatele brute (în cm) din imagine
    coords_raw = detect_rotated_lines_in_mosaic(image_copy, debug=debug)
    # coords_raw este o listă de tuple (x_cm, y_cm)
    
    # Parametri pentru aria de interes
    x_min, x_max = -25, 25
    y_min, y_max = -10, 30

    # 2) Construim gridul pe baza coordonatelor brute
    grid, offset_x, offset_y = build_grid(coords_raw, x_min, x_max, y_min, y_max)

    # 3) Găsim componentele conexe
    comps = find_connected_components(grid)

    # 4) Filtrăm componentele (eliminăm zgomotul)
    comps_filtered = filter_components(comps, min_size=4, min_width=2, min_height=2)

    # 5) Alegem componenta cu cele mai multe celule
    if comps_filtered:
        largest_comp = max(comps_filtered, key=len)
    else:
        largest_comp = []

    # 6) Reconstruim coordonatele 'curate' pentru componenta selectată
    coords_clean = reconstruct_coords(largest_comp, offset_x, offset_y)

    # 7) Calculăm convex hull-ul pentru coordonatele filtrate
    if coords_clean:
        hull = convex_hull(coords_clean)
    else:
        hull = []

    # 8) Determinăm limitele extreme ale zonei
    if hull:
        right_bound = max(x for x, y in hull)
        left_bound  = min(x for x, y in hull)
        top_bound   = max(y for x, y in hull)
        bottom_bound= min(y for x, y in hull)
    else:
        right_bound = left_bound = top_bound = bottom_bound = 999

    zone_limits = {"left": left_bound, "right": right_bound,
                   "top": top_bound, "bottom": bottom_bound}

    # 9) (Opțional) Afișare interfață Tkinter pentru vizualizare standard
    if debug:
        scale = 20  # 1 cm = 20 pixeli
        canvas_width = (x_max - x_min) * scale
        canvas_height = (y_max - y_min) * scale

        root = tk.Tk()
        root.title("Debug - Vizualizare Zonă Detectată")
        canvas = tk.Canvas(root, width=canvas_width, height=canvas_height, bg="white")
        canvas.pack()

        def to_canvas_coords(rx, ry):
            cx = (rx - x_min) * scale
            cy = canvas_height - (ry - y_min) * scale
            return cx, cy

        # A) Desenăm punctele brute (roșu)
        for (x_cm, y_cm) in coords_raw:
            left_rect = x_cm - 0.5
            right_rect = x_cm + 0.5
            bottom_rect = y_cm - 0.5
            top_rect = y_cm + 0.5
            cx1, cy1 = to_canvas_coords(left_rect, top_rect)
            cx2, cy2 = to_canvas_coords(right_rect, bottom_rect)
            canvas.create_rectangle(cx1, cy1, cx2, cy2, fill="red", outline="black")

        # B) Desenăm punctele din componenta cea mai mare (verde)
        for (x_cm, y_cm) in coords_clean:
            left_rect = x_cm - 0.5
            right_rect = x_cm + 0.5
            bottom_rect = y_cm - 0.5
            top_rect = y_cm + 0.5
            cx1, cy1 = to_canvas_coords(left_rect, top_rect)
            cx2, cy2 = to_canvas_coords(right_rect, bottom_rect)
            canvas.create_rectangle(cx1, cy1, cx2, cy2, fill="green", outline="black")

        # C) Desenăm conturul convex hull (albastru)
        if hull:
            hull_canvas_coords = [to_canvas_coords(x, y) for x, y in hull]
            for i in range(len(hull_canvas_coords)):
                x1, y1 = hull_canvas_coords[i]
                x2, y2 = hull_canvas_coords[(i + 1) % len(hull_canvas_coords)]
                canvas.create_line(x1, y1, x2, y2, fill="blue", width=2)

        # D) Funcția de click: afișează dacă punctul este în interior sau exterior
        def on_canvas_click(event):
            rx = (event.x / scale) + x_min
            ry = y_min + (canvas_height - event.y) / scale
            if hull and point_in_poly(rx, ry, hull):
                flag = 1
            else:
                flag = 0
            print(f"Click la ({rx:.2f}, {ry:.2f}): {'Inside' if flag==1 else 'Outside'}")
            size = 0.3  # cm
            left_rect = rx - size/2
            right_rect = rx + size/2
            bottom_rect = ry - size/2
            top_rect = ry + size/2
            cx1, cy1 = to_canvas_coords(left_rect, top_rect)
            cx2, cy2 = to_canvas_coords(right_rect, bottom_rect)
            color = "magenta" if flag == 1 else "yellow"
            canvas.create_rectangle(cx1, cy1, cx2, cy2, fill=color, outline="black")
        canvas.bind("<Button-1>", on_canvas_click)
        root.mainloop()

    # 10) Procesăm parametrul positions (dacă este furnizat)
    pos_flags = []
    if positions is not None:
        if isinstance(positions, tuple) and len(positions) == 2 and isinstance(positions[0], (int, float)):
            positions = [positions]
        for pos in positions:
            x, y = pos
            if hull and point_in_poly(x, y, hull):
                pos_flags.append(1)
            else:
                pos_flags.append(0)

    # Adaptăm coordonatele hull pentru afișare în "sistemul în cm" 1:1
    # (Folosim x_min=0 și y_max=30 pentru a "mută" originea în stânga sus)
    adapted_hull = adapt_hull_coordinates(hull, x_min=0, y_max=30)

    # Dacă debug este True, deschidem o nouă interfață pentru a desena poligonul hull
    # fără scalări speciale (doar 1:1, folosind un canvas de 60x60 cm).
    if debug:
        cm_scale = 10  # 1 cm = 10 pixeli (pentru vizualizare)
        canvas_cm_width = 60 * cm_scale
        canvas_cm_height = 60 * cm_scale

        # Funcție de conversie simplă: presupunem originea în stânga jos (0,0) și 1 cm = 10 pixeli.
        def cm_to_canvas(x, y):
            cx = (x+30) * cm_scale
            cy = canvas_cm_height - (15+y) * cm_scale
            return cx, cy

        debug_root = tk.Tk()
        debug_root.title("Debug - Hull în coordonate cm (1:1)")
        debug_canvas = tk.Canvas(debug_root, width=canvas_cm_width, height=canvas_cm_height, bg="white")
        debug_canvas.pack()

        # Desenăm o grilă simplă (opțional)
        for i in range(0, 61):
            x_coord = i * cm_scale
            debug_canvas.create_line(x_coord, 0, x_coord, canvas_cm_height, fill="#e0e0e0")
        for i in range(0, 61):
            y_coord = i * cm_scale
            debug_canvas.create_line(0, canvas_cm_height - y_coord, canvas_cm_width, canvas_cm_height - y_coord, fill="#e0e0e0")

        # Desenăm poligonul hull folosind coordonatele adaptate (care sunt în cm)
        if adapted_hull and len(adapted_hull) >= 3:
            points = []
            for (x, y) in adapted_hull:
                cx, cy = cm_to_canvas(x, y)
                points.extend([cx, cy])
            debug_canvas.create_polygon(points, outline="blue", fill="", width=2)
        else:
            debug_canvas.create_text(canvas_cm_width/2, canvas_cm_height/2, text="Hull invalid", fill="red", font=("Arial", 16))

        debug_root.mainloop()

    # Returnăm zone_limits, pos_flags și hull adaptat (în cm, 1:1)
    return zone_limits, pos_flags, adapted_hull

##############################################################################
# Exemplu de rulare standalone (doar pentru testare)
##############################################################################
if __name__ == "__main__":
    from CAMERA.camera_session import capture_raw_image
    image_copy = capture_raw_image()
    test_positions = [(-20, 5), (0, 0), (10, 20)]
    limits, flags = detect_zone(image_copy, positions=test_positions, debug=True)
    print("Limitele zonei:", limits)
    print("Rezultatul verificării pozițiilor:", flags)
