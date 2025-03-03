#!/usr/bin/env python3
import json
import sys
import argparse
import os
import random

#--------------------< Constante și Funcții Helper >------------------------
DIR_N = "N"
DIR_S = "S"
DIR_E = "E"
DIR_W = "W"

def compute_exits(entry_dir):
    """
    Pentru o direcție de intrare, returnează mappingul exiturilor.
    """
    mapping = {}
    if entry_dir == DIR_N:
        mapping["înainte"] = DIR_S
        mapping["dreapta"] = DIR_W
        mapping["stânga"] = DIR_E
        mapping["înapoi"] = DIR_N
    elif entry_dir == DIR_S:
        mapping["înainte"] = DIR_N
        mapping["dreapta"] = DIR_E
        mapping["stânga"] = DIR_W
        mapping["înapoi"] = DIR_S
    elif entry_dir == DIR_E:
        mapping["înainte"] = DIR_W
        mapping["dreapta"] = DIR_N
        mapping["stânga"] = DIR_S
        mapping["înapoi"] = DIR_E
    elif entry_dir == DIR_W:
        mapping["înainte"] = DIR_E
        mapping["dreapta"] = DIR_S
        mapping["stânga"] = DIR_N
        mapping["înapoi"] = DIR_W
    return mapping

def get_label_for_exit(exits):
    """
    Transformă mapping-ul de exituri într-un dicționar cu etichete:
      FORWARD = "înainte", RIGHT = "dreapta", LEFT = "stânga", BACK = "înapoi"
    """
    labels = {
        "înainte": "FORWARD",
        "dreapta": "RIGHT",
        "stânga": "LEFT",
        "înapoi": "BACK"
    }
    return {labels[k]: v for k, v in exits.items()}
#--------------------< Sfârșit Constante și Funcții Helper >------------------------

#--------------------< Încărcarea Datelor Exportate >------------------------
def load_export_data(filename):
    """Încarcă fișierul exportat (JSON)."""
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)

# Variabilă globală pentru datele exportate
_export_data = None

def load_data(filename=None):
    """
    Încarcă datele din fișierul export.
    Dacă nu se specifică filename, se folosește 'schema_depozit.json' din același director.
    """
    global _export_data
    if filename is None:
        filename = os.path.join(os.path.dirname(__file__), "schema_depozit.json")
    _export_data = load_export_data(filename)
#--------------------< Sfârșit Încărcare Date >------------------------

#--------------------< Funcții pentru Tag-uri >------------------------
def getDirections(tag):
    """
    Returnează recomandările de direcție pentru un tag, pe baza memoriei intersecției la care este atribuit.
    
    Parametru:
      tag - dicționarul ce reprezintă tagul.
      
    Returnează un dicționar cu cheile "FORWARD", "RIGHT", "LEFT" și "BACK" și valorile corespunzătoare.
    Dacă tagul nu este atribuit unei intersecții sau nu se găsește memoria, se returnează {}.
    """
    assigned = tag.get("assigned_to", "")
    if not assigned.lower().startswith("intersectia"):
        return {}
    try:
        inter_id = int(assigned.split()[1])
    except Exception:
        return {}
    if _export_data is None:
        raise Exception("Datele nu sunt încărcate.")
    inter_memory = None
    for inter in _export_data.get("intersectii", []):
        if inter.get("id") == inter_id:
            inter_memory = inter.get("memory", {})
            break
    if inter_memory is None:
        return {}
    mapping = compute_exits(tag.get("entry_direction", ""))
    mapping_words = {
        "înainte": "FORWARD",
        "dreapta": "RIGHT",
        "stânga": "LEFT",
        "înapoi": "BACK"
    }
    directions = {}
    for key in ["înainte", "dreapta", "stânga", "înapoi"]:
        exit_dir = mapping.get(key)
        exit_val = inter_memory.get(exit_dir)
        if isinstance(exit_val, int):
            # Adăugăm prefixul "I" pentru a standardiza afișarea intersecției
            directions[mapping_words[key]] = f"Intersectia I{exit_val}"
        else:
            directions[mapping_words[key]] = exit_val
    return directions


def getPosition(tag):
    """
    Returnează poziția unui tag sub forma unui dicționar cu:
      - "entry_direction": direcția de intrare
      - "exits": dicționarul exiturilor, convertit cu get_label_for_exit
    """
    entry_dir = tag.get("entry_direction", "-")
    exits = tag.get("exits", {})
    basic_labels = get_label_for_exit(exits)
    return {"entry_direction": entry_dir, "exits": basic_labels}

def getCross(tag):
    """
    Returnează intersecția la care este atribuit tagul.
    Dacă tagul nu este atribuit unei intersecții, returnează None.
    """
    assigned = tag.get("assigned_to", "")
    if assigned.lower().startswith("intersectia"):
        try:
            inter_id = int(assigned.split()[1])
            return f"I{inter_id}"
        except Exception:
            return None
    return None

def getTags():
    """
    Returnează tagurile grupate după intersecție sub forma unei liste.
    Fiecare element al listei are forma:
       [<intersectie>, [<tag1>, <tag2>, ...]]
    Dacă un tag nu este atribuit unei intersecții, acesta este grupat sub cheia "NEATRIBUIT".
    """
    if _export_data is None:
        raise Exception("Datele nu sunt încărcate.")
    groups = {}
    for tag in _export_data.get("tags", []):
        assigned = tag.get("assigned_to", "")
        if assigned.lower().startswith("intersectia"):
            try:
                inter_id = int(assigned.split()[1])
                key = f"I{inter_id}"
            except Exception:
                key = assigned
        else:
            key = "NEATRIBUIT"
        groups.setdefault(key, []).append(tag)
    result = []
    for key, tags in groups.items():
        result.append([key, tags])
    return result
#--------------------< Sfârșit Funcții pentru Tag-uri >------------------------

#--------------------< Funcții de Listare și Lookup >------------------------
def list_intersections_and_tags(data):
    """Listează intersecțiile și tagurile din date."""
    print("\n--- Intersecții ---")
    for inter in data.get("intersectii", []):
        print(f"Intersectia I{inter['id']} la ({inter['x']}, {inter['y']}) - Memory: {inter.get('memory')}")
    print("\n--- Taguri ---")
    for tag in data.get("tags", []):
        print(f"Tag {tag['custom_id']}:")
        print(f"  Atribuit la: {tag.get('assigned_to','-')}")
        pos = getPosition(tag)
        print(f"  Entry Direction: {pos['entry_direction']}")
        print("  Exituri (din tag):")
        for label, val in pos["exits"].items():
            print(f"    {label}: {val}")

def lookup_tag(tag_id, data):
    """Caută și afișează detalii pentru un tag dat."""
    found = False
    for tag in data.get("tags", []):
        if tag["custom_id"].lower() == tag_id.lower():
            found = True
            print(f"\nDetalii pentru Tag {tag['custom_id']}:")
            pos = getPosition(tag)
            print(f"  Entry Direction: {pos['entry_direction']}")
            print("  Exituri (din tag):")
            for label, val in pos["exits"].items():
                print(f"    {label}: {val}")
            cross = getCross(tag)
            if cross:
                print(f"  Atribuit la: {cross}")
                directions = getDirections(tag)
                print("  Recomandări Intersecție:")
                for label, val in directions.items():
                    print(f"    {label}: {val}")
            print("")
            break
    if not found:
        print(f"Tag '{tag_id}' nu a fost găsit.")
#--------------------< Sfârșit Funcții Listare și Lookup >------------------------

#--------------------< Funcție de Testare a Noilor Funcții >------------------------
def test_functions():
    """
    Testează noile funcții:
      - Alege un tag aleatoriu din listă și afișează datele pentru acesta.
      - Afișează gruparea tagurilor pe intersecții.
    """
    if _export_data is None or not _export_data.get("tags"):
        print("Nu există taguri în date.")
        return
    random_tag = random.choice(_export_data["tags"])
    print("Tag ales aleatoriu:", random_tag["custom_id"])
    print("\n--- Detalii Tag ---")
    pos = getPosition(random_tag)
    print(f"Entry Direction: {pos['entry_direction']}")
    print("Exituri (din tag):")
    for label, val in pos["exits"].items():
        print(f"  {label}: {val}")
    cross = getCross(random_tag)
    if cross:
        print(f"Atribuit la: {cross}")
        directions = getDirections(random_tag)
        print("Recomandări Intersecție:")
        for label, val in directions.items():
            print(f"  {label}: {val}")
    else:
        print("Tagul nu este atribuit unei intersecții.")
    
    print("\n--- Grupare Taguri ---")
    groups = getTags()
    for group in groups:
        inter, tags = group
        print(f"Intersecție: {inter} are {len(tags)} tag-uri:")
        for tag in tags:
            print(f"  Tag: {tag['custom_id']}")
#--------------------< Sfârșit Funcție de Testare >------------------------

#--------------------< Main pentru Testare (Modul) >------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Modul pentru procesare tag-uri din fișierul export."
    )
    parser.add_argument("file", nargs="?", help="Numele fișierului export (JSON)", default=None)
    args = parser.parse_args()
    try:
        if args.file:
            load_data(args.file)
        else:
            load_data()  # folosește schema_depozit.json din același director
    except Exception as e:
        print(f"Eroare la încărcarea fișierului: {e}")
        sys.exit(1)
    # Testare a noilor funcții
    test_functions()

if __name__ == "__main__":
    main()
