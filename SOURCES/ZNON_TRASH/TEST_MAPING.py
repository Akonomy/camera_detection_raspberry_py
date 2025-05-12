#!/usr/bin/env python3
import tkinter as tk
from collections import deque
from ZONE_DETECT.detect_zona import detect_rotated_lines_in_mosaic

##############################################################################
# Funcții helper pentru grid, BFS, filtrare
##############################################################################

def build_grid(coords, x_min=-25, x_max=25, y_min=-10, y_max=30):
    """
    Construiește un grid 2D (matrice) pe baza coordonatelor integerizate.
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
    """Returnează vecinii (8-direcții) ai celulei (x,y)."""
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
    Returnează o listă de liste, fiecare sub-listă fiind coordonatele (x,y) ale unei componente.
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
    Elimină acele componente care:
      - au mai puțin de 'min_size' celule
      - bounding box < min_width sau < min_height
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
    """Produsul vectorial (cross product) pentru a determina orientarea."""
    return (a[0] - o[0])*(b[1] - o[1]) - (a[1] - o[1])*(b[0] - o[0])

def convex_hull(points):
    """Calculează coaja convexă a unei liste de puncte folosind algoritmul monotone chain."""
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
    """Verifică dacă punctul (x, y) se află în interiorul poligonului (algoritm ray-casting)."""
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

##############################################################################
# Program principal
##############################################################################

def main():
    # 1) Obținem coordonatele brute (în cm) cu potențial zgomot
    coords_raw = detect_rotated_lines_in_mosaic(debug=False)
    print("Coordonate brute:", coords_raw)

    # Parametri pentru aria de interes
    x_min, x_max = -25, 25
    y_min, y_max = -10, 30

    # 2) Construim gridul pe baza coordonatelor brute
    grid, offset_x, offset_y = build_grid(coords_raw, x_min, x_max, y_min, y_max)

    # 3) Găsim componentele conexe (insule)
    comps = find_connected_components(grid)
    print(f"Număr componente înainte de filtrare: {len(comps)}")

    # 4) Filtrăm insulele prea mici (posibil zgomot)
    comps_filtered = filter_components(comps, min_size=4, min_width=2, min_height=2)
    print(f"Număr componente după filtrare: {len(comps_filtered)}")

    # 5) ALEGEM CEA MAI MARE COMPONENTĂ (cea cu cele mai multe celule)
    if not comps_filtered:
        largest_comp = []
    else:
        largest_comp = max(comps_filtered, key=len)  # componenta cu cele mai multe celule

    # 6) Reconstruim coordonatele 'curate' DOAR pentru acea componentă
    coords_clean = reconstruct_coords(largest_comp, offset_x, offset_y)
    print("Coordonate filtrate (componenta cea mai mare):", coords_clean)

    # 7) Aplicăm convex hull pe coordonatele filtrate (pentru contur final)
    if coords_clean:
        hull = convex_hull(coords_clean)
    else:
        hull = []

    # 8) Determinăm limitele extreme (dacă există hull)
    if hull:
        right_bound = max(x for x, y in hull)
        left_bound  = min(x for x, y in hull)
        top_bound   = max(y for x, y in hull)
        bottom_bound= min(y for x, y in hull)
    else:
        right_bound = left_bound = top_bound = bottom_bound = 999

    print("Limita dreapta:", right_bound)
    print("Limita sus:", top_bound)
    print("Limita stânga:", left_bound)
    print("Limita jos:", bottom_bound)

    # 9) Construim interfața Tkinter pentru vizualizare
    scale = 20  # 1 cm -> 20 pixeli
    width = (x_max - x_min) * scale
    height = (y_max - y_min) * scale

    root = tk.Tk()
    root.title("Preferinta pentru un singur grup unificat de pixeli")
    canvas = tk.Canvas(root, width=width, height=height, bg="white")
    canvas.pack()

    def to_canvas_coords(rx, ry):
        """Transformă (rx, ry) din cm în pixeli Canvas."""
        cx = (rx - x_min)*scale
        cy = height - (ry - y_min)*scale
        return cx, cy

    def from_canvas_coords(cx, cy):
        """Transformă coordonatele mouse (canvas_x, canvas_y) în (rx, ry) cm."""
        rx = (cx / scale) + x_min
        ry = y_min + (height - cy)/scale
        return rx, ry

    # A) Desenăm toate punctele brute (roșu)
    for (x_cm, y_cm) in coords_raw:
        left = x_cm - 0.5
        right = x_cm + 0.5
        bottom = y_cm - 0.5
        top = y_cm + 0.5
        cx1, cy1 = to_canvas_coords(left, top)
        cx2, cy2 = to_canvas_coords(right, bottom)
        canvas.create_rectangle(cx1, cy1, cx2, cy2, fill="red", outline="black")

    # B) Desenăm punctele din cea mai mare componentă (verde)
    for (x_cm, y_cm) in coords_clean:
        left = x_cm - 0.5
        right = x_cm + 0.5
        bottom = y_cm - 0.5
        top = y_cm + 0.5
        cx1, cy1 = to_canvas_coords(left, top)
        cx2, cy2 = to_canvas_coords(right, bottom)
        canvas.create_rectangle(cx1, cy1, cx2, cy2, fill="green", outline="black")

    # C) Desenăm conturul coajei convexe (hull) cu linii albastre
    if hull:
        hull_canvas_coords = [to_canvas_coords(x, y) for x, y in hull]
        for i in range(len(hull_canvas_coords)):
            x1, y1 = hull_canvas_coords[i]
            x2, y2 = hull_canvas_coords[(i + 1) % len(hull_canvas_coords)]
            canvas.create_line(x1, y1, x2, y2, fill="blue", width=2)

    # D) Funcția de click: verifică dacă e inside/outside hull
    def on_canvas_click(event):
        # 1) Transformăm coordonatele din pixeli Canvas în cm
        rx, ry = from_canvas_coords(event.x, event.y)
        # 2) Verificăm inside/outside
        if point_in_poly(rx, ry, hull):
            color = "magenta"  # interior
        else:
            color = "yellow"   # exterior
        # 3) Desenăm un mic pătrat la poziția respectivă
        size = 0.3  # cm
        left = rx - size/2
        right = rx + size/2
        top = ry + size/2
        bottom = ry - size/2
        cx1, cy1 = to_canvas_coords(left, top)
        cx2, cy2 = to_canvas_coords(right, bottom)
        canvas.create_rectangle(cx1, cy1, cx2, cy2, fill=color, outline="black")

    # Asociază funcția on_canvas_click la evenimentul <Button-1> (click stânga)
    canvas.bind("<Button-1>", on_canvas_click)

    root.mainloop()

if __name__ == "__main__":
    main()
