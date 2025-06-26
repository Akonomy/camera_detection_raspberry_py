
# box_alignment.py

DEFAULT_ZONE_TOP_LEFT = (223, 346)
DEFAULT_ZONE_BOTTOM_RIGHT = (307, 474)

# =============================
# Extrage datele relevante din cutie
# =============================
def extract_box_geometry(pkg_data):
    """
    Primește un dicționar de cutie și extrage poziția și dimensiunea.
    """
    position = pkg_data.get("position")
    size = pkg_data.get("size")

    if not position or not size or None in size:
        raise ValueError("Cutia nu are poziție sau dimensiuni valide.")

    return position, size

# =============================
# Calculează depășirile față de zona de interes
# =============================
def compute_zone_overlap(position, size, zone_top_left=None, zone_bottom_right=None):
    """
    Returnează statusul prezenței cutiei și cât de mult iese din fiecare parte.
    """
    if zone_top_left is None:
        zone_top_left = DEFAULT_ZONE_TOP_LEFT
    if zone_bottom_right is None:
        zone_bottom_right = DEFAULT_ZONE_BOTTOM_RIGHT

    cx, cy = position
    w, h = size
    zx1, zy1 = zone_top_left
    zx2, zy2 = zone_bottom_right

    box_left = cx - w // 2
    box_right = cx + w // 2
    box_top = cy - h // 2
    box_bottom = cy + h // 2

    center_inside = zx1 <= cx <= zx2 and zy1 <= cy <= zy2

    # Cât de mult depășește fiecare limită (dacă e sub 0 => nu depășește)
    overlaps = [
        max(0, zy1 - box_top),     # Top
        max(0, box_right - zx2),   # Right
        max(0, box_bottom - zy2),  # Bottom
        max(0, zx1 - box_left)     # Left
    ]

    return "INSIDE" if center_inside else "OUTSIDE", overlaps

# =============================
# Evaluare finală cu tresholduri
# =============================
def evaluate_box_alignment(pkg_data, 
                           zone_top_left=None, 
                           zone_bottom_right=None,
                           thresholds=(30, 6, 6, 6)):
    """
    Primește cutia, evaluează dacă e PASS/CLOSE/REJECTED și cât depășește.
    thresholds = (top, right, bottom, left)
    """
    position, size = extract_box_geometry(pkg_data)
    status, overlaps = compute_zone_overlap(position, size, zone_top_left, zone_bottom_right)

    if status == "OUTSIDE":
        return ["REJECTED", overlaps]

    # Verificăm dacă există vreo depășire peste treshold
    for i in range(4):
        if overlaps[i] > thresholds[i]:
            return ["CLOSE", overlaps]

    # Dacă toate sunt sub sau egale cu treshold => PASS
    return ["PASS", overlaps]



def find_closest_box(session, target_color=None, reference_point=(261, 433)):
    closest_box = None
    min_distance = float('inf')

    for pkg_id, pkg in session.items():
        color_match = target_color is None or pkg.get("box_color") == target_color
        pos = pkg.get("position")

        if color_match and pos:
            distance = ((pos[0] - reference_point[0]) ** 2 + (pos[1] - reference_point[1]) ** 2) ** 0.5
            if distance < min_distance:
                min_distance = distance
                closest_box = pkg

    return closest_box.get("position") if closest_box else None






def evaluate_target_box(session, target_color, target_letter,
                        reference_point=(261, 433),
                        zone_top_left=(223, 346),
                        zone_bottom_right=(307, 474),
                        thresholds=(30, 6, 6, 6)):
    """
    Caută cutia după culoare și literă, dacă nu există caută cea mai apropiată cutie de culoarea cerută,
    altfel cea mai apropiată cutie overall. Returnează statusul și overlaps.

    Returns:
        (label, status, overlaps) dacă se găsește cutie, altfel (None, None, None)
    """
    target_pkg = None

    # 1. Cutia cu litera și culoarea cerută
    for pkg in session.values():
        if pkg.get("box_color") == target_color and target_letter in pkg.get("letters", []):
            target_pkg = pkg
            break

    # 2. Cea mai apropiată cutie cu culoarea cerută
    if not target_pkg:
        closest_pos = find_closest_box(session, target_color=target_color, reference_point=reference_point)
        for pkg in session.values():
            if pkg.get("position") == closest_pos and pkg.get("box_color") == target_color:
                target_pkg = pkg
                break

    # 3. Cea mai apropiată cutie din sesiune
    if not target_pkg:
        closest_pos = find_closest_box(session, reference_point=reference_point)
        for pkg in session.values():
            if pkg.get("position") == closest_pos:
                target_pkg = pkg
                break

    if not target_pkg:
        return None, None, None

    label = f"{target_pkg.get('box_color')}{target_letter if target_letter in target_pkg.get('letters', []) else '?'}"
    status, overlaps = evaluate_box_alignment(
        target_pkg,
        zone_top_left=zone_top_left,
        zone_bottom_right=zone_bottom_right,
        thresholds=thresholds
    )

    return label, status, overlaps
