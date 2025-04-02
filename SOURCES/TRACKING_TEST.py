import cv2
import time
from CAMERA.camera_session import init_camera, stop_camera, capture_raw_image

# Global tracker objects; initially set to None
tracker_boosting = None
tracker_mil = None
tracker_tld = None
tracker_medianflow = None
tracker_kcf = None

# Function to initialize a given tracker if needed
def init_tracker(tracker, tracker_type, frame, bbox):
    if tracker is None:
        if tracker_type == "BOOSTING":
            tracker = cv2.legacy.TrackerBoosting_create()
        elif tracker_type == "MIL":
            tracker = cv2.legacy.TrackerMIL_create()
        elif tracker_type == "TLD":
            tracker = cv2.legacy.TrackerTLD_create()
        elif tracker_type == "MEDIANFLOW":
            tracker = cv2.legacy.TrackerMedianFlow_create()
        elif tracker_type == "KCF":
            tracker = cv2.TrackerKCF_create()  # KCF is not in legacy in recent versions
        tracker.init(frame, bbox)
    return tracker

# Each tracker function takes the current frame, optional last bounding box,
# and the initial bounding box (used on the first call). It returns the updated bbox.
def track_boosting(frame, last_bbox=None, initial_bbox=None):
    global tracker_boosting
    if tracker_boosting is None:
        if initial_bbox is None:
            return None
        tracker_boosting = init_tracker(tracker_boosting, "BOOSTING", frame, initial_bbox)
        return initial_bbox
    ok, bbox = tracker_boosting.update(frame)
    if not ok and last_bbox is not None:
        return last_bbox
    return bbox

def track_mil(frame, last_bbox=None, initial_bbox=None):
    global tracker_mil
    if tracker_mil is None:
        if initial_bbox is None:
            return None
        tracker_mil = init_tracker(tracker_mil, "MIL", frame, initial_bbox)
        return initial_bbox
    ok, bbox = tracker_mil.update(frame)
    if not ok and last_bbox is not None:
        return last_bbox
    return bbox

def track_tld(frame, last_bbox=None, initial_bbox=None):
    global tracker_tld
    if tracker_tld is None:
        if initial_bbox is None:
            return None
        tracker_tld = init_tracker(tracker_tld, "TLD", frame, initial_bbox)
        return initial_bbox
    ok, bbox = tracker_tld.update(frame)
    if not ok and last_bbox is not None:
        return last_bbox
    return bbox

def track_medianflow(frame, last_bbox=None, initial_bbox=None):
    global tracker_medianflow
    if tracker_medianflow is None:
        if initial_bbox is None:
            return None
        tracker_medianflow = init_tracker(tracker_medianflow, "MEDIANFLOW", frame, initial_bbox)
        return initial_bbox
    ok, bbox = tracker_medianflow.update(frame)
    if not ok and last_bbox is not None:
        return last_bbox
    return bbox

def track_kcf(frame, last_bbox=None, initial_bbox=None):
    global tracker_kcf
    if tracker_kcf is None:
        if initial_bbox is None:
            return None
        tracker_kcf = init_tracker(tracker_kcf, "KCF", frame, initial_bbox)
        return initial_bbox
    ok, bbox = tracker_kcf.update(frame)
    if not ok and last_bbox is not None:
        return last_bbox
    return bbox

# Helper: compute the center of a bounding box
def bbox_center(bbox):
    x, y, w, h = bbox
    return (int(x + w/2), int(y + h/2))

# Colors in BGR format for the circles:
COLORS = {
    "BOOSTING": (0, 0, 255),       # Red
    "MIL": (0, 255, 0),            # Green
    "TLD": (255, 0, 0),            # Blue
    "MEDIANFLOW": (0, 0, 0),       # Black
    "KCF": (180, 105, 255)         # Pink-ish
}

def main():
    # Initialize the camera
    init_camera()
    print("Camera initialized. Press 'q' in the image window to stop.")
    
    # Define the initial bounding box for the object to track.
    # Change these values as needed: (x, y, width, height)
    initial_bbox = (200, 200, 50, 50)
    
    # Last known bounding boxes for fallback if update fails
    last_bbox_boosting = initial_bbox
    last_bbox_mil = initial_bbox
    last_bbox_tld = initial_bbox
    last_bbox_medianflow = initial_bbox
    last_bbox_kcf = initial_bbox

    try:
        while True:
            frame = capture_raw_image()
            if frame is None:
                continue
            
            # Update each tracker
            bbox_boosting = track_boosting(frame, last_bbox_boosting, initial_bbox)
            bbox_mil = track_mil(frame, last_bbox_mil, initial_bbox)
            bbox_tld = track_tld(frame, last_bbox_tld, initial_bbox)
            bbox_medianflow = track_medianflow(frame, last_bbox_medianflow, initial_bbox)
            bbox_kcf = track_kcf(frame, last_bbox_kcf, initial_bbox)
            
            # Update last known positions
            if bbox_boosting is not None:
                last_bbox_boosting = bbox_boosting
            if bbox_mil is not None:
                last_bbox_mil = bbox_mil
            if bbox_tld is not None:
                last_bbox_tld = bbox_tld
            if bbox_medianflow is not None:
                last_bbox_medianflow = bbox_medianflow
            if bbox_kcf is not None:
                last_bbox_kcf = bbox_kcf
            
            # Draw circles on the frame at the center of each bounding box
            if bbox_boosting is not None:
                center = bbox_center(bbox_boosting)
                cv2.circle(frame, center, 5, COLORS["BOOSTING"], -1)
            if bbox_mil is not None:
                center = bbox_center(bbox_mil)
                cv2.circle(frame, center, 5, COLORS["MIL"], -1)
            if bbox_tld is not None:
                center = bbox_center(bbox_tld)
                cv2.circle(frame, center, 5, COLORS["TLD"], -1)
            if bbox_medianflow is not None:
                center = bbox_center(bbox_medianflow)
                cv2.circle(frame, center, 5, COLORS["MEDIANFLOW"], -1)
            if bbox_kcf is not None:
                center = bbox_center(bbox_kcf)
                cv2.circle(frame, center, 5, COLORS["KCF"], -1)
            
            # Optionally, you can also draw the bounding boxes for visualization
            # For example:
            # cv2.rectangle(frame, (int(bbox_boosting[0]), int(bbox_boosting[1])),
            #               (int(bbox_boosting[0] + bbox_boosting[2]), int(bbox_boosting[1] + bbox_boosting[3])),
            #               COLORS["BOOSTING"], 2)
            
            cv2.imshow("Tracking", frame)
            
            # Break loop on pressing 'q'
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except Exception as e:
        print("An error occurred:", e)
    finally:
        cv2.destroyAllWindows()
        stop_camera()

if __name__ == '__main__':
    main()
