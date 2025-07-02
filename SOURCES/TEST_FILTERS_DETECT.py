import cv2
import numpy as np
import time
from CAMERA.camera_session import init_camera, stop_camera, capture_raw_image

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



def show_grid_with_titles(images_dict, tile_width=320, slice_count=8):
    keys = list(images_dict.keys())
    images = list(images_dict.values())

    resized = [cv2.resize(img, (tile_width, tile_width)) for img in images]

# Draw horizontal slice lines and labels on each image
    for img in resized:
        slice_height = tile_width // slice_count
        for i in range(1, slice_count):
            y = i * slice_height
            cv2.line(img, (0, y), (tile_width, y), (0, 255, 255), 1)
        for i in range(slice_count):
            label_y = i * slice_height + 20
            cv2.putText(img, str(i), (5, label_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,0), 1)

    cols = 3
    rows = (len(resized) + cols - 1) // cols

    while len(resized) < rows * cols:
        resized.append(np.zeros_like(resized[0]))

    grid_rows = [np.hstack(resized[i*cols:(i+1)*cols]) for i in range(rows)]
    full_grid = np.vstack(grid_rows)

    for i, key in enumerate(keys):
        r = i // cols
        c = i % cols
        x = c * tile_width + 10
        y = r * tile_width + 30
        cv2.putText(full_grid, key, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)

    return full_grid



def loop_preview():
    init_camera()
    while True:
        frame = capture_raw_image()
        if frame is None:
            print("Camera nu a returnat nimic.")
            break

        med_adapt = median_adapt(frame)
        results = detect_line_methods(med_adapt, frame)

        print("\n--- Contour Slice Points ---")
        for i, points in results["contour_slices"].items():
            print(f"Slice {i}: {len(points)} points")
            if points:
                print(f"  Example: {points[:5]}")  # Show first 5 for brevity

        print("\n--- Skeleton Slice Points ---")
        for i, points in results["skeleton_slices"].items():
            print(f"Slice {i}: {len(points)} points")
            if points:
                print(f"  Example: {points[:5]}")



        # Debug
        if results["contour_point"]:
            print("Contour: ", results["contour_point"], "Offset:", results["contour_offset"])
        if results["skeleton_point"]:
            print("Skeleton:", results["skeleton_point"], "Offset:", results["skeleton_offset"])

        display_data = {
            "original": frame,
            "contour": cv2.cvtColor(results["contour_mask"], cv2.COLOR_GRAY2BGR),
            "skeleton": cv2.cvtColor(results["skeleton_mask"], cv2.COLOR_GRAY2BGR)
        }
        grid = show_grid_with_titles(display_data)


       # grid = show_grid_with_titles(results)
        cv2.imshow("Line Detection Preview", grid)

        key = cv2.waitKey(100)
        if key == 27:  # ESC
            break

    cv2.destroyAllWindows()

loop_preview()
