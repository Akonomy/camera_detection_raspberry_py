#!/usr/bin/env python3
"""
Module: movement_command_generator

Acest modul primește o poziție țintă (x, y) în cm și generează comenzi
pentru robot (directie, ticks, speed) pe baza tabelelor de deplasare
laterală și înainte/înapoi, cu regulile:
 - x < 0 => dreapta (10)
 - x > 0 => stânga  (9)
 - y > 0 => înainte (1)
 - y < 0 => înapoi  (2)
 - la deplasare laterală și înainte se evită overshoot,
 - la deplasare înapoi e permis overshoot.

Două funcții principale:
 - getAllCommands(x, y) -> listă cu (directie, ticks, speed, [adjust?])
 - getFirstCommand(x, y) -> doar prima comandă din listă
"""

from typing import List, Tuple

# ------------------------------------------------
# 1) Datele pentru deplasare laterală la dreapta
#    (cod directie = 10, speed = 70)
#    ticks : (distanta_cm, necesita_adjust)
# ------------------------------------------------
LATERAL_RIGHT_TABLE = {
    1:  (2.0,   False),
    2:  (3.5,   False),
    3:  (6.5,   False),
    4:  (8.5,   True),   # adjust
    5:  (12.0,  True),   # adjust
    6:  (15.0,  True),   # adjust
    7:  (18.0,  True),   # adjust
    8:  (20.0,  True),   # adjust
    9:  (24.0,  True),   # adjust
    10: (27.0,  True)    # adjust
}
LATERAL_RIGHT_SPEED = 70

# ------------------------------------------------
# 2) Datele pentru deplasare laterală la stânga
#    (cod directie = 9, speed = 70)
#    ticks : (distanta_cm, necesita_adjust)
# ------------------------------------------------
LATERAL_LEFT_TABLE = {
    1:  (2.0,   False),
    2:  (4.0,   False),
    3:  (6.5,   False),
    4:  (9.5,   False),
    5:  (12.5,  False),
    6:  (15.0,  False),
    7:  (18.0,  False),
    8:  (21.0,  False),
    9:  (25.0,  False),
    10: (27.0,  False)
}
LATERAL_LEFT_SPEED = 70

# ------------------------------------------------
# 3) Datele pentru deplasare înainte/înapoi
#    (cod directie = 1 pt înainte, 2 pt înapoi)
#    Avem un tablou: (ticks, speed) -> distanta
# ------------------------------------------------
FORWARD_BACKWARD_TABLE = {
    110: {1: 3.7,  2: 6.1,  3: 10.0, 4: 13.5,  5: 17.0},
    120: {1: 3.6,  2: 6.0,  3: 9.6,  4: 12.5,  5: 16.0},
    130: {1: 3.0,  2: 5.1,  3: 8.0,  4: 12.0,  5: 15.0},
    140: {1: 2.9,  2: 4.6,  3: 7.5,  4: 11.0,  5: 14.0},
    150: {1: 2.5,  2: 4.0,  3: 7.4,  4: 9.5,   5: 13.0},
    160: {1: 2.0,  2: 999,  3: 999,  4: 999,   5: 999},
    170: {1: 1.5,  2: 999,  3: 999,  4: 999,   5: 999},
    180: {1: 1.0,  2: 999,  3: 999,  4: 999,   5: 999},
}


# ------------------------------------------------
# Funcții ajutătoare pentru căutarea de combinații
# ------------------------------------------------

def find_lateral_commands(distance_cm: float, is_left: bool) -> List[Tuple[int, int, int, bool]]:
    """
    Găsește o secvență de comenzi (directie, ticks, speed, adjust_flag)
    pentru a parcurge `distance_cm` lateral, FĂRĂ overshoot.
    
    - is_left = True  => folosește LATERAL_LEFT_TABLE (cod directie = 9)
    - is_left = False => folosește LATERAL_RIGHT_TABLE (cod directie = 10)
    - speed = 70 (constant)
    
    Returnează o listă de comenzi (directie, ticks, speed, adjust).
    """
    if distance_cm <= 0:
        return []
    
    table = LATERAL_LEFT_TABLE if is_left else LATERAL_RIGHT_TABLE
    directie = 9 if is_left else 10
    speed = LATERAL_LEFT_SPEED if is_left else LATERAL_RIGHT_SPEED
    
    commands = []
    remaining = distance_cm
    
    # Strategie simplă: la fiecare pas, căutăm cea mai mare distanță <= remaining
    # (adică nu depășim niciodată).
    # Repetăm până epuizăm (sau aproape) distanța.
    while remaining > 0:
        best_tick = None
        best_dist = 0.0
        best_adjust = False
        
        for t, (dist, adj) in table.items():
            if dist <= remaining and dist > best_dist:
                best_dist = dist
                best_tick = t
                best_adjust = adj
        
        if best_tick is None:
            # Nu există niciun tick care să fie <= remaining => ieșim (nu putem avansa)
            break
        
        commands.append((directie, best_tick, speed, best_adjust))
        remaining -= best_dist
        
        # Dacă rămâne foarte puțin (sub 0.5 cm de ex.), putem opri
        if remaining < 0.5:
            break
    
    return commands

def find_forward_commands(distance_cm: float) -> List[Tuple[int, int, int, bool]]:
    """
    Găsește o secvență de comenzi (1 = înainte, ticks, speed, adjust=False mereu)
    pentru a parcurge `distance_cm` FĂRĂ overshoot.
    
    Returnează o listă de comenzi (directie=1, ticks, speed, adjust=False).
    """
    if distance_cm <= 0:
        return []
    
    commands = []
    remaining = distance_cm
    
    # Vom încerca o abordare simplă:
    #  1) căutăm un (ticks, speed) care să fie EXACT <= remaining și cât mai aproape de remaining.
    #  2) îl scădem și repetăm.
    while remaining > 0:
        best_speed = None
        best_ticks = None
        best_dist = 0.0
        
        for speed, ticks_map in FORWARD_BACKWARD_TABLE.items():
            for t, dist in ticks_map.items():
                if dist <= remaining and dist > best_dist:
                    best_dist = dist
                    best_speed = speed
                    best_ticks = t
        
        if best_ticks is None:
            # Nu putem găsi nimic <= remaining => ne oprim
            break
        
        commands.append((1, best_ticks, best_speed, False))
        remaining -= best_dist
        
        if remaining < 0.5:
            break
    
    return commands

def find_backward_commands(distance_cm: float) -> List[Tuple[int, int, int, bool]]:
    """
    Găsește o secvență de comenzi (2 = înapoi, ticks, speed, adjust=False)
    pentru a parcurge `distance_cm` CU overshoot PERMIS.
    Idea: dacă putem să facem un singur pas care să depășească distanța,
          e ok. Altfel, îl împărțim.
    """
    if distance_cm <= 0:
        return []
    
    commands = []
    remaining = distance_cm
    
    # Metodă: încercăm să găsim un singur (ticks, speed) care e >= distance_cm (overshoot).
    # Dacă nu găsim, facem sub-pasul cel mai mare < distance_cm, apoi repetăm.
    while remaining > 0:
        best_speed = None
        best_ticks = None
        # caut un dist <-> minim care e >= remaining
        # dacă nu găsesc, fac "cel mai mare sub remaining"
        exact_or_overshoot_found = False
        min_dist_above = 9999
        
        for speed, ticks_map in FORWARD_BACKWARD_TABLE.items():
            for t, dist in ticks_map.items():
                # Distanța dist >= remaining => overshoot ok
                if dist >= remaining and dist < min_dist_above:
                    min_dist_above = dist
                    best_speed = speed
                    best_ticks = t
                    exact_or_overshoot_found = True
        
        if exact_or_overshoot_found:
            # Avem un combo care overshoot-ează (sau e fix egal)
            commands.append((2, best_ticks, best_speed, False))
            break  # ne oprim, că e overshoot dorit
        else:
            # Nu există nimic >= remaining => luăm cel mai mare sub remaining
            best_dist = 0.0
            for speed, ticks_map in FORWARD_BACKWARD_TABLE.items():
                for t, dist in ticks_map.items():
                    if dist > best_dist and dist < remaining:
                        best_dist = dist
                        best_speed = speed
                        best_ticks = t
            if best_ticks is None:
                # nimic nu putem face
                break
            commands.append((2, best_ticks, best_speed, False))
            remaining -= best_dist
            
            if remaining < 0.5:
                break
    
    return commands

# ------------------------------------------------
# Funcțiile principale cerute
# ------------------------------------------------

def getAllCommands(x_cm: float, y_cm: float) -> List[Tuple[int, int, int, bool]]:
    """
    Returnează o listă de comenzi (directie, ticks, speed, adjust_flag)
    pentru a ajunge de la (0, 0) la (x_cm, y_cm).
    
    Reguli simple de prioritate:
     - Dacă y_cm < 0, deplasare înapoi prima.
     - Apoi deplasare laterală (x_cm).
     - Apoi deplasare înainte (dacă y_cm > 0 rămas).
    
    (Ajustarea fină a logicii se poate face după preferințe.)
    """
    commands = []
    
    # 1) Dacă y e negativ, ne deplasăm întâi înapoi
    if y_cm < 0:
        dist_back = abs(y_cm)
        back_cmds = find_backward_commands(dist_back)
        commands.extend(back_cmds)
        # setăm y_cm la 0 după deplasarea înapoi (am considerat că am rezolvat-l)
        y_cm = 0
    
    # 2) Deplasare laterală (dacă x e negativ => dreapta, x pozitiv => stânga)
    if abs(x_cm) > 0.5:
        if x_cm < 0:
            # dreapta
            dist_right = abs(x_cm)
            right_cmds = find_lateral_commands(dist_right, is_left=False)
            commands.extend(right_cmds)
        else:
            # stânga
            dist_left = abs(x_cm)
            left_cmds = find_lateral_commands(dist_left, is_left=True)
            commands.extend(left_cmds)
        # considerăm că x a fost rezolvat
        x_cm = 0
    
    # 3) Dacă mai rămâne y pozitiv, ne deplasăm înainte
    if y_cm > 0.5:
        forward_cmds = find_forward_commands(y_cm)
        commands.extend(forward_cmds)
        y_cm = 0

    modified_commands = [(1, *cmd) for cmd in commands]

    return modified_commands

def getFirstCommand(x_cm: float, y_cm: float) -> Tuple[int, int, int, bool]:
    """
    Returnează DOAR prima comandă din secvența generată de getAllCommands.
    Dacă nu există nicio comandă, întoarce (0, 0, 0, False).
    """
    all_cmds = getAllCommands(x_cm, y_cm)
    if len(all_cmds) > 0:
        return all_cmds[0]
    return (1, 0, 0, 0, False)  # nimic

# ------------------------------------------------
# Exemplu de test
# ------------------------------------------------
if __name__ == "__main__":
    # Exemplu 1: (x, y) = (-10, 0) => dreapta 10 cm
    cmds = getAllCommands(-10.0, 0.0)
    print("Exemplu: (-10.0, 0.0) =>", cmds)
    
    # Exemplu 2: (x, y) = (10, 21) => stânga 10 cm, apoi înainte 21 cm
    cmds2 = getAllCommands(10.0, 21.0)
    print("Exemplu: (10.0, 21.0) =>", cmds2)
    
    # Prima comandă
    first2 = getFirstCommand(10.0, 21.0)
    print("Prima comandă (10.0, 21.0) =>", first2)
