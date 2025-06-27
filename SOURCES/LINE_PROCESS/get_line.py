import cv2
import numpy as np
import time







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

    # Draw only filtered valid points
    for idx, dist, valid in filtered:
        if valid and dist is not None:
            cx = center_x + dist
            cy = idx * slice_height + slice_height // 2
            cv2.circle(mosaic_colored, (cx, cy), 5, (255, 0, 255), -1)

    return mosaic_colored, filtered











def pretty_print_slices(slices_data):
    print("//// DATE ---------")
    for slice_index, distance, valid in slices_data:
        direction = ""
        if distance is None:
            direction = "NO POINT"
        elif distance < -10:
            direction = f"{distance} px (LEFT)"
        elif distance > 10:
            direction = f"{distance} px (RIGHT)"
        else:
            direction = f"{distance} px (CENTER)"

        status = "✓" if valid else "X"
        print(f"S{slice_index} : {direction} [{status}]")
    print("//// END ---------\n")

