import os
import sys
import re

# Adaugă directorul curent în sys.path pentru importuri locale

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)


from find_route import load_data as load_route_data, getfastPath, getPath, resolve_zone, getPathFromTag
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
    useful_tags_entry = {}
    useful_tags_exit = {}

    def extract_tag_matches(path):
        matches = {}
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

            tags = tags_by_inter.get(f"I{inter_id}", [])

            for tag in tags:
                directions = getDirections(tag)
                normalized_directions = {k: normalize_node_name(v) if v else None for k, v in directions.items()}

                entry_match = normalized_directions.get("BACK") == prev_node
                exit_match = next_node in normalized_directions.values()

                if entry_match and exit_match:
                    matches.setdefault(f"I{inter_id}", []).append(tag['custom_id'])
        return matches

    # Forward path
    forward_tags = extract_tag_matches(path)
    # Reverse path
    reversed_path = list(reversed(path))
    backward_tags = extract_tag_matches(reversed_path)

    # Sort tags based on appearance in the original path
    combined_tags = {}
    for node in path:
        if not node.startswith("Intersectia"):
            continue
        inter_id = node.split()[1].split('[')[0].lstrip("I")
        tags_forward = forward_tags.get(f"I{inter_id}", [])
        tags_backward = backward_tags.get(f"I{inter_id}", [])
        all_tags = list(dict.fromkeys(tags_forward + tags_backward))
        if all_tags:
            combined_tags[f"I{inter_id}"] = all_tags

    return combined_tags




def analyze_route(source, target):
    from find_tag import getDirections
    from find_route import getPathFromTag  # presupui tu importul
    load_route_data()
    load_tag_data()

    try:
        tgt = resolve_zone(target)
    except Exception as e:
        raise ValueError(f"Destinația '{target}' nu a putut fi rezolvată: {e}")

    if source.startswith("C["):
        # pornim de la un tag -> folosim funcția specială
        full_path = getPathFromTag(source, target)
        if not full_path or len(full_path) < 1:
            print(f"⚠️ [getPathFromTag] Traseul de la {source} la {target} este prea scurt sau inexistent.")
            return {
                "from": source,
                "to": target,
                "fast_path": [],
                "full_path": [],
                "directions_numeric": [],
                "possible_tags": {}
            }

        
        # simulăm fast_path: eliminăm [DIRECTION] din numele intersecțiilor
        fast_path = [node.split('[')[0] if "Intersectia" in node else node for node in full_path]

        direction_seq = get_direction_sequence(full_path)
        tags = get_possible_tags_for_path(full_path)

        try:


           # directions = getDirections(source)
            next_node = normalize_node_name(fast_path[1])
            normalized_directions = {
                label.upper(): normalize_node_name(dest)
                for label, dest in directions.items()
            }
            for label, destination in normalized_directions.items():
                if destination == next_node:
                    direction_num = direction_map.get(label)
                    if direction_num:
                        direction_seq.insert(0, direction_num)
                        break
        except Exception as e:
            print(f"⚠️ [analyze_route.py] Eroare la determinarea direcției inițiale din tagul {source}: {e}")

    else:
        # sursă normală: alias, Zx, sau Intersectia X
        try:
            src = resolve_zone(source)
        except Exception:
            src = source  # poate e deja nod valid

        fast_path = getfastPath(src, tgt)
        full_path = getPath(src, tgt)
        direction_seq = get_direction_sequence(full_path)
        tags = get_possible_tags_for_path(full_path)

   # print(f'DEBUG line158 get_route.py : VARIABLE direction_seq{direction_seq} --[END DEBUG MSG]')
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
