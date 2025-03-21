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
  - zone_limits: un dicționar cu limitele zonei (left, right, top, bottom).
  - pos_flags: o listă de 1 sau 0, indicând pentru fiecare poziție dacă este în zonă (1) sau nu (0).
  - polygon_points: lista de tuple (x, y) reprezentând punctele care alcătuiesc poligonul (convex hull)
"""
import cv2
import tkinter as tk
from collections import deque
from .detect_zona import detect_rotated_lines_in_mosaic

#---------------------------------------------------------------
#------------------- Grid Building & Offsets -------------------
#---------------------------------------------------------------
def build_grid(coords, x_min=-25, x_max=25, y_min=-10, y_max=30):
    """
    Input: 
      - coords: listă de tuple (x, y) în cm.
      - x_min, x_max, y_min, y_max: limitele zonei de interes (în cm).
    Proces: 
      - Se calculează offset-urile: offset_x = -x_min, offset_y = -y_min.
      - Se creează o matrice (grid) de dimensiune (width x height) cu valori 0.
      - Pentru fiecare coordonată, se calculează poziția în grid (rotunjind coordonatele cu offset)
        și se setează valoarea celulei la 1.
    Output:
      - grid: matricea 2D a zonei.
      - offset_x, offset_y: offseturile folosite.
    """
    offset_x = -x_min
    offset_y = -y_min
    width = x_max - x_min + 1
    height = y_max - y_min + 1
    grid = [[0]*width for _ in range(height)]
    for (x, y) in coords:
        gx = int(round(x + offset_x))
        gy = int(round(y + offset_y))
        if 0 <= gx < width and 0 <= gy < height:
            grid[gy][gx] = 1
    return grid, offset_x, offset_y

#---------------------------------------------------------------
#------------------ Component Extraction -----------------------
#---------------------------------------------------------------
def get_neighbors_8(x, y, width, height):
    """Returnează vecinii 8-direcționali ai celulei (x, y) dintr-o matrice de dimensiune (width x height)."""
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
    Input: grid (matrice 2D)
    Proces:
      - Parcurge gridul pentru a găsi componente conexe (folosind BFS).
    Output:
      - Listă de componente, fiecare componentă fiind o listă de coordonate (gx, gy) din grid.
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
    Input: componente (listă de liste de coordonate în grid)
    Proces:
      - Se filtrează componentele prea mici sau cu dimensiuni de bounding box sub pragurile date.
    Output:
      - Listă de componente acceptate.
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
    Input: 
      - component: listă de coordonate (gx, gy) în grid.
      - offset_x, offset_y: offset-urile folosite la construirea gridului.
    Proces:
      - Se inversează operația de offset pentru a obține coordonatele reale (în cm).
    Output:
      - Listă de coordonate (rx, ry) în cm.
    """
    coords = []
    for (gx, gy) in component:
        rx = gx - offset_x
        ry = gy - offset_y
        coords.append((rx, ry))
    return coords

#---------------------------------------------------------------
#----------------- Convex Hull & Point Test --------------------
#---------------------------------------------------------------
def cross(o, a, b):
    """Calculează produsul vectorial (orientarea) pentru punctele o, a, b."""
    return (a[0] - o[0])*(b[1] - o[1]) - (a[1] - o[1])*(b[0] - o[0])

def convex_hull(points):
    """
    Input: listă de puncte (în cm)
    Proces:
      - Se calculează convex hull-ul folosind algoritmul Monotone Chain.
    Output:
      - Listă de puncte (în cm) care formează coaja convexă.
    """
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
    Input:
      - (x, y): punctul de testat (în cm)
      - poly: listă de puncte (în cm) ce formează un poligon
    Proces:
      - Se folosește algoritmul ray-casting pentru a testa dacă punctul se află în interiorul poligonului.
    Output:
      - True dacă punctul este în interior, False altfel.
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
    """
    Input:
      - hull: listă de puncte (în cm)
      - x_min, y_max: limitele folosite pentru reorientare
    Proces:
      - Se "mută" originea poligonului: se scade x_min din toate valorile x și se face y_max - y pentru y.
    Output:
      - Listă de puncte adaptate (în cm), cu originea în colțul stânga sus.
    """
    adapted = []
    for (x, y) in hull:
        adapted.append((x - x_min, y_max - y))
    return adapted

#---------------------------------------------------------------
#------------------ Conversie Inversă: cm -> px -----------------
#---------------------------------------------------------------
def convert_cm_to_px(real_x, real_y):
    """
    Inversele funcției convert_px_to_cm.
    Calculul se face astfel:
      detected_y' = (real_y + 4.47) / 0.05587,
      detected_y = 512 - detected_y'
      center_x = 0.0203 * detected_y' + 230.38
      scale_x = 0.0000608 * detected_y' + 0.046936
      detected_x = real_x / scale_x + center_x
    Output:
      - (detected_x, detected_y): coordonate în pixeli (rotunjite la întreg).
    """
    detected_y_prime = (real_y + 4.47) / 0.05587
    detected_y = 512 - detected_y_prime
    center_x = 0.0203 * detected_y_prime + 230.38
    scale_x = 0.0000608 * detected_y_prime + 0.046936
    detected_x = real_x / scale_x + center_x
    return int(round(detected_x)), int(round(detected_y))

#---------------------------------------------------------------
#------------------- Procesare Zonă ----------------------------
#---------------------------------------------------------------
def detect_zone(image_copy, positions=None, debug=False):
    #---------------------------------------------------------------
    # 1. Extracția coordonatelor brute (în cm) din imagine
    #---------------------------------------------------------------
    # Se apelează detect_rotated_lines_in_mosaic pentru a obține coordonatele în cm
    coords_raw = detect_rotated_lines_in_mosaic(image_copy, debug=debug)
    # Output: coords_raw - listă de tuple (x_cm, y_cm)

    #---------------------------------------------------------------
    # 2. Construirea gridului pe baza coordonatelor
    #---------------------------------------------------------------
    # Setăm limitele zonei de interes în cm:
    x_min, x_max = -25, 25
    y_min, y_max = -10, 30
    # Se construiește gridul și se obțin offset-urile folosite:
    grid, offset_x, offset_y = build_grid(coords_raw, x_min, x_max, y_min, y_max)
    # Output: grid (matrice 2D), offset_x, offset_y

    #---------------------------------------------------------------
    # 3. Extracția componentelor conexe din grid
    #---------------------------------------------------------------
    comps = find_connected_components(grid)
    # Output: comps - listă de componente (listă de coordonate în grid)

    #---------------------------------------------------------------
    # 4. Filtrarea componentelor (eliminarea zgomotului)
    #---------------------------------------------------------------
    comps_filtered = filter_components(comps, min_size=4, min_width=2, min_height=2)
    # Output: comps_filtered - componente acceptate

    #---------------------------------------------------------------
    # 5. Se selectează componenta cu cele mai multe celule
    #---------------------------------------------------------------
    if comps_filtered:
        largest_comp = max(comps_filtered, key=len)
    else:
        largest_comp = []
    # Output: largest_comp - componenta principală (listă de coordonate în grid)

    #---------------------------------------------------------------
    # 6. Reconstruirea coordonatelor reale (în cm) pentru componenta selectată
    #---------------------------------------------------------------
    coords_clean = reconstruct_coords(largest_comp, offset_x, offset_y)
    # Output: coords_clean - listă de tuple (x_cm, y_cm) în coordonate reale

    #---------------------------------------------------------------
    # 7. Calculul convex hull-ului pentru coordonatele filtrate
    #---------------------------------------------------------------
    if coords_clean:
        hull = convex_hull(coords_clean)
    else:
        hull = []
    # Output: hull - listă de puncte (x_cm, y_cm) care formează convex hull-ul

    #---------------------------------------------------------------
    # 8. Determinarea limitelor extreme ale zonei
    #---------------------------------------------------------------
    if hull:
        right_bound = max(x for x, y in hull)
        left_bound  = min(x for x, y in hull)
        top_bound   = max(y for x, y in hull)
        bottom_bound = min(y for x, y in hull)
    else:
        right_bound = left_bound = top_bound = bottom_bound = 999
    zone_limits = {"left": left_bound, "right": right_bound,
                   "top": top_bound, "bottom": bottom_bound}
    # Output: zone_limits - dicționar cu limitele zonei în cm

    #---------------------------------------------------------------
    # 9. (Opțional) Vizualizare debug prin Tkinter (grid, axă, puncte și convex hull)
    #---------------------------------------------------------------
    if debug:
        scale = 20  # 1 cm = 20 pixeli pentru această fereastră
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

        # A) Punctele brute (în roșu)
        for (x_cm, y_cm) in coords_raw:
            left_rect = x_cm - 0.5
            right_rect = x_cm + 0.5
            bottom_rect = y_cm - 0.5
            top_rect = y_cm + 0.5
            cx1, cy1 = to_canvas_coords(left_rect, top_rect)
            cx2, cy2 = to_canvas_coords(right_rect, bottom_rect)
            canvas.create_rectangle(cx1, cy1, cx2, cy2, fill="red", outline="black")

        # B) Punctele din componenta cea mai mare (în verde)
        for (x_cm, y_cm) in coords_clean:
            left_rect = x_cm - 0.5
            right_rect = x_cm + 0.5
            bottom_rect = y_cm - 0.5
            top_rect = y_cm + 0.5
            cx1, cy1 = to_canvas_coords(left_rect, top_rect)
            cx2, cy2 = to_canvas_coords(right_rect, bottom_rect)
            canvas.create_rectangle(cx1, cy1, cx2, cy2, fill="green", outline="black")

        # C) Conturul convex hull (în albastru)
        if hull:
            hull_canvas_coords = [to_canvas_coords(x, y) for x, y in hull]
            for i in range(len(hull_canvas_coords)):
                x1, y1 = hull_canvas_coords[i]
                x2, y2 = hull_canvas_coords[(i + 1) % len(hull_canvas_coords)]
                canvas.create_line(x1, y1, x2, y2, fill="blue", width=2)

        # D) Funcție de click pentru interacțiune
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

    #---------------------------------------------------------------
    # 10. Procesarea opțională a pozițiilor furnizate (verificare în poligon)
    #---------------------------------------------------------------
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
    # Output: pos_flags - listă de flaguri (1 dacă poziția este în poligon)

    #---------------------------------------------------------------
    # 11. Debug suplimentar: Desenare peste copia imaginii primite, puncte cyan convertite în pixeli
    #---------------------------------------------------------------
    if debug:
        debug_img = image_copy.copy()
        # Se obțin coordonatele cyan din mozaicul marcat (folosind funcția din detect_zona)
        
        cyan_coords =  detect_rotated_lines_in_mosaic(debug_img, debug=False)
        for (x_cm, y_cm) in cyan_coords:
            px, py = convert_cm_to_px(x_cm, y_cm)
            
            if y_cm <0:
                cv2.circle(debug_img, (px, py), 3, (0, 255, 0), -1)  # desenează cercuri verzi
                
            elif y_cm==0 and y_cm<1:
                cv2.circle(debug_img, (px, py), 3, (255, 255, 0), -1) 
                
                
            elif y_cm >1 and x_cm>0:
                cv2.circle(debug_img, (px, py), 3, (0, 255, 255), -1) 
                
            else:
                 cv2.circle(debug_img, (px, py), 3, (255, 0, 255), -1) 
                
                       
            cv2.putText(debug_img, "", (px+2, py-2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        cv2.imshow("Debug - Puncte Cyan pe Imagine", debug_img)
        cv2.waitKey(0)
        cv2.destroyWindow("Debug - Puncte Cyan pe Imagine")

    #---------------------------------------------------------------
    # 12. Adaptarea convex hull-ului pentru afișare în sistemul "cm 1:1"
    #---------------------------------------------------------------
    # Se "muta" originea convex hull-ului: x_min se transformă la 0 și y_max la 30
    adapted_hull = adapt_hull_coordinates(hull, x_min=0, y_max=30)

    #---------------------------------------------------------------
    # 13. Debug suplimentar: Afișare poligon hull în coordonate 1:1 (canvas de 60x60 cm)
    #---------------------------------------------------------------
    if debug == "EXIT":
        cm_scale = 10  # 1 cm = 10 pixeli
        canvas_cm_width = 60 * cm_scale
        canvas_cm_height = 60 * cm_scale

        def cm_to_canvas(x, y):
            cx = (x+30) * cm_scale
            cy = canvas_cm_height - (15+y) * cm_scale
            return cx, cy

        debug_root = tk.Tk()
        debug_root.title("Debug - Hull în coordonate cm (1:1)")
        debug_canvas = tk.Canvas(debug_root, width=canvas_cm_width, height=canvas_cm_height, bg="white")
        debug_canvas.pack()

        for i in range(0, 61):
            x_coord = i * cm_scale
            debug_canvas.create_line(x_coord, 0, x_coord, canvas_cm_height, fill="#e0e0e0")
        for i in range(0, 61):
            y_coord = i * cm_scale
            debug_canvas.create_line(0, canvas_cm_height - y_coord, canvas_cm_width, canvas_cm_height - y_coord, fill="#e0e0e0")

        if adapted_hull and len(adapted_hull) >= 3:
            points = []
            for (x, y) in adapted_hull:
                cx, cy = cm_to_canvas(x, y)
                points.extend([cx, cy])
            debug_canvas.create_polygon(points, outline="blue", fill="", width=2)
        else:
            debug_canvas.create_text(canvas_cm_width/2, canvas_cm_height/2, text="Hull invalid", fill="red", font=("Arial", 16))
        debug_root.mainloop()

    #---------------------------------------------------------------
    # 14. Returnarea valorilor finale
    #---------------------------------------------------------------
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
