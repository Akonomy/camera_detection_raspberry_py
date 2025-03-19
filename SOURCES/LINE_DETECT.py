#!/usr/bin/env python3
"""
Script: color_mosaic_64x64_mark_red_as_cyan.py

Descriere:
  1) Obține imaginea 512x512 (RGB) de la cameră cu capture_raw_image().
  2) Creează o imagine 64x64 (mosaic_64), unde fiecare pixel reprezintă
     media de culoare a unui bloc 8x8 din original.
  3) Convertim mozaicul 64x64 la HSV, detectăm blocurile roșii
     și le înlocuim cu culoarea cyan (turcoaz).
  4) Redimensionăm mozaicul la 512x512 pentru a-l afișa mai clar
     (fără a pierde „blocurile”).
  5) Afișăm atât imaginea originală, cât și mozaicul cu blocuri marcate în cyan.
"""

import cv2
import numpy as np
from CAMERA.camera_session import capture_raw_image

def create_64x64_mosaic():
    """
    Construiește o imagine 64x64, fiecare pixel fiind media de culoare
    a unui bloc 8x8 din imaginea originală (512x512, RGB).
    Returnează:
      - raw_img: imaginea originală (512x512, RGB)
      - mosaic_64: imaginea mozaic (64x64, RGB)
    """
    raw_img = capture_raw_image()  # 512x512, RGB
    h, w, c = raw_img.shape
    if (h != 512 or w != 512):
        print("Atenție: imaginea nu e 512x512. Continuăm oricum...")
    
    # Creăm mozaicul 64x64
    mosaic_64 = np.zeros((64, 64, 3), dtype=np.uint8)
    block_size = 8  # 512 / 64
    
    for row in range(64):
        for col in range(64):
            # coordonatele blocului în original
            y_start = row * block_size
            y_end   = (row + 1) * block_size
            x_start = col * block_size
            x_end   = (col + 1) * block_size
            
            # extragem blocul 8x8
            block = raw_img[y_start:y_end, x_start:x_end]
            # media de culoare (R, G, B) -> convertim la uint8
            mean_color = block.mean(axis=(0, 1)).astype(np.uint8)
            mosaic_64[row, col] = mean_color
    
    return raw_img, mosaic_64

def mark_red_blocks_as_cyan(mosaic_64):
    """
    Primește mozaicul 64x64 (RGB).
    Convertește la HSV, detectează blocurile roșii și le înlocuiește cu (0,255,255) (cyan în RGB).
    Returnează mozaicul modificat.
    """
    # Copie, ca să nu alterăm direct mosaic_64
    mosaic_64_marked = mosaic_64.copy()
    
    # Convertim mozaicul la HSV
    hsv = cv2.cvtColor(mosaic_64_marked, cv2.COLOR_RGB2HSV)
    
    # Definim intervalele pentru roșu (mai permisive, ajustează la nevoie)
    lower_red1 = np.array([0, 80, 80])
    upper_red1 = np.array([15, 255, 255])
    lower_red2 = np.array([160, 80, 80])
    upper_red2 = np.array([180, 255, 255])
    
    lower_pink = np.array([140, 70, 70])  # ~H=140 => un roz-mov
    upper_pink = np.array([170, 255, 255])

    
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    red_mask = mask1 | mask2  # blocurile considerate roșii
    
    
    
    mask_pink = cv2.inRange(hsv, lower_pink, upper_pink)
    
    final_mask = red_mask | mask_pink
    
    # Unde masca e 255 (roșu), punem (0,255,255) = cyan în RGB
    # Atenție: mosaic_64_marked e tot în RGB
    mosaic_64_marked[final_mask == 255] = (0, 255, 255)
    
    return mosaic_64_marked

def show_mosaic_64x64_with_cyan_red():
    # 1) Construim mozaicul
    raw_img, mosaic_64 = create_64x64_mosaic()
    
    # 2) Marcăm blocurile roșii drept cyan
    mosaic_64_marked = mark_red_blocks_as_cyan(mosaic_64)
    
    # 3) Redimensionăm mozaicul la 512x512, folosind INTER_NEAREST
    #    ca să vedem blocurile ca pătrate mari.
    mosaic_up = cv2.resize(mosaic_64_marked, (512, 512), interpolation=cv2.INTER_NEAREST)
    
    # 4) Afișăm
    cv2.imshow("Original 512x512", cv2.cvtColor(raw_img, cv2.COLOR_RGB2BGR))
    cv2.imshow("Mosaic 64x64 (marcat)", cv2.cvtColor(mosaic_64_marked, cv2.COLOR_RGB2BGR))
    cv2.imshow("Mosaic 64x64 scaled to 512x512", cv2.cvtColor(mosaic_up, cv2.COLOR_RGB2BGR))
    
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    show_mosaic_64x64_with_cyan_red()
