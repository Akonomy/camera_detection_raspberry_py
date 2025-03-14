import math
import numpy as np

def determine_tracked_box(session_data, target_box=None, mandatory=False, zone_center=(247, 100)):
    """
    Determină cutia (sau cutia blocantă) ce trebuie urmărită/mutată, pe baza:
      - informațiilor din sesiune (poziție, culoare, litere etc.)
      - opțional, a unei cutii țintă specificate (ex: ("A", "blue") sau un dict cu cheile "box_color" și "letters")
      - opțional, dacă ținta este mandatory (adică se dorește să fie urmărită chiar dacă e blocată)
    
    Returnează un tuple:
      (tracked_box_info, flag1, flag2, nivel_acces, lista_cutii)
      
      - tracked_box_info: dict cu poziția, distanța de la centru, culoarea, litera și coloana (pentru debug)
      - flag1: 1 dacă cutia țintă (target) a fost găsită în sesiune, 0 altfel
      - flag2: 1 dacă cutia returnată este chiar cutia țintă, 0 dacă s-a returnat o cutie blocantă (cea ce trebuie mutată)
      - nivel_acces: un nivel de acces de la 0 la 10 (0 = imediat accesibil; 1 înseamnă că trebuie mutată 1 cutie etc.)
      - lista_cutii: lista (în ordine) de cutii ce trebuie mutate pentru a ajunge la țintă, fiecare reprezentată ca (culoare, literă)
    """
    
    # Dacă nu există cutii în sesiune, returnăm None cu flagurile 0
    if not session_data:
        return None, 0, 0, None, []
    
    # Extragem coordonatele x ale cutiilor
    xs = [ pkg["position"][0] for pkg in session_data.values() ]
    # Calculăm percentila 20, 40, 60, 80 pentru a defini granițele coloanelor
    p20, p40, p60, p80 = np.percentile(xs, [20, 40, 60, 80])
    
    # Funcție care asignează o cutie unei coloane (0: safe stânga, 1: traiectorie stânga, 
    # 2: mijloc (problematic), 3: traiectorie dreapta, 4: safe dreapta)
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
    
    # Adăugăm la fiecare cutie informația despre coloana în care se află
    for key, pkg in session_data.items():
        x = pkg["position"][0]
        pkg["column"] = assign_column(x)
    
    # Grupăm cutiile după coloană
    columns = {i: [] for i in range(5)}
    for pkg in session_data.values():
        col = pkg["column"]
        columns[col].append(pkg)
    
    # În fiecare coloană, sortăm cutiile în funcție de coordonata y descrescătoare
    # (presupunând că y mai mare înseamnă că cutia este mai aproape de robot)
    for col in columns:
        columns[col].sort(key=lambda pkg: pkg["position"][1], reverse=True)
    
    # Inițializări
    target_found = 0
    target_in_return = 0
    chosen_box = None
    access_level = 0
    blocking_boxes = []  # lista cutiilor care blochează accesul (de tip (culoare, literă))
    
    # Dacă a fost specificată o cutie țintă, căutăm în sesiune
    if target_box is not None:
        # Extragem culoarea și litera din target
        if isinstance(target_box, (tuple, list)):
            target_color, target_letter = target_box
        else:
            target_color = target_box.get("box_color")
            target_letter = target_box.get("letters")[0] if target_box.get("letters") else None
        
        matching_boxes = []
        for pkg in session_data.values():
            pkg_letter = pkg["letters"][0] if pkg.get("letters") else None
            if pkg["box_color"] == target_color and pkg_letter == target_letter:
                matching_boxes.append(pkg)
        
        if matching_boxes:
            target_found = 1
            # Dintre toate potrivirile, alegem pe cea mai accesibilă (cu indexul cel mai mic în coloana respectivă)
            best_access = float('inf')
            best_box = None
            for box in matching_boxes:
                col = box["column"]
                # Determinăm poziția în coloana respectivă
                idx = columns[col].index(box)
                if idx < best_access:
                    best_access = idx
                    best_box = box
            # Dacă cutia țintă nu este imediat accesibilă și nu este mandatory,
            # alegem să returnăm cutia blocantă (cea cu index 0 din aceeași coloană)
            if best_access > 0 and not mandatory:
                chosen_box = columns[best_box["column"]][0]
                # Nivelul de acces se va considera ca fiind numărul de cutii care trebuie mutate
                access_level = best_access
                # Lista cutiilor ce blochează: toate cele cu index < best_access
                blocking_boxes = [
                    (b["box_color"], b["letters"][0] if b.get("letters") else None)
                    for b in columns[best_box["column"]][:best_access]
                ]
                target_in_return = 0
            else:
                # Dacă target-ul este accesibil (sau este mandatory), returnăm target-ul
                chosen_box = best_box
                access_level = best_access
                blocking_boxes = [
                    (b["box_color"], b["letters"][0] if b.get("letters") else None)
                    for b in columns[best_box["column"]][:best_access]
                ]
                target_in_return = 1
        # Dacă target-ul specificat nu a fost găsit, se va alege cutia cea mai apropiată de centru
    if chosen_box is None:
        # Selectăm cutia cea mai apropiată de centru
        center_x, center_y = zone_center
        best_dist = float('inf')
        best_box = None
        for pkg in session_data.values():
            x, y = pkg["position"]
            dist = math.sqrt((x - center_x)**2 + (y - center_y)**2)
            if dist < best_dist:
                best_dist = dist
                best_box = pkg
        chosen_box = best_box
        col = chosen_box["column"]
        idx = columns[col].index(chosen_box)
        access_level = idx
        blocking_boxes = [
            (b["box_color"], b["letters"][0] if b.get("letters") else None)
            for b in columns[col][:idx]
        ]
        target_in_return = 0
        target_found = 0

    # Construim informațiile cutiei urmărite
    tracked_info = {
        "position": chosen_box["position"],
        "distance": math.sqrt((chosen_box["position"][0] - zone_center[0])**2 + (chosen_box["position"][1] - zone_center[1])**2),
        "box_color": chosen_box["box_color"],
        "letter": chosen_box["letters"][0] if chosen_box.get("letters") else None,
        "column": chosen_box["column"]
    }
    
    # Nivelul de acces este clamped la maxim 10
    access_level = min(access_level, 10)
    
    return tracked_info, target_found, target_in_return, access_level, blocking_boxes

# ---------------------------
# EXEMPLE DE UTILIZARE:
# ---------------------------

if __name__ == "__main__":
    # Exemplu ipotetic de session_data – cheile pot fi orice, dar cel puțin trebuie să conțină "position", "box_color" și "letters"
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
    
    # Să presupunem că vrem să accesăm cutia "A blue"
    target = ("A", "blue")
    # Apelăm funcția – în acest exemplu, target nu este mandatory, deci dacă e blocată se va returna cutia blocantă
    tracked, flag1, flag2, nivel_acces, lista_cutii = determine_tracked_box(session_data, target_box=target, mandatory=False, zone_center=(256, 256))
    
    print("Tracked Box Info:", tracked)
    print("Flag1 (target găsit):", flag1)
    print("Flag2 (cutia returnată este target):", flag2)
    print("Nivel acces:", nivel_acces)
    print("Lista cutii de mutat:", lista_cutii)


