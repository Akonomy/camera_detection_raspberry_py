#!/usr/bin/env python3
"""
Module: draw_session.py
Descriere: Modul care primește o copie a imaginii și un dicționar de sesiune,
desenează pe imagine:
  - Grilă (grid)
  - Zona definită (mark_zone)
  - Pentru fiecare cutie: un bounding box în culoarea specificată și litera (dacă există) centrată, cu text magenta.
Returnează imaginea desenată.
"""

import cv2

# Definim culorile (BGR)
COLOR_MAP = {
    "A": (0, 255, 0),
    "K": (255, 0, 255),
    "O": (255, 255, 255),
    "Green": (0, 255, 0),
    "Red": (255, 0, 0),
    "Sample": (255, 255, 255),
    "Blue": (0, 0, 255)
}

# Zona definită (aceleași ca în alte module)
ZONE_TOP_LEFT = (200, 40)
ZONE_BOTTOM_RIGHT = (295, 160)

def add_grid(image, grid_size=64):
    h, w = image.shape[:2]
    for x in range(0, w, grid_size):
        cv2.line(image, (x, 0), (x, h), (200, 200, 200), 1)
    for y in range(0, h, grid_size):
        cv2.line(image, (0, y), (w, y), (200, 200, 200), 1)
    return image

def mark_zone(image, top_left, bottom_right, label="Defined Zone", color=(0, 0, 255)):
    cv2.rectangle(image, top_left, bottom_right, color, 2)
    cv2.putText(image, label, (top_left[0], top_left[1]-10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    return image

def draw_boxes(image, session_data):
    """
    Pentru fiecare cutie din session_data, se desenează un bounding box și, dacă există, litera în centru.
    """
    for box_id, pkg in session_data.items():
        pos = pkg.get("position", (0, 0))
        size = pkg.get("size")
        # Folosim o dimensiune implicită dacă size nu este disponibil
        if size is None:
            size = (30, 30)
        x, y = pos
        w, h = size
        top_left = (int(x - w/2), int(y - h/2))
        bottom_right = (int(x + w/2), int(y + h/2))
        
        # Determină culoarea bounding box-ului
        box_color_name = pkg.get("box_color", "White")
        box_color = COLOR_MAP.get(box_color_name.capitalize(), (255, 255, 255))
        
        cv2.rectangle(image, top_left, bottom_right, box_color, 2)
        
        # Desenează litera (dacă există) în centrul box-ului, cu text magenta
        letters = pkg.get("letters", [])
        text = letters[0] if letters else ""
        text_position = (int(x), int(y))
        cv2.putText(image, text, text_position, cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 255), 2, cv2.LINE_AA)
    return image

def draw_session_data(image, session_data):
    """
    Primește o copie a imaginii și un dicționar de sesiune,
    desenează pe imagine grila, zona definită și bounding box-urile cu litere.
    Returnează imaginea cu desene.
    """
    output_image = image.copy()
    output_image = add_grid(output_image, grid_size=64)
    output_image = mark_zone(output_image, ZONE_TOP_LEFT, ZONE_BOTTOM_RIGHT, label="Defined Zone", color=(0, 0, 255))
    output_image = draw_boxes(output_image, session_data)
    return output_image

# Exemplu de rulare dacă modulul este executat direct
if __name__ == "__main__":
    # Pentru test, se poate încărca o imagine de test și un dicționar de sesiune fictiv
    test_image = cv2.imread("test_image.jpg")  # asigură-te că ai o imagine de test
    if test_image is None:
        test_image = 255 * np.ones((512, 512, 3), dtype="uint8")
    # Dicționar exemplu de sesiune
    test_session = {
        "GreenK": {"box_color": "Green", "letters": ["K"], "position": (250, 200), "size": (60, 80), "angle": 0},
        "RedO": {"box_color": "Red", "letters": ["O"], "position": (350, 250), "size": (70, 90), "angle": 0}
    }
    drawn = draw_session_data(test_image, test_session)
    cv2.imshow("Drawn Session", drawn)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
