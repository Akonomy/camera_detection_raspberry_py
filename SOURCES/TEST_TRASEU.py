#!/usr/bin/env python3
import os
import json

# Importăm funcțiile din modulul find_route
from TRASEU.find_route import (
    load_data as route_load_data,
    getAll,
    getfastPath,
    getPath,
    rename
)

# Importăm funcțiile din modulul find_tag
from TRASEU.find_tag import (
    load_data as tag_load_data,
    getDirections,
    getPosition,
    getCross,
    getTags,
    list_intersections_and_tags,
    lookup_tag
)

def main():
    # === Exemplu de utilizare a funcțiilor din find_route ===
    print("=== Funcții din find_route ===")
    
    # Încarcă datele pentru graf (folosește implicit schema_depozit.json din directorul modulului)
    route_load_data()
    print("Zone disponibile inițial:")
    zones = getAll()
    for zone_id, alias in zones.items():
        print(f"  {zone_id}: {alias}")
    
    # Exemplu de redenumire: Z1 devine 'Livrare1' și Z2 devine 'Depozit5'
    print("\nRedenumire zone: Z1 -> Livrare1, Z2 -> Depozit5")
    try:
        rename("Z1", "Livrare1")
        rename("Z2", "Depozit5")
    except ValueError as e:
        print("Eroare la redenumire:", e)
    
    print("Zone disponibile după redenumire:")
    zones = getAll()
    for zone_id, alias in zones.items():
        print(f"  {zone_id}: {alias}")
    
    # Calculare traseu rapid între două zone
    print("\nCalculare traseu rapid de la 'Livrare1' la 'Depozit5':")
    fast_path = getfastPath("Livrare1", "Depozit5")
    if fast_path:
        print("Traseu rapid:", " -> ".join(fast_path))
    else:
        print("Traseu rapid: Nu a fost găsit niciun traseu.")
    
    # Calculare traseu complet cu direcții între două zone
    print("\nCalculare traseu complet (cu direcții) de la 'Livrare1' la 'Depozit5':")
    complete_path = getPath("Livrare1", "Depozit5")
    if complete_path:
        print("Traseu complet:", " -> ".join(complete_path))
    else:
        print("Traseu complet: Nu a fost găsit niciun traseu.")
    
    # === Exemplu de utilizare a funcțiilor din find_tag ===
    print("\n=== Funcții din find_tag ===")
    
    # Încarcă datele export (folosește implicit schema_depozit.json din directorul modulului)
    tag_load_data()
    
    # Pentru funcțiile de listare a tag-urilor, avem nevoie de datele export
    # (presupunem că fișierul JSON se află în directorul TRASEU)
    json_path = os.path.join(os.path.dirname(__file__), "TRASEU", "schema_depozit.json")
    with open(json_path, "r", encoding="utf-8") as f:
        export_data = json.load(f)
    
    # Listăm intersecțiile și tagurile din date
    print("\nListare intersecții și taguri din date:")
    list_intersections_and_tags(export_data)
    
    # Exemplu de lookup pentru un tag specific (presupunem că există un tag cu custom_id "TAG1")
    tag_id = "TAG1"
    print(f"\nDetalii pentru tag '{tag_id}':")
    lookup_tag(tag_id, export_data)
    
    # Exemplu de grupare a tagurilor după intersecție
    print("\nGruparea tagurilor după intersecție:")
    groups = getTags()
    for group in groups:
        intersection, tags = group
        print(f"Intersecție: {intersection} - Număr tag-uri: {len(tags)}")
        for tag in tags:
            print(f"  Tag: {tag['custom_id']}")

if __name__ == "__main__":
    main()
