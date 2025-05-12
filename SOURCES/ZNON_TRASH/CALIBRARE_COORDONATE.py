#!/usr/bin/env python3
import cv2
import numpy as np
import math
from CAMERA.camera_session import capture_raw_image

### Funcții pentru conversie (corecție perspectivă) ###
def convert_px_to_cm(detected_x, detected_y):
    """
    Converteste coordonatele (detected_x, detected_y) din pixeli în coordonate reale (cm)
    folosind formule empirice, apoi rotunjește rezultatul la cel mai apropiat 0.5 cm.
    
    Se inversează doar coordonata y:
      detected_y = 512 - detected_y
    """
    detected_y = 512 - detected_y
    real_y = 0.05587 * detected_y - 4.47

    center_x = 0.0203 * detected_y + 230.38
    scale_x = 0.0000608 * detected_y + 0.046936
    real_x = (detected_x - center_x) * scale_x

    real_x = round(real_x * 2) / 2
    real_y = round(real_y * 2) / 2

    return real_x, real_y

def convert_cm_to_px(real_x, real_y):
    """
    Inversele funcției convert_px_to_cm.
    Calculul se face astfel:
      detected_y' = (real_y + 4.47) / 0.05587, 
      detected_y = 512 - detected_y'
      center_x = 0.0203 * detected_y' + 230.38
      scale_x = 0.0000608 * detected_y' + 0.046936
      detected_x = real_x / scale_x + center_x
    Returnează coordonatele în pixeli (rotunjite la întreg).
    """
    detected_y_prime = (real_y + 4.47) / 0.05587
    detected_y = 512 - detected_y_prime

    center_x = 0.0203 * detected_y_prime + 230.38
    scale_x = 0.0000608 * detected_y_prime + 0.046936

    detected_x = real_x / scale_x + center_x

    return int(round(detected_x)), int(round(detected_y))

### Funcții pentru procesarea imaginii ###
def create_64x64_mosaic(raw_img):
    h, w, c = raw_img.shape
    if (h != 512 or w != 512):
        print("Atenție: imaginea nu e 512x512. Continuăm oricum...")
    mosaic_64 = np.zeros((64, 64, 3), dtype=np.uint8)
    block_size = 8
    for row in range(64):
        for col in range(64):
            y_start = row * block_size
            y_end   = (row + 1) * block_size
            x_start = col * block_size
            x_end   = (col + 1) * block_size
            block = raw_img[y_start:y_end, x_start:x_end]
            mean_color = block.mean(axis=(0, 1)).astype(np.uint8)
            mosaic_64[row, col] = mean_color
    return mosaic_64

def mark_red_blocks_as_cyan(mosaic_64):
    mosaic_64_marked = mosaic_64.copy()
    hsv = cv2.cvtColor(mosaic_64_marked, cv2.COLOR_RGB2HSV)
    lower_red1 = np.array([0, 80, 80])
    upper_red1 = np.array([15, 255, 255])
    lower_red2 = np.array([160, 80, 80])
    upper_red2 = np.array([180, 255, 255])
    lower_pink = np.array([140, 70, 70])
    upper_pink = np.array([170, 255, 255])
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    red_mask = mask1 | mask2
    mask_pink = cv2.inRange(hsv, lower_pink, upper_pink)
    final_mask = red_mask | mask_pink
    mosaic_64_marked[final_mask == 255] = (0, 255, 255)
    return mosaic_64_marked

def get_cyan_block_coordinates(mosaic):
    cyan_coords = []
    rows, cols, _ = mosaic.shape
    for i in range(rows):
        for j in range(cols):
            if (mosaic[i, j] == np.array([0, 255, 255])).all():
                detected_x = j * 8 + 4
                detected_y = i * 8 + 4
                coord = convert_px_to_cm(detected_x, detected_y)
                cyan_coords.append(coord)
    return cyan_coords

### Funcții pentru desenare de vectori ###
def draw_red_points(image, vectors, y_values):
    """
    Desenează pe imagine, folosind convert_cm_to_px, puncte roșii pentru fiecare vector
    (fixat pe x) și pentru fiecare valoare din y_values (în cm). Etichetează punctul cu formatul "B20" (exemplu).
    """
    for label, x_cm in vectors.items():
        for y_cm in y_values:
            px, py = convert_cm_to_px(x_cm, y_cm)
            cv2.circle(image, (px, py), 2, (0, 0, 255), -1)
            cv2.putText(image, f"{label}{y_cm}", (px+2, py-2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
    return image

def draw_yellow_stars(image, vectors, y_values):
    """
    Desenează pe imagine, folosind convert_cm_to_px, stelute galbene pentru fiecare vector
    (fixat pe x) și pentru fiecare valoare din y_values (în cm). Etichetează cu formatul "B20*" (exemplu).
    """
    for label, x_cm in vectors.items():
        for y_cm in y_values:
            px, py = convert_cm_to_px(x_cm, y_cm)
            cv2.putText(image, f"{label}{y_cm}*", (px+2, py-2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
            cv2.circle(image, (px, py), 2, (0, 255, 255), -1)
    return image

def annotate_corners(image):
    """
    Desenează în colțurile imaginii (în magenta, font mediu) coordonatele pixel ale colțurilor.
    """
    h, w = image.shape[:2]
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(image, f"TL: (0,0)", (5, 20), font, 0.6, (255, 0, 255), 2)
    cv2.putText(image, f"TR: ({w-1},0)", (w-150, 20), font, 0.6, (255, 0, 255), 2)
    cv2.putText(image, f"BL: (0,{h-1})", (5, h-10), font, 0.6, (255, 0, 255), 2)
    cv2.putText(image, f"BR: ({w-1},{h-1})", (w-150, h-10), font, 0.6, (255, 0, 255), 2)
    return image

### Funcția principală de debug pentru vectori pe imagini ###
def debug_vectors_on_images():
    """
    Capturează o imagine 512x512, apoi:
      - Pentru imaginea raw (după conversia BGR->RGB), desenează vectorii de puncte roșii și stelute galbene,
      folosind conversia convert_cm_to_px.
      - Pentru imaginea mozaic (64x64 marcate, redimensionată la 512x512), face același lucru.
      - În ambele cazuri, se adaugă în colțurile imaginii coordonatele pixel (cu font magenta).
      - Cele două imagini sunt afișate simultan în ferestre separate.
    """
    # Capturează imaginea raw
    raw_img = capture_raw_image()
    # Convertim de la BGR la RGB
    raw_img = cv2.cvtColor(raw_img, cv2.COLOR_RGB2BGR)
    raw_overlay = raw_img.copy()
    
    # Procesăm mozaicul
    mosaic = create_64x64_mosaic(raw_img)
    mosaic_marked = mark_red_blocks_as_cyan(mosaic)
    mosaic_resized = cv2.resize(mosaic_marked, (512, 512), interpolation=cv2.INTER_NEAREST)
    mosaic_overlay = mosaic_resized.copy()
    
    # Definim vectorii pe x (în cm)
    vectors = {
        "A": -10,
        "B": -5,
        "O": 0,
        "C": 5,
        "D": 10
    }
    # y valorile de la 20 la -4 (pas de 1 cm)
    y_values = list(range(20, -5, -1))
    
    # Desenăm vectorii pe imaginea raw
    raw_overlay = draw_red_points(raw_overlay, vectors, y_values)
    raw_overlay = draw_yellow_stars(raw_overlay, vectors, y_values)
    raw_overlay = annotate_corners(raw_overlay)
    
    # Desenăm vectorii pe imaginea mozaic
    mosaic_overlay = draw_red_points(mosaic_overlay, vectors, y_values)
    mosaic_overlay = draw_yellow_stars(mosaic_overlay, vectors, y_values)
    mosaic_overlay = annotate_corners(mosaic_overlay)
    
    # Combinăm imaginile raw și mozaic în ferestre separate
    cv2.imshow("Raw Image - Vectori", raw_overlay)
    cv2.imshow("Mosaic Image - Vectori", mosaic_overlay)
    
    # Așteptăm apăsarea tastei 'q' pentru a închide ferestrele
    while True:
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
    cv2.destroyAllWindows()

if __name__ == "__main__":
    debug_vectors_on_images()
