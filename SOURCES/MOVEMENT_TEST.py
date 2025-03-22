#!/usr/bin/env python3
import cv2
import time
import numpy as np
from CAMERA.camera_session import init_camera, stop_camera, capture_raw_image

def mosaic_effect(image, scale_down_factor=0.25):
    h, w = image.shape[:2]
    new_size = (int(w * scale_down_factor), int(h * scale_down_factor))
    small = cv2.resize(image, new_size, interpolation=cv2.INTER_NEAREST)
    mosaic = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
    return mosaic

def test_raw_fps(duration=5):
    print("Testare FPS pentru afișarea imaginii brute (fără procesare)...")
    frame_count = 0
    start_time = time.time()
    while True:
        current_frame = capture_raw_image()
        cv2.imshow("Raw FPS", current_frame)
        frame_count += 1
        if (time.time() - start_time) > duration:
            break
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    elapsed = time.time() - start_time
    fps = frame_count / elapsed
    print(f"Raw FPS: {fps:.2f}")
    cv2.destroyWindow("Raw FPS")

def test_mosaic_fps(duration=5):
    print("Testare FPS după aplicarea efectului mozaic...")
    frame_count = 0
    start_time = time.time()
    while True:
        current_frame = capture_raw_image()
        mosaic_frame = mosaic_effect(current_frame, scale_down_factor=0.25)
        cv2.imshow("Mosaic FPS", mosaic_frame)
        frame_count += 1
        if (time.time() - start_time) > duration:
            break
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    elapsed = time.time() - start_time
    fps = frame_count / elapsed
    print(f"Mosaic FPS: {fps:.2f}")
    cv2.destroyWindow("Mosaic FPS")

def initialize_roi(gray_image, center, roi_size=100):
    x, y = center
    half = roi_size // 2
    h, w = gray_image.shape
    x1, y1 = max(x - half, 0), max(y - half, 0)
    x2, y2 = min(x + half, w), min(y + half, h)
    roi = gray_image[y1:y2, x1:x2]
    points = cv2.goodFeaturesToTrack(roi, maxCorners=50, qualityLevel=0.01, minDistance=5)
    if points is not None:
        points += np.array([[x1, y1]], dtype=np.float32)
    return points, (x1, y1, x2, y2)

def draw_tracking_info(frame, center, roi_box, points):
    display = frame.copy()
    x1, y1, x2, y2 = roi_box
    cv2.rectangle(display, (x1, y1), (x2, y2), (255, 0, 0), 2)
    if points is not None:
        for pt in points:
            x, y = pt.ravel().astype(int)
            cv2.circle(display, (x, y), 3, (0, 255, 0), -1)
    cv2.circle(display, center, 10, (0, 0, 255), 2)
    return display

def run_tracking():
    # Inițializare imagine și ROI
    first_frame = capture_raw_image()
    mosaic_first = mosaic_effect(first_frame, scale_down_factor=0.25)
    h, w = mosaic_first.shape[:2]
    center = (w // 2, h // 2)
    prev_gray = cv2.cvtColor(mosaic_first, cv2.COLOR_BGR2GRAY)
    points, roi_box = initialize_roi(prev_gray, center, roi_size=100)
    cum_offset = np.array([0.0, 0.0])
    
    frame_count = 0
    start_time = time.time()
    
    while True:
        current_frame = capture_raw_image()
        mosaic_current = mosaic_effect(current_frame, scale_down_factor=0.25)
        curr_gray = cv2.cvtColor(mosaic_current, cv2.COLOR_BGR2GRAY)
        
        if points is not None:
            new_points, status, error = cv2.calcOpticalFlowPyrLK(prev_gray, curr_gray, points, None)
            good_new = new_points[status.flatten() == 1]
            good_old = points[status.flatten() == 1]
            if len(good_new) > 0:
                shift = np.mean(good_new - good_old, axis=0)
                shift = np.squeeze(shift)
            else:
                shift = np.array([0.0, 0.0])
        else:
            shift = np.array([0.0, 0.0])
        
        cum_offset += shift
        new_center = (int(center[0] + cum_offset[0]), int(center[1] + cum_offset[1]))
        
        dx, dy = shift
        direction = ""
        if dx > 1:
            direction += "Dreapta "
        elif dx < -1:
            direction += "Stânga "
        if dy > 1:
            direction += "Jos "
        elif dy < -1:
            direction += "Sus "
        speed = np.sqrt(dx*dx + dy*dy)
        print(f"Shift: ({dx:.2f}, {dy:.2f}) | Direcție: {direction.strip()} | Viteză: {speed:.2f} pixeli/cadru")
        
        if points is None or (points is not None and len(good_new) < 5):
            points, roi_box = initialize_roi(curr_gray, new_center, roi_size=100)
        else:
            points = good_new.reshape(-1, 1, 2)
        
        prev_gray = curr_gray.copy()
        
        display_frame = draw_tracking_info(mosaic_current, new_center, roi_box, points)
        cv2.imshow("Mosaic Tracking", display_frame)
        
        frame_count += 1
        if frame_count % 10 == 0:
            elapsed = time.time() - start_time
            fps = frame_count / elapsed
            print(f"FPS: {fps:.2f}")
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        
    cv2.destroyAllWindows()

def main():
    # Inițializează camera
    init_camera()
    
    # Testăm FPS pentru afișarea imaginii brute
    test_raw_fps(duration=5)
    input("Apasă ENTER pentru a continua la testul cu efect mozaic (sau 'q' pentru ieșire)...")
    
    # Testăm FPS după aplicarea efectului mozaic
    test_mosaic_fps(duration=5)
    input("Apasă ENTER pentru a continua la modul normal de tracking (sau 'q' pentru ieșire)...")
    
    # Rulăm cursul normal al programului (tracking)
    run_tracking()
    
    stop_camera()

if __name__ == "__main__":
    main()
