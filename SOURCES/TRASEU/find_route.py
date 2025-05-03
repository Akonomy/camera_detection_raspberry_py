#!/usr/bin/env python3
import json
import math
import os
from collections import deque

#--------------------< Constante și funcții helper >------------------------
DIR_N = "N"
DIR_S = "S"
DIR_E = "E"
DIR_W = "W"

def compute_exits(entry_dir):
    """Returnează un dicționar cu ieșiri bazate pe direcția de intrare."""
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

def get_direction(from_coord, to_coord):
    """Determină direcția absolută dintre două puncte (în Tkinter, y crește în jos)."""
    dx = to_coord[0] - from_coord[0]
    dy = to_coord[1] - from_coord[1]
    if abs(dx) >= abs(dy):
        return DIR_E if dx > 0 else DIR_W
    else:
        return DIR_S if dy > 0 else DIR_N

def relative_exit_label(incoming, desired):
    """Returnează eticheta relativă pentru ieșire (ex: BACK, LEFT, RIGHT, FORWARD)."""
    mapping = compute_exits(incoming)
    if desired == mapping["înainte"]:
         return "BACK"
    elif desired == mapping["dreapta"]:
         return "LEFT"
    elif desired == mapping["stânga"]:
         return "RIGHT"
    else:
         return "FORWARD"
#--------------------< Sfârșit Constante și funcții helper >------------------------


#--------------------< Structuri de date pentru graf >------------------------
def load_graph_data(filename):
    """Încarcă datele dintr‑un fișier JSON."""
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

def build_graph(data):
    """
    Construiește un graf: nod -> listă de noduri vecine.
    Nodurile sunt etichetate cu "Z{zone_id}" pentru zone și "I{id}" pentru intersecții.
    Se rețin, de asemenea, coordonatele nodurilor.
    """
    graph = {}
    coords = {}
    node_info = {}

    # Zonele
    for z in data.get("zones", []):
        key = f"Z{z['zone_id']}"
        graph[key] = []
        coords[key] = (z["x"] + z["width"] / 2, z["y"] + z["height"] / 2)
        node_info[key] = z

    # Intersecțiile
    for inter in data.get("intersectii", []):
        key = f"I{inter['id']}"
        graph[key] = []
        coords[key] = (inter["x"], inter["y"])
        node_info[key] = inter

    # Liniile
    for l in data.get("lines", []):
        ep1 = l["ep1"]
        ep2 = l["ep2"]
        key1 = f"Z{ep1['parent_id']}" if ep1["parent_type"] == "zone" else f"I{ep1['parent_id']}"
        key2 = f"Z{ep2['parent_id']}" if ep2["parent_type"] == "zone" else f"I{ep2['parent_id']}"
        if key1 in graph and key2 in graph:
            graph[key1].append(key2)
            graph[key2].append(key1)
    return graph, coords, node_info
#--------------------< Sfârșit Structuri de date pentru graf >------------------------


#--------------------< Algoritm BFS pentru traseu cel mai scurt >------------------------
def bfs_shortest_path(graph, start, goal):
    """Calculează traseul cel mai scurt între două noduri folosind BFS."""
    visited = set()
    queue = deque([[start]])
    while queue:
        path = queue.popleft()
        node = path[-1]
        if node == goal:
            return path
        if node not in visited:
            visited.add(node)
            for neighbor in graph.get(node, []):
                new_path = list(path)
                new_path.append(neighbor)
                queue.append(new_path)
    return None
#--------------------< Sfârșit BFS >------------------------


#--------------------< Stare globală a modulului >------------------------
_raw_data = {}
_graph = {}
_coords = {}
_node_info = {}
_zone_names = {}   # mapping: identificator zonă -> nume original (din JSON)
_zone_aliases = {} # mapping: identificator zonă -> alias curent (poate fi redenumit)
_data_loaded = False

def load_data(filename=None):
    """
    Încarcă datele din fișierul JSON.
    Dacă nu se specifică filename, se folosește 'schema_depozit.json' din directorul modulului.
    """
    global _raw_data, _graph, _coords, _node_info, _zone_names, _zone_aliases, _data_loaded
    if filename is None:
        filename = os.path.join(os.path.dirname(__file__), "schema_depozit.json")
    data = load_graph_data(filename)
    _raw_data = data  # <-- asta e cheia
    _graph, _coords, _node_info = build_graph(data)
    # Construiește mappingul zonelor (cheie: 'Z{zone_id}', valoare: numele zonei)
    _zone_names = {f"Z{z['zone_id']}": z["name"] for z in data.get("zones", [])}
    # Inițial, alias-urile sunt identice cu numele originale
    _zone_aliases = _zone_names.copy()
    _data_loaded = True

def ensure_data_loaded():
    """Asigură că datele au fost încărcate (apelul funcțiilor publice)."""
    if not _data_loaded:
        load_data()


def get_data():
    ensure_data_loaded()
    return _raw_data


#--------------------< Funcții Publice >------------------------

def getAll():
    """
    Returnează toate zonele disponibile sub forma unui dicționar:
      cheie: identificatorul zonei (ex: 'Z1')
      valoare: denumirea curentă (alias) a zonei.
    """
    ensure_data_loaded()
    return _zone_aliases.copy()

def resolve_zone(name):
    from find_tag import get_data as get_tag_data
    data = get_data()
    tag_data = get_tag_data()

    # Caută după nume de zonă sau Z{id}
    for zona in data['zones']:
        if zona['name'] == name:
            return f"Z{zona['zone_id']}"
        if f"Z{zona['zone_id']}" == name:
            return f"Z{zona['zone_id']}"

    # Caută după intersecție sau I{id}
    for inter in data['intersectii']:
        if f"Intersectia {inter['id']}" == name:
            return f"I{inter['id']}"
        if f"I{inter['id']}" == name:
            return f"I{inter['id']}"

    # Caută în taguri
    for tag in tag_data.get('tags', []):
        if tag['custom_id'] == name:
            assigned = tag['assigned_to']
            if assigned.lower().startswith("intersectia"):
                inter_id = int(assigned.split()[1])
                return f"I{inter_id}"
            for zona in data['zones']:
                if zona['name'] == assigned:
                    return f"Z{zona['zone_id']}"

    raise ValueError(f"Zona cu denumirea '{name}' nu a fost găsită.")




def getfastPath(punctA, punctB):
    """
    Calculează traseul brut (fără recomandări de direcții) între două puncte date.
    
    Parametri:
      punctA - numele (alias sau identificatorul) zonei de start.
      punctB - numele (alias sau identificatorul) zonei de destinație.
      
    Returnează o listă cu traseul, de ex: ["Livrare1", "I5", "I8", "I6", "Depozit5"].
    """
    ensure_data_loaded()
    start = resolve_zone(punctA)
    goal = resolve_zone(punctB)
    path = bfs_shortest_path(_graph, start, goal)
    if not path:
        return None
    # Pentru nodurile de tip zonă se folosește aliasul (dacă există)
    route_list = [_zone_aliases.get(n, n) if n.startswith("Z") else n for n in path]
    return route_list

def getPath(punctA, punctB):
    """
    Calculează traseul complet (cu recomandări de direcții) între două puncte date.
    
    Parametri:
      punctA - numele (alias sau identificatorul) zonei de start.
      punctB - numele (alias sau identificatorul) zonei de destinație.
      
    Returnează o listă cu traseul și recomandările de direcții, de ex:
    ["Livrare1", "Intersectia I5[LEFT]", "Intersectia I8[FORWARD]", "Intersectia I6[LEFT]", "Depozit5"].
    """
    ensure_data_loaded()
    start = resolve_zone(punctA)
    goal = resolve_zone(punctB)
    path = bfs_shortest_path(_graph, start, goal)
    if not path:
        return None

    route_list = []
    for i, node in enumerate(path):
        if node.startswith("Z"):
            # Pentru zone, folosim aliasul
            route_list.append(_zone_aliases.get(node, node))
        else:
            # Pentru nodurile de intersecție, dacă nu este ultimul se calculează direcția
            if i < len(path) - 1:
                incoming = get_direction(_coords[path[i-1]], _coords[node])
                desired = get_direction(_coords[node], _coords[path[i+1]])
                rel_label = relative_exit_label(incoming, desired)
                route_list.append(f"Intersectia {node}[{rel_label}]")
            else:
                route_list.append(f"Intersectia {node}")
    return route_list


def getfastPathFromCross(cross, zone):
    """
    Calculează traseul brut (fără recomandări de direcții) între o intersecție și o zonă.
    
    Parametri:
      cross - numele (identificatorul) intersecției de start (ex: "I5").
      zone  - numele (alias sau identificatorul) zonei de destinație.
      
    Returnează o listă cu traseul, de ex: ["I5", "I8", "Depozit5"].
    """
    ensure_data_loaded()
    if cross not in _graph:
        raise ValueError(f"Intersectia '{cross}' nu a fost găsită.")
    start = cross
    goal = resolve_zone(zone)
    path = bfs_shortest_path(_graph, start, goal)
    if not path:
        return None
    route_list = [_zone_aliases.get(n, n) if n.startswith("Z") else n for n in path]
    return route_list

def getPathFromCross(cross, zone):
    """
    Calculează traseul complet (cu recomandări de direcții) între o intersecție și o zonă.
    
    Parametri:
      cross - numele (identificatorul) intersecției de start (ex: "I5").
      zone  - numele (alias sau identificatorul) zonei de destinație.
      
    Returnează o listă cu traseul și recomandările de direcții, de ex:
    ["Intersectia I5", "Intersectia I8[LEFT]", "Intersectia I6[LEFT]", "Depozit5"].
    """
    ensure_data_loaded()
    if cross not in _graph:
        raise ValueError(f"Intersectia '{cross}' nu a fost găsită.")
    start = cross
    goal = resolve_zone(zone)
    path = bfs_shortest_path(_graph, start, goal)
    if not path:
        return None

    route_list = []
    for i, node in enumerate(path):
        if node.startswith("Z"):
            route_list.append(_zone_aliases.get(node, node))
        else:
            if i == 0:
                # Primul nod (intersecție) nu are direcție de intrare
                route_list.append(f"Intersectia {node}")
            elif i < len(path) - 1:
                incoming = get_direction(_coords[path[i-1]], _coords[node])
                desired = get_direction(_coords[node], _coords[path[i+1]])
                rel_label = relative_exit_label(incoming, desired)
                route_list.append(f"Intersectia {node}[{rel_label}]")
            else:
                route_list.append(f"Intersectia {node}")
    return route_list

#--------------------< Sfârșit Funcții Publice >------------------------



def _rename_single(existing, new_alias):
    """
    Funcție internă pentru redenumirea unei singure zone.
    Verifică ca noul alias să nu fie deja atribuit unei alte zone.
    """
    ensure_data_loaded()
    zone_key = resolve_zone(existing)
    # Verifică conflictul: dacă new_alias există deja pentru altă zonă, se aruncă excepție.
    for key, alias in _zone_aliases.items():
        if alias == new_alias and key != zone_key:
            raise ValueError(f"Alias-ul '{new_alias}' este deja folosit pentru zona {key}.")
    _zone_aliases[zone_key] = new_alias

def rename(existing, new_alias):
    """
    Permite redenumirea unei zone sau a unui set de zone.
    
    Parametri:
      existing - identificatorul (sau alias-ul curent) zonei sau lista de zone.
      new_alias - noua denumire sau lista de denumiri corespunzătoare.
    
    Exemplu:
      rename("Z2", "Livrare1")
      rename(["Z2", "Z3"], ["Livrare1", "Depozit5"])
      
    Dacă noul alias este deja folosit pentru o altă zonă, funcția aruncă o eroare.
    """
    ensure_data_loaded()
    if isinstance(existing, list):
        if not isinstance(new_alias, list) or len(existing) != len(new_alias):
            raise ValueError("Listele trebuie să aibă aceeași lungime.")
        for ex, na in zip(existing, new_alias):
            _rename_single(ex, na)
    else:
        _rename_single(existing, new_alias)
#--------------------< Sfârșit Funcții Publice >------------------------


# Exemplu de test (se execută doar dacă modulul este rulat direct)
if __name__ == "__main__":
    load_data()  # Încarcă datele din 'schema_depozit.json'
    print("Zone disponibile inițial:")
    for key, name in getAll().items():
        print(f"{key}: {name}")
    
    # Exemplu de redenumire
    try:
        rename("Z1", "Livrare1")
        rename("Z2", "Depozit5")
    except ValueError as e:
        print("Eroare la redenumire:", e)
    
    print("\nZone disponibile după redenumire:")
    for key, name in getAll().items():
        print(f"{key}: {name}")
    
    # Exemplu de calculare traseu între două zone
    fast_path = getfastPath("Livrare1", "Depozit5")
    complete_path = getPath("Livrare1", "Depozit5")
    
    print("Traseu rapid:", " -> ".join(fast_path))
    print("Traseu complet:", " -> ".join(complete_path))
    
    # Exemplu de calculare traseu pornind de la o intersecție către o zonă
    fast_path_cross = getfastPathFromCross("I5", "Depozit5")
    complete_path_cross = getPathFromCross("I5", "Depozit5")
    
    print("Traseu rapid de la intersecție:", " -> ".join(fast_path_cross))
    print("Traseu complet de la intersecție:", " -> ".join(complete_path_cross))
