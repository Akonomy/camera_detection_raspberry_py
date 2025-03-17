import math
import numpy as np

def determine_tracked_box(session_data, target_box=None, mandatory=False, zone_center=(247, 100)):
    """
    Determină cutia de urmărit și/sau cutia blocantă, pe baza informațiilor din sesiune,
    ținând cont de opțiunea *mandatory*:
    
    - Dacă *mandatory* este True, se dorește urmărirea unei cutii specifice (target).
      Dacă targetul este blocat (adică există alte cutii în fața lui în aceeași coloană),
      se returnează tot targetul (flag2=1) împreună cu lista cutiilor ce trebuie mutate
      (blocking_boxes) și nivelul de acces (numărul de cutii de mutat).
      
    - Dacă *mandatory* este False, nu se impune ca targetul să fie urmărit:
      • Dacă targetul există și este accesibil (index 0 în coloană), se urmărește targetul.
      • Dacă targetul este blocat (index > 0), se ignoră targetul și se alege cutia
        cea mai accesibilă din întreaga sesiune (calculată pe baza distanței față de centru).
    
    Returnează un tuple:
      (tracked_box_info, flag1, flag2, access_level, blocking_boxes)
      
      unde:
      - tracked_box_info: dict cu informații: "position", "distance", "box_color", "letter", "column"
      - flag1: 1 dacă a fost găsită cel puțin o cutie corespunzătoare targetului (dacă target_box a fost specificat), 0 altfel.
      - flag2: 1 dacă cutia returnată este targetul (adică, se urmărește cutia dorită), 0 dacă s-a returnat o cutie blocantă sau o altă cutie.
      - access_level: numărul de cutii ce trebuie mutate (clamped la maxim 10)
      - blocking_boxes: lista cutiilor care blochează accesul (fiecare element ca (box_color, letter))
    """
    if not session_data:
        return None, 0, 0, None, []
    
    # Calculăm limitele pentru atribuirea coloanelor pe baza coordonatelor x ale cutiilor
    xs = [pkg["position"][0] for pkg in session_data.values()]
    p20, p40, p60, p80 = np.percentile(xs, [20, 40, 60, 80])
    
    def assign_column(x):
        if x < p20:
            return 0
        elif x < p40:
            return 1
        elif x < p60:
            return 2
        elif x < p80:
            return 3
        else:
            return 4

    # Atribuim fiecărei cutii coloana corespunzătoare
    for key, pkg in session_data.items():
        x = pkg["position"][0]
        pkg["column"] = assign_column(x)
    
    # Grupăm cutiile pe coloane și sortăm în fiecare coloană după coordonata y descrescătoare 
    # (y mai mare = mai aproape de robot)
    columns = {i: [] for i in range(5)}
    for pkg in session_data.values():
        col = pkg["column"]
        columns[col].append(pkg)
    for col in columns:
        columns[col].sort(key=lambda pkg: pkg["position"][1], reverse=True)
    
    # Determinăm cutia "overall best" – cea mai apropiată de centru, pe baza distanței Euclidiene
    center_x, center_y = zone_center
    overall_best = None
    best_dist = float('inf')
    for pkg in session_data.values():
        x, y = pkg["position"]
        dist = math.sqrt((x - center_x)**2 + (y - center_y)**2)
        if dist < best_dist:
            best_dist = dist
            overall_best = pkg
    # Calculăm indexul în coloană pentru overall_best
    overall_col = overall_best["column"]
    overall_idx = columns[overall_col].index(overall_best)
    overall_access = overall_idx
    overall_blocking = [
        (b["box_color"], b["letters"][0] if b.get("letters") else None)
        for b in columns[overall_col][:overall_idx]
    ]
    
    target_found = 0
    target_in_return = 0
    chosen_box = None
    access_level = 0
    blocking_boxes = []
    
    if target_box is not None:
        # Extragem target_color și target_letter din target_box
        if isinstance(target_box, (tuple, list)):
            target_color, target_letter = target_box
        else:
            target_color = target_box.get("box_color")
            target_letter = target_box.get("letters")[0] if target_box.get("letters") else None
        
        # Selectăm cutiile ce corespund targetului
        matching_boxes = []
        for pkg in session_data.values():
            pkg_letter = pkg["letters"][0] if pkg.get("letters") else None
            if pkg["box_color"] == target_color and pkg_letter == target_letter:
                matching_boxes.append(pkg)
        
        if matching_boxes:
            target_found = 1
            # Selectăm candidate-ul target ca fiind cel cu cel mai mic index în propria coloană
            best_access = float('inf')
            candidate = None
            for box in matching_boxes:
                col = box["column"]
                idx = columns[col].index(box)
                if idx < best_access:
                    best_access = idx
                    candidate = box
            candidate_blocking = [
                (b["box_color"], b["letters"][0] if b.get("letters") else None)
                for b in columns[candidate["column"]][:best_access]
            ]
            # Logica depinde de parametrul mandatory
            if mandatory:
                # Vreau targetul indiferent de blocare: returnez candidate cu flag2=1,
                # dar indic nivelul de acces (câte cutii sunt în față) și lista cutiilor blocante.
                chosen_box = candidate
                access_level = best_access
                blocking_boxes = candidate_blocking
                target_in_return = 1
            else:
                # Dacă nu este mandatory, prefer cel mai accesibil box din întreaga sesiune,
                # CU excepția cazului în care targetul este accesibil (index 0).
                if best_access == 0:
                    chosen_box = candidate
                    access_level = 0
                    blocking_boxes = []
                    target_in_return = 1
                else:
                    # Targetul există dar este blocat, deci alegem overall best
                    chosen_box = overall_best
                    access_level = overall_access
                    blocking_boxes = overall_blocking
                    target_in_return = 0
        else:
            # Nu s-a găsit target-ul, deci alegem overall best
            chosen_box = overall_best
            access_level = overall_access
            blocking_boxes = overall_blocking
            target_found = 0
            target_in_return = 0
    else:
        # Niciun target specificat; alegem overall best
        chosen_box = overall_best
        access_level = overall_access
        blocking_boxes = overall_blocking
        target_found = 0
        target_in_return = 0

    # Construim informațiile pentru cutia returnată
    tracked_info = {
        "position": chosen_box["position"],
        "distance": math.sqrt((chosen_box["position"][0] - zone_center[0])**2 + (chosen_box["position"][1] - zone_center[1])**2),
        "box_color": chosen_box["box_color"],
        "letter": chosen_box["letters"][0] if chosen_box.get("letters") else None,
        "column": chosen_box["column"]
    }
    
    access_level = min(access_level, 10)
    
    return tracked_info, target_found, target_in_return, access_level, blocking_boxes

# ---------------------------
# EXEMPLE DE UTILIZARE:
# ---------------------------
if __name__ == "__main__":
    # Exemplu ipotetic de session_data
    session_data = {
        "box1": {"position": (244, 164), "box_color": "Green", "letters": ["A"]},
        "box2": {"position": (450, 167), "box_color": "Green", "letters": ["K"]},
        "box3": {"position": (248, 335), "box_color": "Blue",  "letters": ["A"]},
        "box4": {"position": (431, 379), "box_color": "Sample", "letters": []},
        "box5": {"position": (171, 416), "box_color": "Red", "letters": ["A"]},
        "box6": {"position": (343, 430), "box_color": "Green", "letters": ["O"]},
        "box7": {"position": (258, 484), "box_color": "Sample", "letters": ["A"]},
        "box8": {"position": (125, 482), "box_color": "Sample", "letters": ["K"]},
        "box9": {"position": (395, 490), "box_color": "Blue", "letters": ["K"]},
        "box10": {"position": (57, 155), "box_color": "Red", "letters": ["K"]},
        "box11": {"position": (156, 262), "box_color": "Sample", "letters": ["O"]},
        "box12": {"position": (355, 275), "box_color": "Red", "letters": ["O"]}
    }
    
    # Exemplu de apel: dacă targetul este specificat, de exemplu ("Red", "A")
    target = ("Red", "A")
    # Dacă mandatory e True, dorim targetul, chiar dacă e blocat; dacă e False, se alege cea mai accesibilă cutie
    tracked, flag1, flag2, nivel_acces, lista_cutii = determine_tracked_box(session_data, target_box=target, mandatory=True, zone_center=(256, 256))
    
    print("Tracked Box Info:", tracked)
    print("Flag1 (target găsit):", flag1)
    print("Flag2 (cutia returnată este targetul):", flag2)
    print("Nivel acces:", nivel_acces)
    print("Lista cutii de mutat:", lista_cutii)
