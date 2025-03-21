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
    Primește coordonate reale (x și y, în cm) și returnează coordonatele detectate (în pixeli),
    folosind relațiile inverse:
      - detected_y = (real_y + 4.47) / 0.05587
      - center_x = 0.0203 * detected_y + 230.38
      - scale_x  = 0.0000608 * detected_y + 0.046936
      - detected_x = (real_x / scale_x) + center_x
    """
    detected_y = (real_y + 4.47) / 0.05587
    center_x = 0.0203 * detected_y + 230.38
    scale_x = 0.0000608 * detected_y + 0.046936
    detected_x = (real_x / scale_x) + center_x
    return int(round(detected_x)), int(round(detected_y))

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
        cv2.imshow("Detected Zone", debug_img)
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
