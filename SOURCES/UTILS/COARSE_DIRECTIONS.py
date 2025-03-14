#!/usr/bin/env python3
"""
Noua implementare a generatorului de comenzi
folosind exclusiv noile date.

Funcțiile principale:
  - getAllCommands(x_cm, y_cm) -> listă de comenzi
       Fiecare comandă este un tuple: (1, tick, direction, speed_vector)
  - getFirstCommand(x_cm, y_cm) -> returnează doar prima comandă din listă

Reguli:
  - x < 0  => mișcare laterală spre dreapta (direction 10)
  - x > 0  => mișcare laterală spre stânga  (direction 9)
  - y > 0  => mișcare înainte (direction 1)
  - y < 0  => mișcare înapoi  (direction 2)
  
Pentru mișcarea înainte/înapoi se alege o comandă cu distanţa maximă ce nu depăşeşte
valoarea țintă (nu se permite overshoot). Pentru mișcările laterale, se selectează candidatul
cea mai apropiat de valoarea dorită (chiar dacă se depăşeşte).
"""

# --- Noile date pentru mișcarea înainte (și, implicit, pentru backward) ---
# Fiecare tuple este de forma: (tick, speed, distance) 

#-----------<  TESTATE LA 8 VOLTI  >--------------------


forward_commands = [
    (1, 100, 2.0),
    (2, 100, 2.5),
    (3, 100, 6.0),
    (3, 100, 5.5),
    (4, 100, 8.5),
    (6, 100, 14.5),
    (7, 100, 17.0),
    (8, 100, 20.0),
    (8, 100, 20.0),
    (1, 120, 3.0),
    (2, 120, 4.5),
    (3, 120, 8.0),
    (3, 120, 8.0),
    (4, 120, 10.5),
    (5, 120, 14.0),
    (6, 120, 17.0),
    (7, 120, 20.5),
    (1, 160, 4.5),
    (2, 160, 6.5),
    (3, 160, 10.5),
    (4, 160, 14.5),
    (5, 160, 18.0),
    (6, 160, 22.0),
    (1, 180, 5.0),
    (2, 180, 7.0),
    (3, 180, 11.5),
    (4, 180, 16.0),
    (5, 180, 20.0),
    (1, 190, 5.5),
    (2, 190, 7.5),
    (3, 190, 12.0),
    (4, 190, 16.5),
    (1, 95, 2.0),
    (1, 88, 1.5),
    (1, 80, 1.0)
]



old_forward_commands = [
    (1, 100 , 1 ),
    (1, 105, 1.5),
    (3, 100, 4.0),
    (5, 100, 9.5),
    (6, 100, 12.0),
    (7, 100, 14.5),
    (1, 130, 3.0),
    (2, 130, 4.0),
    (3, 130, 7.0),
    (4, 130, 10.7),
    (5, 130, 13.0),
    (6, 130, 16.0),
    (7, 130, 19.5),
    (8, 130, 22.0),
    (1, 140, 3.0),
    (2, 140, 4.0),
    (3, 140, 7.0),
    (4, 140, 11.0),
    (5, 140, 14.5),
    (1, 160, 4.0),
    (2, 160, 6.0),
    (3, 160, 9.0),
    (4, 160, 12.5),
    (5, 160, 16.0),
    (6, 160, 19.5),
    (3, 180, 10.0),
    (4, 180, 14.0),
    (5, 180, 18.0),
    (1, 135, 2.5),
    (1, 130, 2.0),
    (2, 160, 5.0),
    (3, 150, 8.0)
]




# --- Noile date pentru mișcarea laterală spre dreapta ---
# Fiecare tuple este: (tick, speed_vector, distance)
side_right_commands = [
    (10, [167, 169, 185, 194], 18.0),
    (9,  [167, 169, 185, 194], 15.5),
    (8,  [167, 169, 185, 194], 14.5),
    (7,  [167, 169, 185, 194], 14.5),
    (7,  [167, 169, 185, 194], 12.0),
    (6,  [167, 169, 185, 194], 10.0),
    (5,  [167, 169, 185, 194], 8.0),
    (4,  [167, 169, 185, 194], 6.5),
    (3,  [167, 169, 185, 194], 4.0),
    (2,  [167, 169, 185, 194], 3.0),
    (1,  [167, 169, 185, 194], 2.0)
]

# --- Noile date pentru mișcarea laterală spre stânga ---
# Am combinat două grupuri de date într-o singură listă
# Fiecare tuple este: (tick, speed_vector, distance)
side_left_commands = [
    (1,  [168, 158, 166, 161], 1.5),
    (2,  [168, 158, 166, 161], 2.5),
    (1,  [191, 180, 187, 176], 2.0),
    (2,  [191, 180, 187, 176], 3.0),
    (3,  [191, 180, 187, 176], 5.0),
    (4,  [191, 180, 187, 176], 8.5),
    (5,  [191, 180, 187, 176], 10.0),
    (6,  [191, 180, 187, 176], 13.0),
    (7,  [191, 180, 187, 176], 15.5),
    (8,  [191, 180, 187, 176], 18.0),
    (9,  [191, 180, 187, 176], 19.5),
    (10, [191, 180, 187, 176], 23.5)
]

# --- Funcții helper pentru selectarea celui mai bun candidat ---

def find_best_forward_command(target_distance: float):
    """
    Selectează comanda din forward_commands cu distanţa maximă care nu depăşeşte target_distance.
    Returnează un tuple: (tick, speed, distance) sau None dacă nu există candidat.
    """
    valid = [cmd for cmd in forward_commands if cmd[2] <= target_distance]
    if not valid:
        return None
    # Alege comanda cu distanţa maximă (cea mai aproape de target, fără overshoot)
    best = max(valid, key=lambda x: x[2])
    return best

def find_best_side_command(target_distance: float, side: str):
    """
    Pentru mișcarea laterală, selectează candidatul din lista corespunzătoare
    cu distanţa cea mai apropiată de target_distance (overshoot permis).
    Parametrul side poate fi "right" sau "left".
    Returnează un tuple: (tick, speed_vector, distance) sau None.
    """
    if side == "right":
        candidates = side_right_commands
    elif side == "left":
        candidates = side_left_commands
    else:
        return None
    # Alege candidatul cu diferenţa minimă faţă de target_distance (absolute)
    best = min(candidates, key=lambda x: abs(x[2] - target_distance))
    return best

def find_best_backward_command(target_distance: float):
    """
    Pentru backward se foloseşte aceeaşi logică ca pentru forward,
    dar comanda va fi modificată să aibă direcţia 2.
    Returnează un tuple: (tick, speed, distance) sau None.
    """
    return find_best_forward_command(target_distance)

# --- Funcțiile principale ---

def getAllCommands(x_cm: float, y_cm: float):
    """
    Primeşte coordonatele țintă (x, y) în cm și returnează o listă de comenzi,
    fiecare sub forma (1, tick, direction, speed_vector) potrivită pentru funcția process_command.
    
    Prioritate:
      1. Dacă y < 0: se adaugă comanda backward (folosind forward_commands, cu direction = 2)
      2. Dacă |x| > 0.5: se adaugă comanda laterală:
           x < 0  => side right (direction = 10)
           x > 0  => side left  (direction = 9)
      3. Dacă y > 0: se adaugă comanda forward (direction = 1)
    """
    commands = []
    
    # 1) Mișcare înapoi (y negativ)
    if y_cm < 0:
        candidate = find_best_backward_command(abs(y_cm))
        if candidate is not None:
            tick, speed, _ = candidate
            # Pentru backward, se foloseşte acelaşi speed, dar direction devine 2;
            # speed_vector se transmite ca listă (mod uniform)
            commands.append((1, tick, 2, [speed]))
        y_cm = 0

    # 2) Mișcare laterală
    if abs(x_cm) > 0.5:
        if x_cm < 0:
            candidate = find_best_side_command(abs(x_cm), "right")
            if candidate is not None:
                tick, speed_vector, _ = candidate
                commands.append((1, tick, 10, speed_vector))
        else:
            candidate = find_best_side_command(abs(x_cm), "left")
            if candidate is not None:
                tick, speed_vector, _ = candidate
                commands.append((1, tick, 9, speed_vector))
        x_cm = 0

    # 3) Mișcare înainte (y pozitiv)
    if y_cm > 0.5:
        candidate = find_best_forward_command(y_cm)
        if candidate is not None:
            tick, speed, _ = candidate
            commands.append((1, tick, 1, [speed]))
        y_cm = 0

    return commands

def getFirstCommand(x_cm: float, y_cm: float):
    """
    Returnează doar prima comandă din secvenţa generată de getAllCommands.
    Dacă nu există nicio comandă, returnează (0, 0, 0, []).
    """
    cmds = getAllCommands(x_cm, y_cm)
    if cmds:
        return cmds[0]
    return (0, 0, 0, [])

# --- Exemplu de testare ---
if __name__ == "__main__":
    # Exemplu 1: (x, y) = (-10, 0) => mișcare laterală spre dreapta pentru 10 cm
    cmds1 = getAllCommands(-10.0, 0.0)
    print("Comenzi pentru (-10, 0):", cmds1)
    
    # Exemplu 2: (x, y) = (10, 21) => mișcare laterală spre stânga pentru 10 cm, apoi înainte pentru 21 cm
    cmds2 = getAllCommands(10.0, 21.0)
    print("Comenzi pentru (10, 21):", cmds2)
    
    # Exemplu 3: (x, y) = (0, -15) => mișcare înapoi pentru 15 cm
    cmds3 = getAllCommands(0, -15.0)
    print("Comenzi pentru (0, -15):", cmds3)
    
    # Prima comandă pentru (10, 21)
    first_cmd = getFirstCommand(10.0, 21.0)
    print("Prima comandă pentru (10, 21):", first_cmd)
