import numpy as np

def filter_close_points(points, distance_threshold=4, size_threshold=4):
    """
    Filters duplicate detections by clustering close points and averaging them.
    
    Args:
        points: List of detected bounding boxes (x, y, width, height, class).
        distance_threshold: Maximum difference in (x, y) positions to consider duplicates.
        size_threshold: Maximum difference in (width, height) to consider duplicates.

    Returns:
        A filtered list of unique bounding boxes.
    """
    if not points:
        return []

    filtered_points = []
    used_indices = set()

    for i, point in enumerate(points):
        if i in used_indices:
            continue

        cluster = [point]
        used_indices.add(i)

        for j, other_point in enumerate(points):
            if j != i and j not in used_indices:
                if (abs(point[0] - other_point[0]) <= distance_threshold and
                    abs(point[1] - other_point[1]) <= distance_threshold and
                    abs(point[2] - other_point[2]) <= size_threshold and
                    abs(point[3] - other_point[3]) <= size_threshold and
                    point[4] == other_point[4]):  # Ensure same class
                
                    cluster.append(other_point)
                    used_indices.add(j)

        # Compute the median values for a better approximation
        median_x = int(np.median([p[0] for p in cluster]))
        median_y = int(np.median([p[1] for p in cluster]))
        median_width = int(np.median([p[2] for p in cluster]))
        median_height = int(np.median([p[3] for p in cluster]))
        max_class = cluster[0][4]  # Keep the same class

        filtered_points.append((median_x, median_y, median_width, median_height, max_class))

    return filtered_points
    
    
    
    
    
    
    


def assign_letters_to_packages(letters, packages, threshold=5):
    """
    Assigns letters to the nearest detected package (box).
    
    Args:
        letters: List of detected letters ({"label", "x", "y", "width", "height"}).
        packages: List of detected packages ({"label", "x", "y", "width", "height"}).
        threshold: Maximum distance allowed for a letter to be considered inside a package.

    Returns:
        List of matched packages with their letters.
    """

    matched_packages = []

    for package in packages:
        package_x, package_y, package_w, package_h = package["x"], package["y"], package["width"], package["height"]
        package_top_left = (package_x - package_w // 2, package_y - package_h // 2)
        package_bottom_right = (package_x + package_w // 2, package_y + package_h // 2)

        assigned_letters = []

        for letter in letters:
            letter_x, letter_y, letter_w, letter_h = letter["x"], letter["y"], letter["width"], letter["height"]
            letter_top_left = (letter_x - letter_w // 2, letter_y - letter_h // 2)
            letter_bottom_right = (letter_x + letter_w // 2, letter_y + letter_h // 2)

            # Check if letter is inside package (with some threshold tolerance)
            if (package_top_left[0] - threshold <= letter_top_left[0] and
                package_top_left[1] - threshold <= letter_top_left[1] and
                package_bottom_right[0] + threshold >= letter_bottom_right[0] and
                package_bottom_right[1] + threshold >= letter_bottom_right[1]):
                assigned_letters.append(letter["label"])

        # If at least one letter is inside, append result
        if True:
            matched_packages.append({
                "package_label": package["label"],
                "package_x": package_x,
                "package_y": package_y,
                "letters": assigned_letters
            })

    return matched_packages




def calculate_box_distance(boxes, zone_center, pass_threshold=5, max_distance=20):
    """
    Calculates the distance from each detected package (box) to the center of the defined zone.
    
    Args:
        boxes: List of detected packages ({"label", "x", "y", "width", "height"}).
        zone_center: Tuple (x, y) representing the center of the defined zone.
        pass_threshold: Distance threshold to consider a package as "PASS".
        max_distance: Maximum distance to still consider the package as valid.

    Returns:
        List of dictionaries containing box information with distance from the zone.
    """

    results = []
    
    for box in boxes:
        box_center = (box["x"], box["y"])
        
        # Calculate Euclidean distance
        distance = np.sqrt((box_center[0] - zone_center[0])**2 + (box_center[1] - zone_center[1])**2)
        
        # Determine if the package is within the acceptable range
        if distance <= pass_threshold:
            status = "PASS"
        elif distance > max_distance:
            status = "REJECTED"
        else:
            status = "CLOSE"

        results.append({
            "package_label": box["label"],
            "package_x": box["x"],
            "package_y": box["y"],
            "distance": round(distance, 2),  # Round to 2 decimal places
            "status": status
        })
    
    return results
    
    

# BOX_DETECT/utils.py

def build_session_data(matched_packages, box_distances, detections_boxes):
    """
    Build a dictionary (session_data) that contains info about each detected package.
    
    Args:
        matched_packages: List of dicts from assign_letters_to_packages
            e.g., [{'letters': [...], 'package_label': 'Green', 'package_x': 123, 'package_y': 456}, ...]
        box_distances: List of dicts with distance info
            e.g., [{'package_label': 'Green', 'package_x': ..., 'package_y': ..., 'distance': ..., 'status': ...}, ...]
        detections_boxes: List of raw box detections from detect_objects()
            e.g., [{'label': 'Green', 'x': 123, 'y': 456, 'width': 50, 'height': 60}, ...]
    
    Returns:
        session_data: A dict mapping "PACKAGE1", "PACKAGE2", ...
        to a dict with keys: ["box_color", "letters", "position", "size", "distance", "status"]
    """
    session_data = {}
    package_index = 1

    def find_box_info(box_distances_list, pkg):
        for box in box_distances_list:
            same_label = (box['package_label'] == pkg['package_label'])
            same_position = (box['package_x'] == pkg['package_x'] and 
                             box['package_y'] == pkg['package_y'])
            if same_label and same_position:
                return box
        return None

    for pkg in matched_packages:
        # Remove duplicate letters from the list (if any)
        unique_letters = list(set(pkg["letters"]))

        # Find the matching distance data
        box_info = find_box_info(box_distances, pkg)

        # Find the matching detection in detections_boxes to get width/height
        box_detection = next(
            (
                d for d in detections_boxes
                if d["label"] == pkg["package_label"]
                and d["x"] == pkg["package_x"]
                and d["y"] == pkg["package_y"]
            ),
            None
        )

        if box_info and box_detection:
            package_data = {
                "box_color": pkg["package_label"],
                "letters": unique_letters,
                "position": (pkg["package_x"], pkg["package_y"]),
                "size": (box_detection["width"], box_detection["height"]),
                "distance": box_info["distance"],
                "status": box_info["status"]
            }
        else:
            package_data = {
                "box_color": pkg["package_label"],
                "letters": unique_letters,
                "position": (pkg["package_x"], pkg["package_y"]),
                "size": (None, None),
                "distance": None,
                "status": "UNKNOWN"
            }

        session_data[f"PACKAGE{package_index}"] = package_data
        package_index += 1

    return session_data


def get_high_priority_package(session_data):
    """
    Returns (package_key, package_info) for the highest-priority package 
    based on:
      1) Smallest distance (primary),
      2) Color priority (secondary),
      3) Letter priority (tertiary).

    If no packages, returns (None, None).
    If letters are missing, letter priority is set to a default (e.g. 999),
    but that won't matter if the distance difference is large enough.

    Priority order by color (lowest rank = highest priority):
        Blue=1, Red=2, Sample=3, Green=4

    Priority order by letter (lowest rank = highest priority):
        A=1, K=2, O=3
        (If no letters, rank=999)

    This ensures a very close package with no letters 
    can still win if it's significantly closer than others.
    """

    if not session_data:
        return None, None  # No packages at all

    # Define color priority (1 is highest)
    color_priority_map = {
        "Blue": 1,
        "Red": 2,
        "Sample": 3,
        "Green": 4
    }

    # Define letter priority (1 is highest)
    letter_priority_map = {
        "A": 1,
        "K": 2,
        "O": 3
    }

    def get_letter_rank(letters):
        if not letters:
            return 999  # If no letter is found, treat as lowest letter priority
        best_rank = 999
        for lt in letters:
            rank = letter_priority_map.get(lt, 999)
            if rank < best_rank:
                best_rank = rank
        return best_rank

    # Gather valid packages (must have a distance)
    valid_packages = [
        (pkg_key, pkg_info)
        for pkg_key, pkg_info in session_data.items()
        if pkg_info.get("distance") is not None
    ]
    if not valid_packages:
        return None, None

    # Build a list for sorting:
    # (distance, color_rank, letter_rank, pkg_key, pkg_info)
    sortable_list = []
    for pkg_key, pkg_info in valid_packages:
        dist   = pkg_info["distance"]
        color  = pkg_info["box_color"]
        letters = pkg_info["letters"]

        color_rank  = color_priority_map.get(color, 999)
        letter_rank = get_letter_rank(letters)

        sortable_list.append((dist, color_rank, letter_rank, pkg_key, pkg_info))

    # Sort ascending by distance, then color rank, then letter rank
    sortable_list.sort(key=lambda x: (x[0], x[1], x[2]))

    # The first entry is the best
    _, _, _, best_pkg_key, best_pkg_info = sortable_list[0]
    return best_pkg_key, best_pkg_info



def old_get_high_priority_package(session_data):
    """
    Given a session_data dictionary with structure:
        {
            "PACKAGE1": {
                "box_color": ...,
                "letters": [...],
                "position": (...),
                "size": (...),
                "distance": ...,
                "status": ...
            },
            "PACKAGE2": {...},
            ...
        }
    Returns (package_key, package_info) for the highest-priority package 
    based primarily on the *smallest distance*, then breaks ties
    among packages that are within +10 distance units by color > letter.

    Priority order by color (lowest rank = highest priority):
        1) Blue
        2) Red
        3) Sample
        4) Green

    If multiple packages share the same color, priority by letter:
        1) A
        2) K
        3) O

    If no packages or no valid distances, returns (None, None).
    """

    if not session_data:
        return None, None  # No packages

    # Define color priority (1 is highest)
    color_priority_map = {
        "Blue": 1,
        "Red": 2,
        "Sample": 3,
        "Green": 4
    }

    # Define letter priority (1 is highest)
    letter_priority_map = {
        "A": 1,
        "K": 2,
        "O": 3
    }

    def get_letter_rank(letters_list):
        """
        Among possibly multiple letters, pick the highest priority (lowest rank).
        If no letters, return a large rank (lowest priority).
        """
        if not letters_list:
            return 999
        best_rank = 999
        for letter in letters_list:
            rank = letter_priority_map.get(letter, 999)  # default if unknown
            if rank < best_rank:
                best_rank = rank
        return best_rank

    # ------------------------------------------------------
    # 1) Find the minimum distance among all valid packages
    # ------------------------------------------------------
    valid_packages = [(pkg_key, pkg_info) 
                      for pkg_key, pkg_info in session_data.items()
                      if pkg_info.get("distance") is not None]

    if not valid_packages:
        # No valid distances
        return None, None

    d_min = min(pkg_info["distance"] for _, pkg_info in valid_packages)

    # ------------------------------------------------------
    # 2) Gather the subset of packages with distance ≤ d_min + 10
    # ------------------------------------------------------
    threshold = d_min + 10
    candidate_packages = [
        (pkg_key, pkg_info)
        for pkg_key, pkg_info in valid_packages
        if pkg_info["distance"] <= threshold
    ]

    # ------------------------------------------------------
    # 3) Among these candidates, pick highest color/letter priority
    # ------------------------------------------------------
    best_priority_tuple = (999, 999, None, None)  # (color_rank, letter_rank, pkg_key, pkg_info)

    for pkg_key, pkg_info in candidate_packages:
        color   = pkg_info["box_color"]
        letters = pkg_info["letters"]

        color_rank  = color_priority_map.get(color, 999)
        letter_rank = get_letter_rank(letters)

        current_tuple = (color_rank, letter_rank, pkg_key, pkg_info)
        if current_tuple < best_priority_tuple:
            best_priority_tuple = current_tuple

    _, _, best_pkg_key, best_pkg_info = best_priority_tuple

    if best_pkg_key is None:
        return None, None
    return best_pkg_key, best_pkg_info


    def get_letter_rank(letters_list):
        """
        Among possibly multiple letters, pick the highest priority (lowest rank).
        If no letters, return a large rank (lowest priority).
        """
        if not letters_list:
            return 999  # No letters => lowest priority

        best_rank = 999
        for letter in letters_list:
            rank = letter_priority_map.get(letter, 999)  # default if unknown
            if rank < best_rank:
                best_rank = rank
        return best_rank

    best_priority_tuple = (999, 999, None, None)  # (color_rank, letter_rank, pkg_key, pkg_info)

    for pkg_key, pkg_info in session_data.items():
        color  = pkg_info["box_color"]
        letters = pkg_info["letters"]

        c_rank = color_priority_map.get(color, 999)
        l_rank = get_letter_rank(letters)

        current_priority = (c_rank, l_rank, pkg_key, pkg_info)
        if current_priority < best_priority_tuple:
            best_priority_tuple = current_priority

    _, _, best_pkg_key, best_pkg_info = best_priority_tuple

    if best_pkg_key is None:
        return None, None

    return best_pkg_key, best_pkg_info




# BOX_DETECT/utils.py

def update_tracked_package(tracked_pkg, session_data, distance_threshold=150):
    """
    Attempts to find a package in session_data that matches
    the tracked_pkg by color and letters.

    Args:
        tracked_pkg: A dict containing info about the tracked package,
                     including 'box_color', 'letters', and 'distance'.
        session_data: The dict built by build_session_data(...),
                      e.g. { "PACKAGE1": { ... }, "PACKAGE2": { ... }, ... }
        distance_threshold: Max allowed change in distance before we discard tracking.

    Returns:
        updated_pkg: A dict with updated info (e.g., new position, distance, status)
                     plus 'miss_detections' = 0, if matched and within threshold.
        False: If package is not found at all (by color+letters).
        "TOO_FAR": If found a matching color+letters but the distance jumped too much.
    """
    tracked_color = tracked_pkg['box_color']
    tracked_letters_set = set(tracked_pkg['letters'])
    old_distance = tracked_pkg.get("distance")

    for pkg_key, pkg_info in session_data.items():
        # Check color match
        if pkg_info['box_color'] == tracked_color:
            # Check letters match as a set
            current_letters_set = set(pkg_info['letters'])
            if current_letters_set == tracked_letters_set:
                # We found a potential match
                new_distance = pkg_info.get("distance")
                if old_distance is not None and new_distance is not None:
                    # Check if distance changed drastically
                    if abs(new_distance - old_distance) > distance_threshold:
                        # Return special marker => too big a jump
                        return "TOO_FAR"

                # Otherwise, this is a valid update => merge data
                updated_pkg = pkg_info.copy()
                updated_pkg['miss_detections'] = 0  # reset missing detection
                return updated_pkg

    # If we reach here, no match was found
    return False



def compute_movement_command(
    box_position, 
    zone_center, 
    grid_size=8, 
    x_tolerance=0, 
    y_tolerance=0
):
    """
    Given the (x,y) of a box and the (x,y) of the zone center in an image,
    returns a suggested movement command so the robot can bring the box
    into the 'PASS' zone.

    Args:
        box_position: (x, y) of the box in the image.
        zone_center: (cx, cy) of the 'defined zone' center.
        grid_size: number of pixels representing one 'grid' move in x or y.
        x_tolerance: how close (in grid units) we want x to be before we consider it aligned.
        y_tolerance: how close (in grid units) we want y to be before we consider it aligned.

    Returns:
        A list of strings describing movement suggestions.
        e.g., ["RIGHT 2", "FORWARD 1"]
        If no movement needed, returns an empty list [].
    """
    box_x, box_y = box_position
    center_x, center_y = zone_center

    # How many pixels away in x and y
    dx_pixels = box_x - center_x  # +ve => box is to the right
    dy_pixels = box_y - center_y  # +ve => box is below

    # Convert to grid units (round so it’s easy for the robot)
    dx_grids = round(dx_pixels / grid_size)
    dy_grids = round(dy_pixels / grid_size)

    # We'll build commands in a list
    commands = []

    # Check horizontal direction
    # If dx_grids is positive => box is to the right => move RIGHT
    # If dx_grids is negative => box is to the left => move LEFT
    if abs(dx_grids) > x_tolerance:
        if dx_grids > 0:
            commands.append(f"LEFT {abs(dx_grids)}")
        else:
            commands.append(f"RIGHT {abs(dx_grids)}")

    # Check vertical direction
    # Typically, smaller y means "further up" in the image. We'll define
    # negative dy => box is above the center => move FORWARD
    # positive dy => box is below the center => move BACK
    if abs(dy_grids) > y_tolerance:
        if dy_grids > 0:
            commands.append(f"FORWARD {abs(dy_grids)}")
        else:
            commands.append(f"BACK {abs(dy_grids)}")

    return commands



def fine_adjustment_command(
    package_info,
    zone_top_left,
    zone_bottom_right,
    margin=0
):
    """
    Given a package's bounding box (from package_info) and the zone bounding box,
    returns small "LITTLE_*" movement suggestions if ANY part of the box
    is outside the zone (plus some margin). This ensures we gradually move
    the box so it's fully contained within the zone edges.

    Args:
        package_info: dict with keys:
            {
                "position": (x, y),
                "size": (width, height),
                ...
            }
        zone_top_left: (zx1, zy1)
        zone_bottom_right: (zx2, zy2)
        margin: extra space around the zone to treat as "close enough"

    Returns:
        A list of strings describing small movement suggestions, e.g.:
        ["LITTLE_RIGHT", "LITTLE_FORWARD"].

        If the box is fully within these boundaries (plus margin),
        returns an empty list [].
    """

    px, py = package_info["position"]
    w, h = package_info["size"]

    if w is None or h is None:
        # If we have no bounding box size, we can't do a precise check
        return []

    # Compute the bounding box of the package
    box_left   = px - w // 2
    box_right  = px + w // 2
    box_top    = py - h // 2
    box_bottom = py + h // 2

    # Unpack the zone bounding box
    zone_left, zone_top_y = zone_top_left
    zone_right, zone_bottom_y = zone_bottom_right

    # Adjust the zone with a margin
    z_left   = zone_left   - margin
    z_right  = zone_right  + margin
    z_top    = zone_top_y  - margin
    z_bottom = zone_bottom_y + margin

    movements = []

    # Check if the box extends beyond the left zone boundary
    if box_left < z_left:
        # The box is partially (or fully) off to the left => move right
        movements.append("LITTLE_RIGHT")

    # Check if the box extends beyond the right zone boundary
    elif box_right > z_right:
        # The box is partially off to the right => move left
        movements.append("LITTLE_LEFT")

    # Check if the box extends beyond the top zone boundary
    # Smaller y => 'higher' in the image => typically means "move FORWARD"
    if box_top < z_top:
        movements.append("LITTLE_BACK")

    # Check if the box extends beyond the bottom zone boundary
    # Bigger y => 'lower' => typically "move BACK"
    elif box_bottom > z_bottom:
        movements.append("LITTLE_FORWARD")

    return movements

