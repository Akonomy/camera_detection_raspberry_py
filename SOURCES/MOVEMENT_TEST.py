#!/usr/bin/env python3
import cv2
import time
from CAMERA.camera_session import init_camera, stop_camera, capture_raw_image
from CAMERA.tracked_position import track_position, mosaic_effect, track_with_detailed_analysis, track_position_by_phase

def test_fps_and_display(method="standard", duration=15):
    frame_count = 0
    start_time = time.time()
    
    while True:
        frame = capture_raw_image()
        
        if method == "standard":
            result = track_position(frame)
        elif method == "detailed":
            # Exemplu: folosim intervalul HSV pentru verde
            detailed = track_with_detailed_analysis(frame, hsv_lower=(30, 50, 50), hsv_upper=(90, 255, 255))
            result = detailed["tracking_result"]
        elif method == "phase":
            # Folosim metoda de tracking cu phase correlation; se poate ajusta crop_percent după nevoie
            result = track_position_by_phase(frame, crop_percent=(0.3, 0.7))
        else:
            result = None
        
        # Aplicăm efectul mozaic pentru afișare
        mosaic_frame = mosaic_effect(frame)
        if result is not None:
            if method == "phase":
                # Pentru metoda phase, ROI-ul este returnat sub cheia "roi"
                x1, y1, x2, y2 = result["roi"]
            else:
                x1, y1, x2, y2 = result["roi_box"]
            cv2.rectangle(mosaic_frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
            cv2.circle(mosaic_frame, result["center"], 10, (0, 0, 255), 2)
        
        cv2.imshow(f"{method.capitalize()} Tracking", mosaic_frame)
        frame_count += 1
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        if (time.time() - start_time) > duration:
            break
            
    elapsed = time.time() - start_time
    fps = frame_count / elapsed
    print(f"{method.capitalize()} tracking FPS: {fps:.2f}")
    cv2.destroyAllWindows()

def main():
    init_camera()
    
    print("Test FPS și afișare pentru metoda standard (track_position) pentru 15 secunde:")
    test_fps_and_display(method="standard", duration=15)
    
    print("Test FPS și afișare pentru metoda detaliată (track_with_detailed_analysis) pentru 15 secunde:")
    test_fps_and_display(method="detailed", duration=15)
    
    print("Test FPS și afișare pentru metoda phase (track_position_by_phase) pentru 15 secunde:")
    test_fps_and_display(method="phase", duration=15)
    
    stop_camera()

if __name__ == "__main__":
    main()
