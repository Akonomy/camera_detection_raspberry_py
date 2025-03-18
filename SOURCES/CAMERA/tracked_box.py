#!/usr/bin/env python3
"""
Module: tracked_box.py
Descriere: Acest modul primește un dicționar de sesiune (cutii detectate)
și, folosind o logică de selecție, returnează cutia considerată "tracked" (urmărită).
Dacă se furnizează un target_box_id și acesta se găsește în sesiune,
se returnează acel box; altfel, se alege cel mai apropiat de centru.
"""

import math

def select_best_candidate(boxes):
    """
    Selectează cel mai potrivit candidat din dicționarul de cutii.
    Se presupune că fiecare cutie are cel puțin:
      - "real_position": tuple (x, y)
    Candidatul ales este cel cu cea mai mică distanță față de origine (0,0).
    
    Returnează un tuple (candidate_id, candidate_box).
    """
    best_candidate_id = None
    best_candidate = None
    best_dist = float('inf')
    for box_id, box in boxes.items():
        # Dacă nu există "real_position", încercăm să folosim "position"
        pos = box.get("real_position", box.get("position", (0, 0)))
        x, y = pos
        d = math.sqrt(x * x + y * y)
        if d < best_dist:
            best_candidate_id = box_id
            best_candidate = box
            best_dist = d
    return best_candidate_id, best_candidate

def get_tracked_box(session_data, target_box_id=None):
    """
    Primește dicționarul de sesiune (cutii detectate) și opțional un target_box_id.
    Dacă target_box_id este furnizat și se găsește în sesiune, returnează acel box.
    Altfel, folosește select_best_candidate pentru a alege cutia trackată.
    
    Returnează cutia trackată (un dicționar cu date despre cutie) sau None dacă nu există date.
    """
    if not session_data:
        return None
    if target_box_id is not None and target_box_id in session_data:
        return session_data[target_box_id]
    else:
        _, candidate = select_best_candidate(session_data)
        return candidate

if __name__ == "__main__":
    # Exemplu de test
    test_session = {
        "BlueK": {"real_position": (250, 150), "box_color": "Blue", "letters": ["K"], "size": (50, 60)},
        "RedO": {"real_position": (300, 200), "box_color": "Red", "letters": ["O"], "size": (60, 70)},
        "GreenA": {"real_position": (200, 100), "box_color": "Green", "letters": ["A"], "size": (40, 50)}
    }
    tracked = get_tracked_box(test_session, target_box_id="BlueK")
    print("Tracked box:", tracked)

