import os
import sys
import re

# Adaugă directorul curent în sys.path pentru importuri locale
sys.path.append(os.path.dirname(__file__))

from find_route import load_data as load_route_data, getfastPath, getPath, resolve_zone
from find_tag import load_data as load_tag_data, getDirections, getCross, getTags

# Constante direcții numerice
direction_map = {
    "FORWARD": 1,
    "RIGHT": 2,
    "LEFT": 3,
    "BACK": 4
}

def normalize_node_name(name):
    import re
    if "Intersectia" in name:
        num = re.findall(r'\d+', name)
        return f"I{num[0]}" if num else name
    match = re.search(r'\[(\d+)\]', name)
    if match:
        return f"Z{match.group(1)}"
    return name


def get_direction_sequence(path):
    sequence = []
    for step in path:
        if '[' in step:
            match = re.search(r'\[(.*?)\]', step)
            if match:
                label = match.group(1)
                num = direction_map.get(label.upper())
                if num:
                    sequence.append(num)
    return sequence


def get_possible_tags_for_path(path):
    tags_by_inter = dict(getTags())
    useful_tags = {}

    print("\n[DEBUG] Path analizat:")
    for p in path:
        print(" -", p)

    for i, node in enumerate(path):
        if not node.startswith("Intersectia"):
            continue

        inter_id = node.split()[1].split('[')[0].lstrip("I")

        next_node = None
        prev_node = None

        if i > 0:
            prev_node = path[i - 1].split()[1].split('[')[0] if "Intersectia" in path[i - 1] else path[i - 1]
        if i < len(path) - 1:
            next_node = path[i + 1].split()[1].split('[')[0] if "Intersectia" in path[i + 1] else path[i + 1]

        prev_node = normalize_node_name(prev_node) if prev_node else None
        next_node = normalize_node_name(next_node) if next_node else None

        print(f"\n[DEBUG] Intersecție curentă: I{inter_id}")
        print(f"[DEBUG]  - Nod anterior: {prev_node}")
        print(f"[DEBUG]  - Nod următor: {next_node}")

        tags = tags_by_inter.get(f"I{inter_id}", [])
        print(f"[DEBUG]  - Taguri disponibile: {[t['custom_id'] for t in tags]}")

        for tag in tags:
            directions = getDirections(tag)
            print(f"    [DEBUG]  > Tag {tag['custom_id']} directions: {directions}")

            # Normalizează toți vecinii direcți
            normalized_directions = {k: normalize_node_name(v) if v else None for k, v in directions.items()}

            entry_match = normalized_directions.get("BACK") == prev_node
            exit_match = next_node in normalized_directions.values()

            print(f"      [DEBUG]     - Entry match: {entry_match}")
            print(f"      [DEBUG]     - Exit match:  {exit_match}")

            if entry_match and exit_match:
                print(f"      [DEBUG]     -> Tag {tag['custom_id']} ADĂUGAT")
                useful_tags.setdefault(f"I{inter_id}", []).append(tag['custom_id'])
            else:
                print(f"      [DEBUG]     -> Tag {tag['custom_id']} IGNORAT")

    return useful_tags



def analyze_route(source, target):
    load_route_data()
    load_tag_data()

    try:
        src = resolve_zone(source)
    except:
        src = source  # Maybe it's already a node or intersection

    tgt = resolve_zone(target)

    fast_path = getfastPath(src, tgt)
    full_path = getPath(src, tgt)
    direction_seq = get_direction_sequence(full_path)
    tags = get_possible_tags_for_path(full_path)

    return {
        "from": source,
        "to": target,
        "fast_path": fast_path,
        "full_path": full_path,
        "directions_numeric": direction_seq,
        "possible_tags": tags
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="Tag ID sau nume zonă sursă")
    parser.add_argument("target", help="Nume zonă destinație")
    args = parser.parse_args()

    source = args.source
    target = args.target

    result = analyze_route(source, target)

    print("\n=== TRASEU ===")
    print(" -> ".join(result['fast_path']))

    print("\n=== INSTRUCȚIUNI COMPLETE ===")
    for step in result['full_path']:
        print(" -", step)

    print("\n=== DIRECȚII (numerice) ===")
    print(result['directions_numeric'])

    print("\n=== TAGURI UTILE PE TRASEU ===")
    for inter, tags in result['possible_tags'].items():
        print(f" - {inter}: {tags}")
