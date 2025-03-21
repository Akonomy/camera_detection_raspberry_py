#!/usr/bin/env python3
import cv2
from CAMERA.camera_session import capture_raw_image
import math

def convert_px_to_cm(detected_x, detected_y):
    """
    Converteste coordonatele (detected_x, detected_y) din pixeli în coordonate reale (cm)
    folosind formule empirice, apoi rotunjește rezultatul la cel puțin 0.5 cm.
    Se inversează doar coordonata y: 
      detected_y = 512 - detected_y.
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
    Pornind de la:
      real_y = 0.05587 * detected_y' - 4.47, unde detected_y' = 512 - detected_y,
    se deduce:
      detected_y' = (real_y + 4.47) / 0.05587, iar detected_y = 512 - detected_y'.
    Pentru x:
      center_x = 0.0203 * detected_y' + 230.38,
      scale_x = 0.0000608 * detected_y' + 0.046936,
      iar real_x = (detected_x - center_x) * scale_x.
    Invers:
      detected_x = real_x / scale_x + center_x.
    Returnează (detected_x, detected_y) în pixeli (rotunjite la întreg).
    """
    detected_y_prime = (real_y + 4.47) / 0.05587
    detected_y = 512 - detected_y_prime

    center_x = 0.0203 * detected_y_prime + 230.38
    scale_x = 0.0000608 * detected_y_prime + 0.046936

    detected_x = real_x / scale_x + center_x

    return int(round(detected_x)), int(round(detected_y))

def debug_vectors():
    """
    Capturează o imagine 512x512 de la cameră și desenează cinci vectori verticali de puncte,
    cu puncte la fiecare 1 cm în intervalul y din 20 până la -4, la poziții fixe pe x:
      - Vectorul A: x = -10 cm
      - Vectorul B: x = -5 cm
      - Vectorul O: x = 0 cm
      - Vectorul C: x = 5 cm
      - Vectorul D: x = 10 cm
    Fiecare punct este convertit în pixeli folosind convert_cm_to_px și etichetat cu litera vectorului
    urmată de indice (de la 0 în sus).
    """
    # Capturează imaginea 512x512
    image = capture_raw_image()
    overlay = image.copy()

    # Definim vectorii cu x fix în cm
    vectors = {
        "A": -10,
        "B": -5,
        "O": 0,
        "C": 5,
        "D": 10
    }
    # Vom genera puncte de la y=20 până la y=-4 (pas 1 cm)
    y_values = list(range(20, -5, -1))  # 20, 19, ..., -4

    # Pentru fiecare vector, desenăm punctele
    for label, x_cm in vectors.items():
        for idx, y_cm in enumerate(y_values):
            px, py = convert_cm_to_px(x_cm, y_cm)
            # Desenăm un cerc mic la poziția calculată
            cv2.circle(overlay, (px, py), 3, (0, 0, 255), -1)
            # Adăugăm eticheta: litera și indicele
            cv2.putText(overlay, f"{label}{idx}", (px + 4, py - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    
    cv2.imshow("Debug Vectors", overlay)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    debug_vectors()
