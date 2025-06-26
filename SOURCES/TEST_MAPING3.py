#!/usr/bin/env python3
import tkinter as tk
from CAMERA.camera_session import capture_raw_image, init_camera
from ZONE_DETECT.get_zone import detect_zone

def display_hull(hull, canvas_width=600, canvas_height=600, cm_scale=10):
    """
    Desenează hull-ul primit (în cm) pe un canvas Tkinter unde (0,0) este în centru.
    
    Parametri:
      - hull: listă de tuple (x, y) în cm (adaptate, adică 1:1 în sistemul de coordonate cm).
      - canvas_width, canvas_height: dimensiunile canvas-ului (în pixeli).
      - cm_scale: factorul de scalare (ex. 10 pixeli pe cm).
    """
    # Pentru un canvas de 60x60 cm, centrul în cm este la (30, 30)
    def cm_to_canvas(x, y):
        # Mutăm originea (0,0) în centrul canvas-ului:
        cx = (x + 30) * cm_scale
        cy = (15+y) * cm_scale
        return cx, cy

    root = tk.Tk()
    root.title("Display Hull (Coordonate cm, 1:1)")
    canvas = tk.Canvas(root, width=canvas_width, height=canvas_height, bg="white")
    canvas.pack()

    # (Opțional) Desenăm grila
    for i in range(0, 61):
        x_line = i * cm_scale
        canvas.create_line(x_line, 0, x_line, canvas_height, fill="#e0e0e0")
    for i in range(0, 61):
        y_line = i * cm_scale
        canvas.create_line(0, y_line, canvas_width, y_line, fill="#e0e0e0")
    
    # Desenăm poligonul hull, dacă este valid
    if hull and len(hull) >= 3:
        points = []
        for (x, y) in hull:
            cx, cy = cm_to_canvas(x, y)
            points.extend([cx, cy])
        canvas.create_polygon(points, outline="blue", fill="", width=2)
    else:
        canvas.create_text(canvas_width/2, canvas_height/2, text="Hull invalid", fill="red", font=("Arial", 16))

    root.mainloop()


def main():
    # Capturează o imagine (512x512)
    init_camera()

    image_copy = capture_raw_image()
    
    # Apelăm detect_zone cu debug=False pentru a nu afișa interfața inițială
    limits, flags, hull = detect_zone(image_copy, debug=False)
    
    print("Limitele zonei:", limits)
    print("Rezultatul verificării pozițiilor:", flags)
    
    # Desenăm hull-ul primit într-o interfață Tkinter separată
    display_hull(hull)

if __name__ == "__main__":
    main()
