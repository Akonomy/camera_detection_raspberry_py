#!/usr/bin/env python3
"""
Script: detect_rotated_parallelogram.py

Utilizare modulară:
  from detect_rotated_parallelogram import detect_rotated_lines_in_mosaic

  # Se presupune că 'image_copy' este deja obținută din alt modul (de exemplu, din camera)
  coords_cyan = detect_rotated_lines_in_mosaic(image_copy, debug=False)
  # coords_cyan va fi o listă de tuple (x_cm, y_cm) deduplicate
     pentru fiecare celulă detectată cu bloc cyan

Dacă debug=True, se vor afișa ferestrele OpenCV și interfețele Tkinter.
"""

import cv2
import numpy as np
import tkinter as tk
import math
from CAMERA.camera_session import capture_raw_image  # Se folosește doar pentru rularea standalone

### Funcții pentru conversie (corecție perspectivă) ###
def convert_px_to_cm(detected_x, detected_y):
    """
    Converteste coordonatele (detected_x, detected_y) din pixeli în coordonate reale (cm)
    folosind formulele empirice, apoi rotunjește rezultatul la cel mai apropiat 0.5 cm.
    
    Se inversează doar coordonata y:
      - Imaginea are 512 pixeli în înălțime.
      - Pentru un detected_y mic (susul imaginii) se obține un y mare,
        iar pentru detected_y mare (josul imaginii) y devine mic.
    """
    detected_y = 512 - detected_y
    real_y = 0.05587 * detected_y - 4.47

    center_x = 0.0203 * detected_y + 230.38
    scale_x = 0.0000608 * detected_y + 0.046936
    real_x = (detected_x - center_x) * scale_x

    real_x = round(real_x * 2) / 2
    real_y = round(real_y * 2) / 2

    return real_x, real_y

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
    """
    Parcurge mozaicul și pentru fiecare celulă care este cyan (0,255,255),
    calculează coordonatele centrale (în pixeli) și le convertește în cm.
    Returnează o listă de tuple (real_x, real_y).
    """
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

### Funcții pentru afișare (doar pentru debug) ###
def show_opencv_windows(raw_img, mosaic_64_marked, contours):
    block_size = 8
    out_bgr = cv2.cvtColor(raw_img, cv2.COLOR_RGB2BGR)
    for cnt in contours:
        area_64 = cv2.contourArea(cnt)
        if area_64 < 5:
            continue
        rect = cv2.minAreaRect(cnt)
        box_points = cv2.boxPoints(rect)
        box_points = np.int0(box_points)
        mapped_box = []
        for (mx, my) in box_points:
            mx = max(mx, 0)
            my = max(my, 0)
            X = mx * block_size
            Y = my * block_size
            mapped_box.append([X, Y])
        mapped_box = np.array(mapped_box, dtype=np.int32)
        cv2.polylines(out_bgr, [mapped_box], isClosed=True, color=(0, 0, 255), thickness=3)

    mosaic_up = cv2.resize(mosaic_64_marked, (512, 512), interpolation=cv2.INTER_NEAREST)
    cv2.imshow("Original 512x512 (with rotated lines)", out_bgr)
    cv2.imshow("Mosaic 64x64 scaled", cv2.cvtColor(mosaic_up, cv2.COLOR_RGB2BGR))
    cv2.waitKey(1000)
    cv2.destroyAllWindows()

def show_tkinter_grid(mosaic, timeout=70000):
    import numpy as np
    import tkinter as tk

    cell_size = 10
    rows, cols, _ = mosaic.shape
    width = cols * cell_size
    height = rows * cell_size

    clicked_cells = {}
    root = tk.Tk()
    root.title("Grid 64x64 - Vedere NECorectată cu click")
    frame = tk.Frame(root)
    frame.pack(fill=tk.BOTH, expand=True)
    canvas = tk.Canvas(frame, width=width, height=height, bg="white")
    canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
    listbox = tk.Listbox(frame, height=6)
    listbox.pack(side=tk.BOTTOM, fill=tk.X)
    
    def draw_grid():
        canvas.delete("all")
        for i in range(rows):
            for j in range(cols):
                x0 = j * cell_size
                y0 = i * cell_size
                x1 = x0 + cell_size
                y1 = y0 + cell_size
                if (i, j) in clicked_cells:
                    fill_color = "green"
                else:
                    if (mosaic[i, j] == np.array([0, 255, 255])).all():
                        fill_color = "#00ffff"
                    else:
                        fill_color = "white"
                canvas.create_rectangle(x0, y0, x1, y1, fill=fill_color, outline="black")
        canvas.configure(scrollregion=canvas.bbox("all"))
    
    def on_cell_click(event):
        nonlocal cell_size
        j = event.x // cell_size
        i = event.y // cell_size
        if i < 0 or i >= rows or j < 0 or j >= cols:
            return
        detected_x = j * 8 + 4
        detected_y = i * 8 + 4
        real_x, real_y = convert_px_to_cm(detected_x, detected_y)
        coord_text = (f"Mozaic row {i}, Col {j} -> Detected: ({detected_x}, {detected_y}) | "
                      f"in cm: ({real_x}, {real_y})")
        if (i, j) not in clicked_cells:
            clicked_cells[(i, j)] = coord_text
            listbox.insert(tk.END, coord_text)
        draw_grid()
    
    def zoom(event):
        nonlocal cell_size
        if hasattr(event, "delta"):
            factor = 1.1 if event.delta > 0 else 0.9
        elif event.num == 4:
            factor = 1.1
        elif event.num == 5:
            factor = 0.9
        else:
            return
        cell_size = int(cell_size * factor)
        draw_grid()
    
    canvas.bind("<Button-1>", on_cell_click)
    canvas.bind("<Button-4>", zoom)
    canvas.bind("<Button-5>", zoom)
    canvas.bind("<MouseWheel>", zoom)
    
    draw_grid()
    root.after(timeout, root.destroy)
    root.mainloop()

def show_tkinter_cm_interface(cyan_coords, timeout=60000):
    """
    Deschide o interfață Tkinter cu gridul (1 cm x 1 cm) în care se colorează
    o singură celulă pentru fiecare coordonată (deduplicată) din lista de coordonate.
    """
    x_min, x_max = -25, 25
    y_min, y_max = -10, 30
    scale = 10
    canvas_width = (x_max - x_min) * scale
    canvas_height = (y_max - y_min) * scale

    def to_canvas_coords(real_x, real_y):
        canvas_x = (real_x - x_min) * scale
        canvas_y = canvas_height - (real_y - y_min) * scale
        return canvas_x, canvas_y

    root = tk.Tk()
    root.title("Coordonate în cm - Blocuri Cyan")
    canvas = tk.Canvas(root, width=canvas_width, height=canvas_height, bg="white")
    canvas.pack()

    for x in range(x_min, x_max + 1,5):
        cx, _ = to_canvas_coords(x, y_min)
        canvas.create_line(cx, 0, cx, canvas_height, fill="lightgray")
        canvas.create_text(cx, canvas_height - 10, text=str(x), fill="black", font=("Arial", 10))
    for y in range(y_min, y_max + 1, 5):
        _, cy = to_canvas_coords(x_min, y)
        canvas.create_line(0, cy, canvas_width, cy, fill="lightgray")
        canvas.create_text(20, cy, text=str(y), fill="black", font=("Arial", 10))
    cx0, _ = to_canvas_coords(0, y_min)
    canvas.create_line(cx0, 0, cx0, canvas_height, fill="black", width=2)
    _, cy0 = to_canvas_coords(x_min, 0)
    canvas.create_line(0, cy0, canvas_width, cy0, fill="black", width=2)

    # Deduplicare similară: se calculează celulele unice (snap la număr întreg)
    colored_cells = set()
    for (real_x, real_y) in cyan_coords:
        grid_x = round(real_x)
        grid_y = round(real_y)
        if grid_x < x_min or grid_x >= x_max or grid_y < y_min or grid_y >= y_max:
            continue
        colored_cells.add((grid_x, grid_y))

    for (grid_x, grid_y) in colored_cells:
        left = grid_x
        right = grid_x + 1
        bottom = grid_y
        top = grid_y + 1
        cx1, cy1 = to_canvas_coords(left, top)
        cx2, cy2 = to_canvas_coords(right, bottom)
        canvas.create_rectangle(cx1, cy1, cx2, cy2, fill="#00ffff", outline="black")

    root.after(timeout, root.destroy)
    root.mainloop()

### Funcția principală modificată ###
def detect_rotated_lines_in_mosaic(image_copy, debug=False):
    """
    Procesează o imagine preluată ca parametru pentru a detecta blocurile roșii/cyan,
    efectuează conversia în coordonate (cm) și deduplicatează rezultatul, astfel încât
    dacă mai multe blocuri se mapează la aceeași celulă, se returnează o singură coordonată.
    
    Dacă debug=True, se afișează ferestrele OpenCV și interfețele Tkinter.
    
    Parametru:
      - image_copy: O copie a imaginii (preprocesată, de dimensiune 512x512) care va fi folosită pentru procesare.
    
    Returnează:
      - o listă de tuple (x_cm, y_cm) deduplicate.
    """
    mosaic_64 = create_64x64_mosaic(image_copy)
    mosaic_64_marked = mark_red_blocks_as_cyan(mosaic_64)

    mask_cyan = np.zeros((64, 64), dtype=np.uint8)
    cyan_pixels = ((mosaic_64_marked[:,:,0] == 0) &
                   (mosaic_64_marked[:,:,1] == 255) &
                   (mosaic_64_marked[:,:,2] == 255))
    mask_cyan[cyan_pixels] = 255
    contours, _ = cv2.findContours(mask_cyan, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if debug:
        show_opencv_windows(image_copy, mosaic_64_marked, contours)
        show_tkinter_grid(mosaic_64_marked, timeout=70000)
    
    cyan_coords = get_cyan_block_coordinates(mosaic_64_marked)

    # Aplicăm deduplicarea: "snap-uim" fiecare coordonată la cel mai apropiat număr întreg
    deduped_coords = {(round(x), round(y)) for (x, y) in cyan_coords}
    deduped_coords = list(deduped_coords)

    if debug:
        show_tkinter_cm_interface(deduped_coords, timeout=60000)

    return cyan_coords

### Exemplu de rulare standalone ###
if __name__ == "__main__":
    try:
        raw_img = capture_raw_image()  # Capturează o imagine (512x512) folosind modulul de cameră
        coords = detect_rotated_lines_in_mosaic(raw_img, debug=True)
        print("Coordonate (cm) detectate (deduplicate):", coords)
    except KeyboardInterrupt:
        pass
