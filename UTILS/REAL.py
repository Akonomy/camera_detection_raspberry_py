#!/usr/bin/env python3
"""
Module: real_coordinate_converter
Descriere: Funcții de conversie a coordonatelor detectate (x, y) din imagine în coordonate reale (cm),
           bazate pe o calibrare (exemplificată cu datele colectate) și generarea instrucțiunilor de deplasare.
"""

def round_to_half(value):
    """Rotunjește valoarea la cel mai apropiat 0.5 cm."""
    return round(value * 2) / 2

# Funcții de conversie pentru axa Y
def get_real_y(detected_y):
    """
    Conversia pentru axa y.
    Pe baza datelor calibrate:
      - detected_y = 80  => real_y ≈ 0
      - detected_y = 474 => real_y ≈ 22.0
    Formula aleasă:
      real_y = 0.05587 * detected_y - 4.47
    """
    return 0.05587 * detected_y - 4.47

# Funcții de conversie pentru axa X
def get_center_x(detected_y):
    """
    Calculează coordonata de centru (pentru slotul central, unde real_x = 0)
    Pe baza datelor calibrate:
      - detected_y = 80  => center_x ≈ 232
      - detected_y = 474 => center_x ≈ 240
    Formula aleasă:
      center_x = 0.0203 * detected_y + 230.38
    """
    return 0.0203 * detected_y + 230.38

def get_scale_x(detected_y):
    """
    Factorul de scalare pentru transformarea abaterii față de centru în real_x.
    Se calculează pe baza datelor calibrate:
      - La low y: scale_x ≈ 10 / 193 ≈ 0.0518
      - La high y: scale_x ≈ 10 / 132 ≈ 0.0758
    Formula aleasă:
      scale_x = 0.0000608 * detected_y + 0.046936
    """
    return 0.0000608 * detected_y + 0.046936

def getRealCoordinates(detected_x, detected_y):
    """
    Primește coordonatele detectate din imagine (detected_x, detected_y) și
    returnează o tuplă (real_x, real_y) în centimetri, rotunjite la cel mai apropiat 0.5 cm.
    
    Nota:
      - real_x este calculat astfel încât valorile negative indică poziții la dreapta (ex: -10 cm)
        și valorile pozitive la stânga (ex: +10 cm), conform convenției tale.
      - real_y se interpretează ca distanță față de centrul mașinii.
    """
    center_x = get_center_x(detected_y)
    scale_x = get_scale_x(detected_y)
    
    # Calculul real_x: diferența de la centru, scalată
    real_x = (detected_x - center_x) * scale_x
    
    # Calculul real_y
    real_y = get_real_y(detected_y)
    
    # Rotunjire la cel mai apropiat 0.5
    real_x = round_to_half(real_x)
    real_y = round_to_half(real_y)
    
    return real_x, real_y

def getMovementInstructions(detected_x, detected_y):
    """
    Pe baza coordonatelor detectate se generează instrucțiuni de deplasare.
    Returnează o tuplă (x_instruction, y_instruction):
      - Pentru x: dacă real_x < 0, se recomandă deplasare spre dreapta cu |real_x| cm;
               dacă real_x > 0, deplasare spre stânga cu real_x cm.
      - Pentru y: dacă real_y > 0, se recomandă deplasare înainte cu real_y cm;
                 dacă real_y < 0, deplasare înapoi cu |real_y| cm.
    """
    real_x, real_y = getRealCoordinates(detected_x, detected_y)
    
    # Instrucțiuni pentru axa X
    if real_x < 0:
        x_instruction = f"Move {abs(real_x)} cm to the RIGHT"
    elif real_x > 0:
        x_instruction = f"Move {real_x} cm to the LEFT"
    else:
        x_instruction = "No lateral movement needed"
    
    # Instrucțiuni pentru axa Y
    if real_y > 0:
        y_instruction = f"Move {real_y} cm FORWARD"
    elif real_y < 0:
        y_instruction = f"Move {abs(real_y)} cm BACKWARD"
    else:
        y_instruction = "No forward/backward movement needed"
    
    return x_instruction, y_instruction

# Exemplu de utilizare (doar pentru testare; se poate rula dacă modulul este rulat ca script principal)
if __name__ == '__main__':
    # Exemplu: coordonate detectate (de la imagine)
    test_points = [
        (44, 81),
        (232, 81),
        (430, 81),
        (44, 400),
        (240, 400),
        (430, 400)
    ]
    for (dx, dy) in test_points:
        real_coords = getRealCoordinates(dx, dy)
        instructions = getMovementInstructions(dx, dy)
        print(f"Detected: (x={dx}, y={dy}) -> Real: {real_coords} cm")
        print("Instructions:", instructions)
        print("-" * 50)
