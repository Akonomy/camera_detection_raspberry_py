import cv2
import numpy as np
import time



directions=[
(1,1,4,[145]), #front right  0
(1,1,10,[145]),  #side right 1
(1,1,10,[140, 190, 140, 190]),  #diagonala right  2

(1,1,3,[145]),  #3
(1,1,9,[145]),   #4
(1,1,9,[190, 140, 190, 140]), #5
(1,1,8,[145]), #rotire dreapta

(1,1,1,[145]), #front
]











def filter_linear_outliers(slices, max_deviation=170):
    # Extract slice indexes and distances from valid points
    valid_points = [(i, d) for i, d, v in slices if v and d is not None]
    if len(valid_points) < 3:
        return slices  # not enough data to filter

    xs, ys = zip(*valid_points)
    xs = np.array(xs)
    ys = np.array(ys)

    # Fit a linear model: y = a*x + b
    A = np.vstack([xs, np.ones(len(xs))]).T
    m, b = np.linalg.lstsq(A, ys, rcond=None)[0]

    # Compute predictions and residuals
    predicted = m * xs + b
    residuals = np.abs(ys - predicted)

    # Mark those with high residuals as invalid
    filtered = []
    for i, (slice_index, distance, valid) in enumerate(slices):
        if valid and distance is not None and (slice_index, distance) in valid_points:
            res = np.abs(distance - (m * slice_index + b))
            if res > max_deviation:
                filtered.append((slice_index, distance, 0))  # mark as invalid
            else:
                filtered.append((slice_index, distance, 1))  # keep
        else:
            filtered.append((slice_index, distance, valid))

    return filtered







def detect_colored_boxes_multi(frames, mosaic_size=128, min_area=50, iou_threshold=0.1):
    """
    frames: list of BGR images (e.g. [img1, img2, img3])
    Returns:
      - merged_boxes: list of (color, (x, y, w, h)) across all frames
      - debug_img: mosaic image (from last frame) with merged boxes drawn
    """
    assert len(frames) >= 1, "Need at least one frame"
    height, width = frames[0].shape[:2]

    raw_boxes = []
    # Process each frame
    for img in frames:
        img= cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        small = cv2.resize(img, (mosaic_size, mosaic_size), interpolation=cv2.INTER_LINEAR)
        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
        color_ranges = {
            'red': [([0, 100, 100], [10, 255, 255]), ([160, 100, 100], [180, 255, 255])],
            'green': [([40, 70, 70], [80, 255, 255])],
            'blue': [([100, 150, 0], [140, 255, 255])]
        }
        for color, ranges in color_ranges.items():
            mask = None
            for lo, hi in ranges:
                m = cv2.inRange(hsv, np.array(lo), np.array(hi))
                mask = m if mask is None else cv2.bitwise_or(mask, m)
            cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in cnts:
                if cv2.contourArea(cnt) > min_area:
                    x, y, w, h = cv2.boundingRect(cnt)
                    # enlarge by 10%
                    pad_x = int(w * 0.1); pad_y = int(h * 0.1)
                    x0 = max(0, x - pad_x)
                    y0 = max(0, y - pad_y)
                    x1 = min(mosaic_size, x + w + pad_x)
                    y1 = min(mosaic_size, y + h + pad_y)
                    w1, h1 = x1 - x0, y1 - y0
                    # scale to original image
                    x_o = int(x0 * width / mosaic_size)
                    y_o = int(y0 * height / mosaic_size)
                    w_o = int(w1 * width / mosaic_size)
                    h_o = int(h1 * height / mosaic_size)
                    raw_boxes.append((color, (x_o, y_o, w_o, h_o)))

    merged_boxes = merge_boxes(raw_boxes, iou_threshold)

    # create debug mosaic image from last frame
    debug_img = cv2.resize(frames[-1], (mosaic_size, mosaic_size))
    for color, (x, y, w, h) in merged_boxes:
        x_m = int(x * mosaic_size / width); y_m = int(y * mosaic_size / height)
        w_m = int(w * mosaic_size / width); h_m = int(h * mosaic_size / height)
        #cv2.rectangle(debug_img, (x_m, y_m), (x_m + w_m, y_m + h_m), (255, 255, 255), 2)
        #cv2.putText(debug_img, color, (x_m, y_m - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

    # scale debug back to original
    #debug_img = cv2.resize(debug_img, (width, height), interpolation=cv2.INTER_NEAREST)

    return merged_boxes

def merge_boxes(boxes, iou_threshold=0.1):
    merged = []
    used = [False] * len(boxes)

    def iou(a, b):
        _, (ax, ay, aw, ah) = a
        _, (bx, by, bw, bh) = b
        x1 = max(ax, bx); y1 = max(ay, by)
        x2 = min(ax + aw, bx + bw); y2 = min(ay + ah, by + bh)
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        union = aw * ah + bw * bh - inter
        return inter / union if union else 0

    for i in range(len(boxes)):
        if used[i]: continue
        col_i, (x, y, w, h) = boxes[i]
        used[i] = True
        group = [(col_i, (x, y, w, h))]
        for j in range(i + 1, len(boxes)):
            if used[j]: continue
            col_j, _ = boxes[j]
            if col_i == col_j and iou(boxes[i], boxes[j]) > iou_threshold:
                group.append(boxes[j])
                used[j] = True
        xs = [b[1][0] for b in group]; ys = [b[1][1] for b in group]
        xs2 = [b[1][0] + b[1][2] for b in group]; ys2 = [b[1][1] + b[1][3] for b in group]
        merged.append((col_i, (min(xs), min(ys), max(xs2)-min(xs), max(ys2)-min(ys))))
    return merged












def get_binary_mosaic_with_exclusion(image, exclude_bottom_ratio=0.35):
    height, width, _ = image.shape
    excl_zone_y = int(height * (1 - exclude_bottom_ratio))

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 90, 255, cv2.THRESH_BINARY_INV)

    small = cv2.resize(binary, (128, 128), interpolation=cv2.INTER_LINEAR)
    mosaic = cv2.resize(small, (width, height), interpolation=cv2.INTER_NEAREST)
    mosaic_colored = cv2.cvtColor(mosaic, cv2.COLOR_GRAY2BGR)

    return mosaic_colored, excl_zone_y

def point_in_box(px, py, boxes):
    for _, (bx, by, bw, bh) in boxes:
        if bx <= px <= bx + bw and by <= py <= by + bh:
            return True
    return False

def analyze_binary_mosaic_with_guidance(image, boxes=[], num_slices=8, exclude_bottom_ratio=0.35, point_spacing=25, min_line_thickness=3):
    mosaic_colored, excl_zone_y = get_binary_mosaic_with_exclusion(image, exclude_bottom_ratio)
    height, width = mosaic_colored.shape[:2]
    center_x = width // 2

    excl_margin = 0.05
    excl_x_start = max(0, int(width * (0.3 - excl_margin)))
    excl_x_end = min(width, int(width * (0.7 + excl_margin)))

    slice_height = height // num_slices
    raw_results = []

    for i in range(num_slices):
        y_start = i * slice_height
        y_end = y_start + slice_height
        band = mosaic_colored[y_start:y_end, :]
        band_gray = cv2.cvtColor(band, cv2.COLOR_BGR2GRAY)
        found = False

        for x in range(0, width - min_line_thickness, point_spacing):
            cx = x + min_line_thickness // 2
            cy = y_start + slice_height // 2

            if i > 4 and (x + min_line_thickness >= excl_x_start and x <= excl_x_end):
                continue
            if i < 5 and excl_zone_y <= cy <= height:
                continue
            if point_in_box(cx, cy, boxes):
                continue

            roi = band_gray[:, x:x + min_line_thickness]
            if cv2.countNonZero(roi) > 3 * min_line_thickness:
                raw_results.append((i, cx - center_x, 1))
                found = True
                break

        if not found:
            raw_results.append((i, None, 0))


     # Apply linear filter
    filtered = filter_linear_outliers(raw_results)

    # Build final result with (x, y) position instead of just validity flag
    detailed_results = []
    for idx, dist, valid in filtered:
        if valid and dist is not None:
            cx = center_x + dist
            cy = idx * slice_height + slice_height // 2
            detailed_results.append((idx, dist, (cx, cy)))
        else:
            detailed_results.append((idx, None, None))

    return mosaic_colored, detailed_results




def pretty_print_slices(slices_data):
    print("//// DATE ---------")
    for slice_index, distance, position in slices_data:
        direction = ""
        if distance is None:
            direction = "NO POINT"
        elif distance < -10:
            direction = f"{distance} px (LEFT)"
        elif distance > 10:
            direction = f"{distance} px (RIGHT)"
        else:
            direction = f"{distance} px (CENTER)"


        print(f"S{slice_index} : {direction} [{position}]")
    print("//// END ---------\n")







######################<CONFIRM FUNCTIONS>#######################





def filter_largest_component(binary_img, min_size=25):
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary_img, connectivity=8)
    mask = np.zeros_like(binary_img)

    for i in range(1, num_labels):  # skip background
        area = stats[i, cv2.CC_STAT_AREA]
        if area >= min_size:
            mask[labels == i] = 255
    return mask


def median_adapt(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    mblur = cv2.medianBlur(gray, 5)
    adapt = cv2.adaptiveThreshold(mblur, 255,
                                  cv2.ADAPTIVE_THRESH_MEAN_C,
                                  cv2.THRESH_BINARY_INV,
                                  11, 3)
    return adapt


def preprocess_binary(binary_img):
    # Remove tiny noise using morphological operations
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    opened = cv2.morphologyEx(binary_img, cv2.MORPH_OPEN, kernel, iterations=2)
    cleaned = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel, iterations=1)
    return cleaned


def detect_line_methods(binary_image, original_image):
    results = {}
    height, width = binary_image.shape
    center_x = width // 2

    cleaned = preprocess_binary(binary_image)

    ## === Contours === ##
    contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    big_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > 150]

    contour_mask = np.zeros_like(cleaned)
    cv2.drawContours(contour_mask, big_contours, -1, 255, -1)

    # Get center of mass for largest contour
    contour_point = None
    if big_contours:
        biggest = max(big_contours, key=cv2.contourArea)
        M = cv2.moments(biggest)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            contour_point = (cx, cy)

    ## === Skeleton === ##
    skel = np.zeros(cleaned.shape, np.uint8)
    element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    img = cleaned.copy()
    while True:
        eroded = cv2.erode(img, element)
        temp = cv2.dilate(eroded, element)
        temp = cv2.subtract(img, temp)
        skel = cv2.bitwise_or(skel, temp)
        img = eroded.copy()
        if cv2.countNonZero(img) == 0:
            break

    skeleton_clean = filter_largest_component(skel)
    skeleton_point = None
    ys, xs = np.where(skeleton_clean > 0)
    if len(xs) > 0:
        cx = int(np.mean(xs))
        cy = int(np.mean(ys))
        skeleton_point = (cx, cy)

    ## === Slice Grouping: HORIZONTAL === ##
    slice_count = 8
    slice_height = height // slice_count
    contour_slices = {i: [] for i in range(slice_count)}
    skeleton_slices = {i: [] for i in range(slice_count)}

    if big_contours:
        for cnt in big_contours:
            for pt in cnt:
                x, y = pt[0]
                slice_idx = min(y // slice_height, slice_count - 1)
                contour_slices[slice_idx].append((x, y))

    for x, y in zip(xs, ys):
        slice_idx = min(y // slice_height, slice_count - 1)
        skeleton_slices[slice_idx].append((x, y))

    ## === Results === ##
    results["contour_mask"] = contour_mask
    results["skeleton_mask"] = skeleton_clean
    results["contour_point"] = contour_point
    results["skeleton_point"] = skeleton_point
    results["contour_slices"] = contour_slices
    results["skeleton_slices"] = skeleton_slices
    results["slice_count"] = slice_count
    results["slice_height"] = slice_height

    if contour_point:
        results["contour_offset"] = contour_point[0] - center_x
    if skeleton_point:
        results["skeleton_offset"] = skeleton_point[0] - center_x

    return results



def confirm_analyzed_points(data, radius=20):
    """
    Confirms analyzed points from `analyze_binary_mosaic_with_guidance` by checking
    for nearby skeleton/contour points from the same slice.

    Args:
        data: output from `extract_dual_data()`
        radius: distance threshold in pixels to consider a match

    Returns:
        List of tuples: (slice_index, deviation, (x, y), confirmed)
    """
    confirmed_results = []

    def is_near(px, py, points, threshold):
        for x, y in points:
            if (x - px)**2 + (y - py)**2 <= threshold**2:
                return True
        return False

    mosaic_points = data["mosaic"]
    contours = data["contour_slices"]
    skeletons = data["skeleton_slices"]

    for slice_idx, deviation, pos in mosaic_points:
        if pos is None:
            confirmed_results.append((slice_idx, deviation, None, False))
            continue

        cx, cy = pos
        confirmed = False
        candidates = contours.get(slice_idx, []) + skeletons.get(slice_idx, [])

        if is_near(cx, cy, candidates, radius):
            confirmed = True

        confirmed_results.append((slice_idx, deviation, pos, confirmed))

    return confirmed_results





def extract_dual_data(image, num_slices=8):
    """
    Processes one image and returns data from both analysis methods:
    - Binary mosaic analysis (returns: [(slice_idx, deviation, (x, y)) or None])
    - Contour/Skeleton slice groups from line detection

    Returns:
        {
            "mosaic": [(slice_index, deviation, (x, y))],
            "contour_slices": {slice_index: [(x, y), ...]},
            "skeleton_slices": {slice_index: [(x, y), ...]},
        }
    """
    # Analyze binary mosaic (ignore mosaic_colored output)
    _, mosaic_data = analyze_binary_mosaic_with_guidance(image, num_slices=num_slices)

    # Prepare image using median threshold
    bin_img = median_adapt(image)

    # Run contour/skeleton detection
    line_results = detect_line_methods(bin_img, image)

    return {
        "mosaic": mosaic_data,
        "contour_slices": line_results["contour_slices"],
        "skeleton_slices": line_results["skeleton_slices"]
    }



import math
from typing import List, Tuple, Optional

# Detection tuple: (slice_index, angle_degrees, (x, y), is_valid)
Detection = Tuple[int, float, Tuple[float, float], bool]


def classify_direction(
    detections: List[Detection],
    image_width: float
) -> Optional[str]:
    """
    Given line detections with angles and validity flags, returns one of:
    RIGHT, DIAGONAL FRONT RIGHT, FRONT, DIAGONAL FRONT LEFT, LEFT,
    DIAGONAL BACK LEFT, BACK, DIAGONAL BACK RIGHT, or None if no valid lines.
    """
    # Filter only the valid detections
    good = [(ang, x) for (_, ang, (x, _), valid) in detections if valid]
    if not good:
        return None

    # Compute circular mean of angles
    sin_sum = sum(math.sin(math.radians(ang)) for ang, _ in good)
    cos_sum = sum(math.cos(math.radians(ang)) for ang, _ in good)
    mean_angle = math.degrees(math.atan2(sin_sum, cos_sum))  # in (–180,180]
    if mean_angle < 0:
        mean_angle += 360  # normalize to [0,360)

    # Compute average x to disambiguate left vs right for vertical-ish lines
    avg_x = sum(x for _, x in good) / len(good)

    # Helper to check if mean_angle is within +/- half_width of a center angle
    def in_arc(angle: float, center: float, width: float = 45.0) -> bool:
        diff = (angle - center + 180) % 360 - 180
        return abs(diff) <= width / 2

    # Direction bins: 0=RIGHT, 90=FRONT, 180=LEFT, 270=BACK
    if in_arc(mean_angle, 0):
        return "LEFT"
    if in_arc(mean_angle, 45):
        return "DIAGONAL FRONT LEFT"
    if in_arc(mean_angle, 90):
        # use avg_x to refine
        if avg_x > image_width * 0.66:
            return "FRONT LEFT"
        if avg_x < image_width * 0.33:
            return "FRONT RIGHT"
        return "FRONT"
    if in_arc(mean_angle, 135):
        return "DIAGONAL FRONT RIGHT"
    if in_arc(mean_angle, 180):
        return "RIGHT"
    if in_arc(mean_angle, 225):
        return "DDFRONT"
    if in_arc(mean_angle, 270):
        return "LLFRONT"
    if in_arc(mean_angle, 315):
        return "AAFRONT"

    return "UNKNOWN"










def get_direction_from_confirmed_results(confirmed_results, image_width=512):
    """
    Converts confirmed_results from confirm_analyzed_points into a direction string
    using classify_direction().

    Args:
        confirmed_results: List of (slice_index, deviation, (x, y), confirmed)
        image_width: Width of the original image

    Returns:
        Direction string or None
    """
    detections = [
        (slice_idx, deviation, pos, confirmed)
        for slice_idx, deviation, pos, confirmed in confirmed_results
        if deviation is not None and pos is not None
    ]

    return classify_direction(detections, image_width)













def new_classify_direction(confirmed_results):
    """
    Take confirmed_results = [(slice_idx, deviation, pos, confirmed), ...]
    and return one of:
      'D1front', 'D3right', 'D10right', 'D17right',
      'D4left', 'D9left', 'D15left'.
    """
    # 1) gather all confirmed deviations
    vals = [dev for (_, dev, _, conf) in confirmed_results
            if conf and dev is not None]
    if not vals:
        # no reliable data → default to rotate
        return directions[6]

    # 2) compute mean
    mean_dev = sum(vals) / len(vals)

    # 3) threshold into buckets
    if -60 < mean_dev <  60:
        return directions[7]

    if mean_dev >= 0:
        if   mean_dev < 140: return directions[0]
        elif mean_dev < 200: return directions[1]
        else:                return directions[2]  #right
    else:
        # mean_dev < 0
        if   mean_dev > -170: return directions[3]
        elif mean_dev > -220: return directions[4]
        else:                 return directions[5]   #left






# directions=[
# (1,1,4,[145]), #front right  0
# (1,1,10,[145]),  #side right 1
# (1,1,10,[140, 190, 140, 190]),  #diagonala right  2

# (1,1,3,[145]),  #3
# (1,1,9,[145]),   #4
# (1,1,9,[190, 140, 190, 140]) #5
# ]



