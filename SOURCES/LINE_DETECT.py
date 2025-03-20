#!/usr/bin/env python3
"""
Script: detect_rotated_parallelogram.py

Descriere pe scurt:
  1) Obținem imaginea raw (512x512) și construim mozaicul 64x64.
  2) Marcăm blocurile roșii cu cyan.
  3) În mozaic (64x64), construim o mască binară pentru cyan și găsim contururile.
  4) Pentru fiecare contur semnificativ, folosim cv2.minAreaRect + cv2.boxPoints
     ca să obținem un dreptunghi rotit (4 colțuri).
  5) Mapăm punctele la coordonatele 512x512 (înmulțim cu 8) și desenăm poligonul
     în imaginea originală.
"""

import cv2
import numpy as np
from CAMERA.camera_session import capture_raw_image

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
    """
    Convertește mozaicul la HSV, detectează blocurile roșii/roz
    și le înlocuiește cu (0,255,255) (cyan în RGB).
    """
    mosaic_64_marked = mosaic_64.copy()
    
    hsv = cv2.cvtColor(mosaic_64_marked, cv2.COLOR_RGB2HSV)
    
    # Interval roșu/roz (exemplu)
    lower_red1 = np.array([0, 80, 80])
    upper_red1 = np.array([15, 255, 255])
    lower_red2 = np.array([160, 80, 80])
    upper_red2 = np.array([180, 255, 255])
    
    # Interval roz (ex.)
    lower_pink = np.array([140, 70, 70])
    upper_pink = np.array([170, 255, 255])
    
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    red_mask = mask1 | mask2
    
    mask_pink = cv2.inRange(hsv, lower_pink, upper_pink)
    
    final_mask = red_mask | mask_pink
    
    # Marcăm cu (0,255,255) = cyan
    mosaic_64_marked[final_mask == 255] = (0, 255, 255)
    
    return mosaic_64_marked

def detect_rotated_lines_in_mosaic():
    # 1) Obținem imaginea 512x512 (RGB)
    raw_img = capture_raw_image()
    
    # 2) Creăm mozaicul 64x64
    mosaic_64 = create_64x64_mosaic(raw_img)
    
    # 3) Marcăm blocurile roșii cu cyan
    mosaic_64_marked = mark_red_blocks_as_cyan(mosaic_64)
    
    # 4) Construim masca binară pentru cyan
    mask_cyan = np.zeros((64, 64), dtype=np.uint8)
    # pixel = (0,255,255) => R=0, G=255, B=255
    cyan_pixels = ((mosaic_64_marked[:,:,0] == 0) &
                   (mosaic_64_marked[:,:,1] == 255) &
                   (mosaic_64_marked[:,:,2] == 255))
    mask_cyan[cyan_pixels] = 255
    
    # Găsim contururile
    contours, _ = cv2.findContours(mask_cyan, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # 5) Prelucrăm fiecare contur
    block_size = 8
    out_bgr = cv2.cvtColor(raw_img, cv2.COLOR_RGB2BGR)
    
    for cnt in contours:
        area_64 = cv2.contourArea(cnt)
        if area_64 < 5:
            continue  # ignorăm contururile prea mici
        
        # Folosim minAreaRect => (center, (width, height), angle)
        rect = cv2.minAreaRect(cnt)
        box_points = cv2.boxPoints(rect)  # 4 colțuri => float32 (x,y) în coordonate 64x64
        
        # Convertim la int
        box_points = np.int0(box_points)
        
        # Filtru opțional: un contur poate fi prea mic, chiar dacă area_64 > 5
        # Poți verifica min(lățime, înălțime) > 2, etc.
        
        # Mapăm colțurile la coordonate 512x512
        # Fiecare x,y => x*8, y*8
        mapped_box = []
        for (mx, my) in box_points:
            # Clamping, just in case
            if mx < 0: mx = 0
            if my < 0: my = 0
            X = mx * block_size
            Y = my * block_size
            mapped_box.append([X, Y])
        
        mapped_box = np.array(mapped_box, dtype=np.int32)
        
        # 6) Desenăm poligonul (paralelogram) în imaginea originală
        cv2.polylines(out_bgr, [mapped_box], isClosed=True, color=(0,0,255), thickness=3)
    
    # 7) Afișăm rezultatele
    mosaic_up = cv2.resize(mosaic_64_marked, (512, 512), interpolation=cv2.INTER_NEAREST)
    cv2.imshow("Original 512x512 (with rotated lines)", out_bgr)
    cv2.imshow("Mosaic 64x64 Marked", cv2.cvtColor(mosaic_64_marked, cv2.COLOR_RGB2BGR))
    cv2.imshow("Mosaic 64x64 scaled", cv2.cvtColor(mosaic_up, cv2.COLOR_RGB2BGR))
    cv2.imshow("Mask Cyan (64x64)", mask_cyan)
    
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    detect_rotated_lines_in_mosaic()
