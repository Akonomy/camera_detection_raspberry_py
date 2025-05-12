import cv2
from picamera2 import Picamera2

# Detection modules
from BOX_DETECT.letter_detect import detect_letters
from BOX_DETECT.box_detect import detect_objects

# Utility functions
from BOX_DETECT.utils import (
    assign_letters_to_packages,
    calculate_box_distance,
    build_session_data,
    get_high_priority_package,
    update_tracked_package,
    compute_movement_command,
    fine_adjustment_command
)

# --------------------------------------------------
# CAMERA + ZONE SETUP
# --------------------------------------------------
picam2 = Picamera2()
picam2.configure(picam2.create_still_configuration())
picam2.start()

zone_top_left = (200, 40)
zone_bottom_right = (295, 160)
zone_center = ((zone_top_left[0] + zone_bottom_right[0]) // 2,
               (zone_top_left[1] + zone_bottom_right[1]) // 2)

# --------------------------------------------------
# DRAWING HELPERS
# --------------------------------------------------
def add_grid(image, grid_size=64):
    h, w = image.shape[:2]
    for x in range(0, w, grid_size):
        cv2.line(image, (x, 0), (x, h), (255, 255, 255), 1)
    for y in range(0, h, grid_size):
        cv2.line(image, (0, y), (w, y), (255, 255, 255), 1)

def mark_zone(image, top_left, bottom_right, label="Zone", color=(0, 0, 255), thickness=2):
    cv2.rectangle(image, top_left, bottom_right, color, thickness)
    label_position = (top_left[0], top_left[1] - 10)
    cv2.putText(image, label, label_position, cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

def draw_detections(image, detections, color_map):
    for obj in detections:
        x, y = obj["x"], obj["y"]
        w, h = obj["width"], obj["height"]
        label = obj["label"]
        color = color_map.get(label, (255, 255, 255))

        # Draw bounding box
        top_left = (x - w // 2, y - h // 2)
        bottom_right = (x + w // 2, y + h // 2)
        cv2.rectangle(image, top_left, bottom_right, color, 2)

        # Add label text
        cv2.putText(image, label, (x + 5, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

def draw_tracked_package(image, tracked_pkg, color=(255, 255, 0)):
    """
    Draw a special bounding box or point for the tracked package in CYAN by default.
    """
    x, y = tracked_pkg["position"]
    w, h = tracked_pkg["size"]
    box_label = f"TRACKED: {tracked_pkg['box_color']} / {tracked_pkg['letters']}"

    if w is None or h is None:
        # If no size, just draw a small circle
        cv2.circle(image, (x, y), 10, color, -1)
        cv2.putText(image, box_label, (x + 5, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        return

    top_left = (x - w // 2, y - h // 2)
    bottom_right = (x + w // 2, y + h // 2)
    cv2.rectangle(image, top_left, bottom_right, color, 3)

    cv2.putText(image, box_label, (x + 5, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

# --------------------------------------------------
# COLOR MAP
# --------------------------------------------------
color_map = {
    "A": (0, 255, 0),      # Green
    "K": (255, 0, 255),    # Magenta
    "O": (255, 255, 255),  # White
    "Green": (0, 255, 0),  # Green
    "Red": (255, 0, 0),    # Blue-ish if you prefer (your code swapped)
    "Sample": (255, 255, 255),
    "Blue": (0, 0, 255)
}

# --------------------------------------------------
# TRACKING
# --------------------------------------------------
tracked_package = None      # Will hold our current tracked package info
MISS_THRESHOLD = 5          # After 5 missed sessions, we stop tracking

DISTANCE_JUMP_THRESHOLD = 150  # Max allowed distance jump

# --------------------------------------------------
# MAIN LOOP
# --------------------------------------------------
while True:
    # 1) Capture an image
    image = picam2.capture_array()
    image = cv2.resize(image, (512, 512))
    image = cv2.rotate(image, cv2.ROTATE_180)

    # 2) Detections
    detections_letters = detect_letters(picam2)
    detections_boxes   = detect_objects(picam2)

    # 3) Assign + Distance
    matched_packages = assign_letters_to_packages(detections_letters, detections_boxes, threshold=5)
    box_distances    = calculate_box_distance(detections_boxes, zone_center, pass_threshold=20, max_distance=30)

    # 4) Build session data
    session_data = build_session_data(matched_packages, box_distances, detections_boxes)

    # 5) Possibly update or pick a new tracked package
    if tracked_package is None:
        # No package is currently tracked => pick the highest priority from session
        high_pkg_key, high_pkg_info = get_high_priority_package(session_data)
        if high_pkg_key is not None:
            high_pkg_info["miss_detections"] = 0
            tracked_package = high_pkg_info
    else:
        # Already have a tracked package => try to update it
        result = update_tracked_package(
            tracked_package, 
            session_data, 
            distance_threshold=DISTANCE_JUMP_THRESHOLD
        )
  
        
                # In your main loop, around line 74 (where you do "if result is False:")
        if result is False:
            # The tracked package was not found in this new session
            if not tracked_package["letters"]:
                # It was letterless => let's pick a new box immediately
                print("Tracked letterless package disappeared => pick a new box with priority.")
                high_pkg_key, high_pkg_info = get_high_priority_package(session_data)
                if high_pkg_key is not None:
                    high_pkg_info["miss_detections"] = 0
                    tracked_package = high_pkg_info
                else:
                    tracked_package = None
            else:
                # If it had letters, do the usual missed detection logic:
                tracked_package["miss_detections"] += 1
                if tracked_package["miss_detections"] > MISS_THRESHOLD:
                    print("Tracked package missing for too many sessions => stop tracking.")
                    tracked_package = None
                    
            
            
        elif result == "TOO_FAR":
            # The distance jumped too far => discard and pick a new box
            print("Large distance jump => discard tracking. We'll pick a new box.")
            tracked_package = None

            # Now pick a new highest priority from the current session
            high_pkg_key, high_pkg_info = get_high_priority_package(session_data)
            if high_pkg_key is not None:
                high_pkg_info["miss_detections"] = 0
                tracked_package = high_pkg_info
        else:
            # Otherwise, we got a valid updated package => keep tracking
            tracked_package = result

    # 6) Draw the normal bounding boxes for all detected boxes
    draw_detections(image, detections_boxes, color_map)

    # 7) If we have a tracked package, draw it in CYAN

        
     
       
    if tracked_package is not None:
        draw_tracked_package(image, tracked_package, color=(255, 255, 0))
        status = tracked_package["status"]

        if status == "PASS":
            print("Tracked package is PASS; no movement needed.")
        elif status == "CLOSE":
            # Do fine bounding-box alignment
            fine_cmds = fine_adjustment_command(
                tracked_package,
                zone_top_left,
                zone_bottom_right,
                margin=1
            )
            if fine_cmds:
                print("Fine adjustment needed =>", fine_cmds)
            else:
                print("Box is 'CLOSE' but no fine movement needed. Possibly move physically closer if needed.")
        else:
            # status == "REJECTED"
            # Attempt coarse movement first
            coarse_cmds = compute_movement_command(
                box_position=tracked_package["position"],
                zone_center=zone_center,
                grid_size=64,
                x_tolerance=1,
                y_tolerance=1
            )
            if coarse_cmds:
                print("Coarse movement =>", coarse_cmds)
            else:
                # If coarse move is empty but status is still REJECTED => try fine
                fine_cmds = fine_adjustment_command(
                    tracked_package,
                    zone_top_left,
                    zone_bottom_right,
                    margin=0
                )
                if fine_cmds:
                    print("Fine adjustment =>", fine_cmds)
                else:
                    print("cvfd "
                          "error")


    # 8) Mark zone + grid
    mark_zone(image, zone_top_left, zone_bottom_right, label="Defined Zone")
    add_grid(image)

    # 9) (Optional) Print session data
    print("\n--- SESSION DATA ---")
    for pkg_key, pkg_info in session_data.items():
        print(f"{pkg_key} => {pkg_info}")
    print("--- END SESSION DATA ---")

    # 10) Show the frame
    cv2.imshow("Detection Output", cv2.cvtColor(image, cv2.COLOR_RGB2BGR))

    # Press 'q' to exit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Cleanup
picam2.stop()
cv2.destroyAllWindows()
