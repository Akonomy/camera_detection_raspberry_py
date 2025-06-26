import cv2
from picamera2 import Picamera2

import os
import sys

# Adaugă directorul părinte la sys.path pentru a putea importa modulele din BOX_DETECT și UTILS
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)



from BOX_DETECT.letter_detect import detect_letters
from BOX_DETECT.box_detect import detect_objects
from BOX_DETECT.utils import assign_letters_to_packages, calculate_box_distance

# Initialize the camera
picam2 = Picamera2()
picam2.configure(picam2.create_still_configuration())
picam2.start()

# Define the zone center based on the defined zone bounds
zone_top_left = (200, 40)
zone_bottom_right = (295, 160)
zone_center = ((zone_top_left[0] + zone_bottom_right[0]) // 2,
               (zone_top_left[1] + zone_bottom_right[1]) // 2)  # Compute center

# Define priority order for colors and letters
color_priority = ["Green", "Red", "Sample", "Blue"]
letter_priority = ["A", "K", "O"]

# Tracked box information
tracked_box = None

# Function to add a grid overlay to the image
def add_grid(image, grid_size=64):
    h, w = image.shape[:2]
    for x in range(0, w, grid_size):  
        cv2.line(image, (x, 0), (x, h), (255, 255, 255), 1)  
    for y in range(0, h, grid_size):  
        cv2.line(image, (0, y), (w, y), (255, 255, 255), 1)  

# Function to mark the defined zone
def mark_zone(image, top_left, bottom_right, label="Zone", color=(0, 0, 255), thickness=2):
    cv2.rectangle(image, top_left, bottom_right, color, thickness)
    label_position = (top_left[0], top_left[1] - 10)
    cv2.putText(image, label, label_position, cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

# Function to draw bounding boxes on the image
def draw_detections(image, detections, color_map, tracked_box):
    """
    Draws detected bounding boxes on the image.

    Args:
        image: The frame on which to draw.
        detections: List of detected objects.
        color_map: Dictionary mapping labels to BGR color values.
        tracked_box: The currently tracked box to highlight.
    """
    for obj in detections:
        x, y, width, height = obj["x"], obj["y"], obj["width"], obj["height"]
        label = obj["label"]
        color = color_map.get(label, (255, 255, 255))  # Default to white

        # Define the bounding box corners
        top_left = (x - width // 2, y - height // 2)
        bottom_right = (x + width // 2, y + height // 2)

        # Highlight tracked box in CYAN
        if tracked_box and obj["x"] == tracked_box["x"] and obj["y"] == tracked_box["y"]:
            color = (255, 255, 0)  # Cyan

        # Draw bounding box
        cv2.rectangle(image, top_left, bottom_right, color, 2)

        # Add label text
        cv2.putText(image, label, (x + 5, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

# Define colors for different detections
color_map = {
    "A": (0, 255, 0),     
    "K": (255, 0, 255),    
    "O": (255, 255, 255),  
    "Green": (0, 255, 0),  
    "Red": (0, 0, 255),    
    "Sample": (255, 255, 255),  
    "Blue": (255, 0, 0)    
}

# Main loop for real-time visualization
while True:
    # Capture an image
    image = picam2.capture_array()

    # Resize and rotate for proper orientation
    image = cv2.resize(image, (512, 512))
    image = cv2.rotate(image, cv2.ROTATE_180)

    # Run both detections
    detections_letters = detect_letters(picam2)
    detections_boxes = detect_objects(picam2)

    # Assign letters to their respective packages
    matched_packages = assign_letters_to_packages(detections_letters, detections_boxes, threshold=5)

    # Calculate distances from zone center
    box_distances = calculate_box_distance(detections_boxes, zone_center, pass_threshold=20, max_distance=30)

    # Select the best box to track
    if tracked_box is None or tracked_box["status"] == "PASS":
        tracked_box = None  # Reset if the previous box reached PASS

        # Sort boxes based on color priority, then distance
        sorted_boxes = sorted(box_distances, key=lambda b: (color_priority.index(b["package_label"]), b["distance"]))

        if sorted_boxes:
            tracked_box = sorted_boxes[0]  # Select the best box to track

    # Draw detected bounding boxes
    draw_detections(image, detections_letters + detections_boxes, color_map, tracked_box)

    # Mark the defined zone
    mark_zone(image, zone_top_left, zone_bottom_right, label="Defined Zone")

    # Add grid overlay
    add_grid(image)

    # Show the frame with detections
    cv2.imshow("Detection Output", cv2.cvtColor(image, cv2.COLOR_RGB2BGR))

    # Print tracked box details
    if tracked_box:
        print(f"\n🚀 Tracking {tracked_box['package_label']} at ({tracked_box['package_x']}, {tracked_box['package_y']})")

    # Print letter-to-package assignments
    for package in matched_packages:
        print(f"{package['letters']} -> {package['package_label']} at ({package['package_x']}, {package['package_y']})")

    # Print distance information
    for box in box_distances:
        print(f"{box['package_label']} at ({box['package_x']}, {box['package_y']}) -> Distance: {box['distance']} | Status: {box['status']}")

    # Automatically continue without requiring key press
    cv2.waitKey(1)
