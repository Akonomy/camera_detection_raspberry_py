import cv2
import math
import numpy as np
from collections import Counter

def quantize_angle(a):
    """
    Quantizes an angle (in degrees) into one of the discrete levels: 0, 15, 25, 35, or 45.
    """
    a = abs(a)
    # Adjust to get an effective angle between 0 and 45 degrees
    if a > 45:
        a = 90 - a
    if a < 7.5:
        return 0
    elif a < 20:
        return 15
    elif a < 27.5:
        return 25
    elif a < 37.5:
        return 35
    else:
        return 45

def get_box_inclination_angle(image, tracked_pkg, margin=10, debug=False):
    """
    Processes a given image copy and tracked package info to compute the inclination angle.
    
    It extracts the ROI based on the tracked package’s bounding box (plus a margin),
    performs preprocessing (grayscale conversion, Gaussian blur, Canny edge detection),
    and detects lines using the Hough transform. The detected line angles are then
    quantized to discrete values, and the most common value is returned as the inclination angle.
    
    :param image: A copy of the image (numpy array) to be processed.
    :param tracked_pkg: Dictionary with at least "position" (tuple) and "size" (tuple) keys.
    :param margin: Extra margin (in pixels) added around the bounding box for ROI extraction.
    :param debug: If True, shows the ROI with detected lines.
    :return: The quantized inclination angle (int) for the tracked package.
    """
    x, y = tracked_pkg["position"]
    if tracked_pkg.get("size") is not None and None not in tracked_pkg.get("size"):
        w, h = tracked_pkg["size"]
    else:
        w, h = 50, 50  # Default dimensions if not provided

    # Define ROI boundaries based on package position and size plus margin
    roi_x1 = max(0, int(x - w / 2 - margin))
    roi_y1 = max(0, int(y - h / 2 - margin))
    roi_x2 = min(image.shape[1], int(x + w / 2 + margin))
    roi_y2 = min(image.shape[0], int(y + h / 2 + margin))
    
    roi = image[roi_y1:roi_y2, roi_x1:roi_x2]
    roi_h, roi_w = roi.shape[:2]
    
    # Preprocess ROI: convert to grayscale, apply blur, and detect edges
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    
    # Detect lines with the probabilistic Hough transform
    lines = cv2.HoughLinesP(edges, 1, math.pi/180, threshold=30,
                            minLineLength=roi_w // 4, maxLineGap=10)
    
    raw_angles = []
    quantized_angles = []
    
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle_deg = math.degrees(math.atan2(y2 - y1, x2 - x1))
            # Normalize angle to the range [-90, 90]
            if angle_deg > 90:
                angle_deg -= 180
            elif angle_deg < -90:
                angle_deg += 180
            raw_angles.append(angle_deg)
            quantized_angles.append(quantize_angle(angle_deg))
            if debug:
                cv2.line(roi, (x1, y1), (x2, y2), (0, 255, 0), 2)
    else:
        quantized_angles = [0]  # Default if no lines are found

    # Determine the most frequent (mode) quantized angle
    if quantized_angles:
        final_orientation = Counter(quantized_angles).most_common(1)[0][0]
    else:
        final_orientation = 0
    
    if debug:
        cv2.imshow("Debug ROI", roi)
        cv2.waitKey(0)
        cv2.destroyWindow("Debug ROI")
    
    return final_orientation
