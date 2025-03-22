#!/usr/bin/env python3
"""
Modul: zone_module.py

Acest modul procesează o imagine (de la cameră) pentru a detecta o zonă
definită de componente conexe și convex hull. Funcția principală, detect_zone,
primește:
  - image_copy: o copie a imaginii (512x512) (obligatoriu),
  - positions: o poziție (tuple) sau o listă de poziții (opțional),
  - debug: flag boolean; dacă True se afișează copia imaginii cu poligonul desenat.

La final, funcția returnează:
  - zone_limits: un dicționar cu limitele zonei (left, right, top, bottom),
  - pos_flags: o listă de 1 sau 0, indicând pentru fiecare poziție dacă este în zonă (1) sau nu (0),
  - polygon_points: lista de tuple (x, y) reprezentând punctele care alcătuiesc convex hull-ul.
"""

import math
import cv2
import numpy as np
from collections import deque
from .detect_zona import detect_rotated_lines_in_mosaic

##############################################################################
# Funcții pentru filtrare și clusterizare (eliminarea insulelor)
##############################################################################

def euclidean_distance(p, q):
    return math.sqrt((p[0] - q[0])**2 + (p[1] - q[1])**2)

def cluster_points(points, dist_threshold=1.0, min_cluster_size=4):
    """
    Grupează punctele din lista 'points' pe baza unei distanțe maxime (dist_threshold).
    Se rețin doar clusterele cu cel puțin 'min_cluster_size' puncte.
    """
    clusters = []
    visited = [False] * len(points)
    for i, p in enumerate(points):
        if visited[i]:
            continue
        cluster = []
        queue = [i]
        visited[i] = True
        while queue:
            idx = queue.pop(0)
            cluster.append(points[idx])
            for j, q in enumerate(points):
                if not visited[j] and euclidean_distance(points[idx], q) <= dist_threshold:
                    visited[j] = True
                    queue.append(j)
        if len(cluster) >= min_cluster_size:
            clusters.append(cluster)
    return clusters

##############################################################################
# Funcții pentru convex hull și testul de interior
##############################################################################

def cross(o, a, b):
    return (a[0] - o[0])*(b[1] - o[1]) - (a[1] - o[1])*(b[0] - o[0])

def convex_hull(points):
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
# Funcția de conversie: cm -> pixeli (folosind relațiile inverse)
##############################################################################

def getDetectedCoordinates(real_x, real_y):

    """
    Primește coordonatele reale (real_x, real_y) în centimetri și
    returnează coordonatele detectate (detected_x, detected_y) în pixeli,
    pentru o imagine de 512x512, presupunând că imaginea a fost rotită 180° înainte de procesare.
    
    Operațiunea inversă:
      1. Se inversează calculul lui real_y pentru a obține rotated_y:
            rotated_y = inv_get_real_y(real_y)
         (inv_get_real_y este funcția inversă a lui get_real_y)
      2. Se calculează center_x și scale_x pe baza lui rotated_y:
            center_x = get_center_x(rotated_y)
            scale_x  = get_scale_x(rotated_y)
      3. Se inversează calculul pentru real_x:
            rotated_x = (real_x / scale_x) + center_x
      4. Se inversează rotația de 180°:
            detected_x = (width - 1) - rotated_x
            detected_y = (height - 1) - rotated_y
    """
    width, height = 512, 512

    # Pasul 1: Inversul get_real_y pentru a obține rotated_y
    rotated_y = (real_y + 4.47) / 0.05587

    # Pasul 2: Calculăm center_x și scale_x pentru rotated_y
    center_x = 0.0203 * rotated_y + 230.38
    scale_x = 0.0000608 * rotated_y + 0.046936
    # Inversul calculului pentru real_x:
    rotated_x = (real_x / scale_x) + center_x

    # Pasul 3: Inversăm rotația de 180°
    detected_x = (width - 1) - rotated_x
    detected_y = (height - 1) - rotated_y

    return detected_x, detected_y


##############################################################################
# Funcția principală de procesare a zonei
##############################################################################

def detect_zone(image_copy, positions=None, debug=False):
    """
    Procesează imaginea pentru a detecta zona definită de punctele clusterizate și convex hull.
    
    Pași:
      1. Se obțin coordonatele brute (în cm) din imagine folosind detect_rotated_lines_in_mosaic.
      2. Se clusterizează punctele pentru a elimina insulele mici.
      3. Se selectează cel mai mare cluster și se calculează convex hull-ul acestuia.
      4. Se determină limitele extreme ale zonei din hull.
      5. (Opțional) Se verifică, pentru fiecare poziție dată, dacă se află în interiorul hull-ului.
      6. Dacă debug==True, se afișează copia imaginii cu poligonul convertit din cm în pixeli, desenat pe ea.
    
    Returnează:
      - zone_limits: dicționar cu "left", "right", "top", "bottom"
      - pos_flags: listă de 1/0 pentru fiecare poziție
      - polygon_points: convex hull-ul (listă de puncte în cm)
    """
    # 1) Obține coordonatele brute (în cm)
    coords_raw = detect_rotated_lines_in_mosaic(image_copy, debug=debug)
    
    # 2) Clusterizează punctele pentru a elimina insulele mici
    clusters = cluster_points(coords_raw, dist_threshold=1.0, min_cluster_size=4)
    if clusters:
        largest_cluster = max(clusters, key=len)
    else:
        largest_cluster = []
    
    # 3) Calculează convex hull-ul pentru clusterul selectat
    if largest_cluster:
        hull = convex_hull(largest_cluster)
    else:
        hull = []
    
    # 4) Determină limitele extreme ale zonei din hull
    if hull:
        right_bound = max(x for x, y in hull)
        left_bound  = min(x for x, y in hull)
        top_bound   = max(y for x, y in hull)
        bottom_bound = min(y for x, y in hull)
    else:
        right_bound = left_bound = top_bound = bottom_bound = 999
    zone_limits = {"left": left_bound, "right": right_bound,
                   "top": top_bound, "bottom": bottom_bound}
    
    # 5) Verifică pozițiile furnizate, dacă există, folosind testul de apartenență la hull
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
    
    # 6) Dacă debug==True, afișează copia imaginii cu poligonul desenat (convertit din cm în pixeli)
    if debug:
        debug_img = image_copy.copy()
        if hull and len(hull) >= 3:
            pts = [getDetectedCoordinates(x, y) for (x, y) in hull]
            pts_array = np.array(pts, dtype=np.int32)
            cv2.polylines(debug_img, [pts_array], isClosed=True, color=(255, 0, 0), thickness=2)
        # Adăugăm punctele suplimentare: (+5,0), (-5,0), (0,+5) și (0,-5)
        extra_points = {
            "+X": (5, 0),
            "-X": (-5, 0),
            "+Y": (0, 5),
            "-Y": (0, -5)
        }
        for label, real_pt in extra_points.items():
            detected_pt = getDetectedCoordinates(real_pt[0], real_pt[1])
            # Desenează un cerc mic la poziția detectată
            cv2.circle(debug_img, (int(detected_pt[0]), int(detected_pt[1])), radius=5, color=(0, 255, 0), thickness=-1)

            # Adaugă eticheta lângă punct (offset de 10 pixeli)
            cv2.putText(debug_img, label, (int(detected_pt[0]) + 10, int(detected_pt[1]) + 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.imshow("get_zone Zone", debug_img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    
    return zone_limits, pos_flags, hull

##############################################################################
# Exemplu de rulare standalone (pentru testare)
##############################################################################
if __name__ == "__main__":
    from CAMERA.camera_session import capture_raw_image
    image_copy = capture_raw_image()
    test_positions = [(-20, 5), (0, 0), (10, 20)]
    limits, flags, hull = detect_zone(image_copy, positions=test_positions, debug=True)
    print("Limitele zonei:", limits)
    print("Rezultatul verificării pozițiilor:", flags)
