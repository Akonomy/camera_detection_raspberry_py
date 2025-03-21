#!/usr/bin/env python3
import cv2
import math
from CAMERA.camera_session import capture_raw_image

def convert_px_to_cm(detected_x, detected_y):
    """
    Converteste coordonatele (detected_x, detected_y) din pixeli în coordonate reale (cm)
    folosind formule empirice, apoi rotunjește rezultatul la cel puțin 0.5 cm.
    Se inversează doar coordonata y.
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
    Calculul se face după:
      detected_y' = (real_y + 4.47) / 0.05587, apoi detected_y = 512 - detected_y'
      center_x = 0.0203 * detected_y' + 230.38
      scale_x = 0.0000608 * detected_y' + 0.046936
      și detected_x = real_x / scale_x + center_x.
    Returnează coordonatele în pixeli (rotunjite la întreg).
    """
    detected_y_prime = (real_y + 4.47) / 0.05587
    detected_y = 512 - detected_y_prime

    center_x = 0.0203 * detected_y_prime + 230.38
    scale_x = 0.0000608 * detected_y_prime + 0.046936

    detected_x = real_x / scale_x + center_x

    return int(round(detected_x)), int(round(detected_y))

# Funcția din MAP – aici folosim o scalare fixă (1 cm = 10 pixeli)
PIXELS_PER_CM = 10
def simple_cm_to_px(real_x, real_y):
    """
    Conversia simplă din cm în pixeli, presupunând că 1 cm = 10 pixeli.
    Pentru a alinia cu sistemul din convert_cm_to_px, folosim același offset pentru (0,0).
    În testul anterior, convert_cm_to_px(0,0) produce aproximativ (232,432) pixeli.
    Astfel, definim offset: offset_x = 232, offset_y = 432.
    """
    offset_x, offset_y = 232, 432
    # Pentru x: pixel = offset_x + (real_x * PIXELS_PER_CM)
    # Pentru y: pixel = offset_y - (real_y * PIXELS_PER_CM)
    return int(round(real_x * PIXELS_PER_CM + offset_x)), int(round(offset_y - real_y * PIXELS_PER_CM))

def debug_vectors_comparison():
    """
    Capturează o imagine 512x512 și desenează pe ea vectorii de puncte verticali pentru
    cinci seturi de coordonate pe axa x (în cm): A: -10, B: -5, O: 0, C: 5, D: 10.
    Pentru fiecare vector, punctele sunt generate din y=20 până la y=-4, cu pas 1 cm.
    
    Pentru fiecare punct, se calculează două conversii:
      - Conversia "RED": folosind convert_cm_to_px (inversul funcției convert_px_to_cm)
      - Conversia "YELLOW": folosind simple_cm_to_px (1 cm = 10 pixeli + offset fix)
    
    Se desenează cercuri roșii (etichete cu "R") și cercuri galbene (etichete cu "Y") pentru a compara rezultatele.
    """
    image = capture_raw_image()  # imaginea este 512x512
    overlay = image.copy()

    # Definim vectorii de interes (valori de x în cm)
    vectors = {
        "A": -10,
        "B": -5,
        "O": 0,
        "C": 5,
        "D": 10
    }
    # Valorile de y de la 20 la -4 (pas de -1, deci 20, 19, ..., -4)
    y_values = list(range(20, -5, -1))

    for label, x_cm in vectors.items():
        for idx, y_cm in enumerate(y_values):
            # Conversia folosind funcția convert_cm_to_px (RED)
            px_red, py_red = convert_cm_to_px(x_cm, y_cm)
            # Conversia folosind funcția simple_cm_to_px (YELLOW)
            px_yellow, py_yellow = simple_cm_to_px(x_cm, y_cm)
            # Desenăm cercuri: roșu pentru "RED", galben pentru "YELLOW"
            cv2.circle(overlay, (px_red, py_red), 3, (0, 0, 255), -1)
            cv2.circle(overlay, (px_yellow, py_yellow), 3, (0, 255, 255), -1)
            # Adăugăm etichete: eticheta se va afișa pentru fiecare conversie
            cv2.putText(overlay, f"{label}R{idx}", (px_red + 4, py_red - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            cv2.putText(overlay, f"{label}Y{idx}", (px_yellow + 4, py_yellow - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    
    cv2.imshow("Debug Vectors Comparison", overlay)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    debug_vectors_comparison()
