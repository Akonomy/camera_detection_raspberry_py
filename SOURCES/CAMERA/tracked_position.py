#!/usr/bin/env python3
"""
Modul: position_tracker.py

Descriere: Acest modul oferă o clasă PositionTracker și două funcții de tracking:
          - track_position(image, ...) urmărește mișcarea între cadre,
            calculând deplasarea (shift), viteza, direcția și poziția estimată (center)
            a obiectului urmărit, precum și ROI-ul în care s-au detectat punctele.
          - analyze_detailed_position(image, bbox, hsv_lower, hsv_upper) primește o imagine
            și un bounding box (ROI inițial) și, pe baza segmentării în spațiul HSV (folosind
            intervalul [hsv_lower, hsv_upper]), calculează centrul mediu al regiunii de interes
            și returnează poziția rafinată.
            
Utilizare exemplu:
    from position_tracker import track_position, analyze_detailed_position

    # Tracking simplu:
    result = track_position(image)
    # result este un dicționar cu informații precum:
    # {"shift": (dx, dy), "speed": s, "direction": "Dreapta Jos", 
    #  "center": (x, y), "roi_box": (x1, y1, x2, y2)}
    
    # Analiză detaliată într-un ROI:
    refined = analyze_detailed_position(image, bbox=(x1, y1, x2, y2), 
                                          hsv_lower=(30, 50, 50), hsv_upper=(90, 255, 255))
    # refined este un dicționar cu "refined_center" și "refined_bbox".
"""

import cv2
import numpy as np

def mosaic_effect(image, scale_down_factor=0.25):
    h, w = image.shape[:2]
    new_size = (int(w * scale_down_factor), int(h * scale_down_factor))
    small = cv2.resize(image, new_size, interpolation=cv2.INTER_NEAREST)
    mosaic = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
    return mosaic

def initialize_roi(gray_image, center, roi_size=100, exclusion_zones=[((166,335),(375,512))]):
    x, y = center
    half = roi_size // 2
    h, w = gray_image.shape
    x1, y1 = max(x - half, 0), max(y - half, 0)
    x2, y2 = min(x + half, w), min(y + half, h)
    roi = gray_image[y1:y2, x1:x2]
    points = cv2.goodFeaturesToTrack(roi, maxCorners=100, qualityLevel=0.01, minDistance=5)
    if points is not None:
        # Adăugăm offset-ul ROI-ului pentru a obține coordonatele în imaginea originală
        points += np.array([[x1, y1]], dtype=np.float32)
        
        # Filtrare: excludem punctele din zonele interzise
        filtered_points = []
        for pt in points:
            px, py = pt.ravel()
            inside = False
            for zone in exclusion_zones:
                (ex_x1, ex_y1), (ex_x2, ex_y2) = zone
                if ex_x1 <= px <= ex_x2 and ex_y1 <= py <= ex_y2:
                    inside = True
                    break
            if not inside:
                filtered_points.append(pt)
        if filtered_points:
            points = np.array(filtered_points, dtype=np.float32)
        else:
            points = None
    return points, (x1, y1, x2, y2)

class PositionTracker:
    def __init__(self, scale_down_factor=0.25, roi_size=100, initial_center=None,
                 exclusion_zones=[((166,335),(375,512))]):
        self.scale_down_factor = scale_down_factor
        self.roi_size = roi_size
        self.prev_gray = None
        self.points = None
        self.roi_box = None
        self.cum_offset = np.array([0.0, 0.0])
        self.center = initial_center  # Dacă rămâne None, se calculează din prima imagine
        self.exclusion_zones = exclusion_zones

    def reset(self, initial_center=None):
        self.prev_gray = None
        self.points = None
        self.roi_box = None
        self.cum_offset = np.array([0.0, 0.0])
        self.center = initial_center if initial_center is not None else self.center

    def track_position(self, image):
        # Aplică efectul mozaic pentru a reduce volumul de date
        mosaic = mosaic_effect(image, self.scale_down_factor)
        curr_gray = cv2.cvtColor(mosaic, cv2.COLOR_BGR2GRAY)
        
        # Inițializare: la primul apel se setează starea internă
        if self.prev_gray is None:
            self.prev_gray = curr_gray.copy()
            h, w = curr_gray.shape[:2]
            if self.center is None:
                self.center = (w // 2, h // 2)
            self.points, self.roi_box = initialize_roi(curr_gray, self.center, self.roi_size, self.exclusion_zones)
            return {"shift": (0.0, 0.0),
                    "speed": 0.0,
                    "direction": "",
                    "center": self.center,
                    "roi_box": self.roi_box}
        
        # Calcul optical flow pentru punctele din ROI
        if self.points is not None:
            new_points, status, error = cv2.calcOpticalFlowPyrLK(self.prev_gray, curr_gray, self.points, None)
            good_new = new_points[status.flatten() == 1]
            good_old = self.points[status.flatten() == 1]
            # Filtrare: elimină punctele care intră în oricare dintre zonele interzise
            filtered_new = []
            filtered_old = []
            for p_new, p_old in zip(good_new, good_old):
                x, y = p_new.ravel()
                inside_exclusion = False
                for zone in self.exclusion_zones:
                    (ex_x1, ex_y1), (ex_x2, ex_y2) = zone
                    if ex_x1 <= x <= ex_x2 and ex_y1 <= y <= ex_y2:
                        inside_exclusion = True
                        break
                if not inside_exclusion:
                    filtered_new.append(p_new)
                    filtered_old.append(p_old)
            if len(filtered_new) > 0:
                good_new = np.array(filtered_new)
                good_old = np.array(filtered_old)
                shift = np.mean(good_new - good_old, axis=0)
                shift = np.squeeze(shift)
            else:
                shift = np.array([0.0, 0.0])
        else:
            shift = np.array([0.0, 0.0])
        
        # Actualizează deplasarea cumulativă și noul centru
        self.cum_offset += shift
        new_center = (int(self.center[0] + self.cum_offset[0]), int(self.center[1] + self.cum_offset[1]))
        
        # Interpretare direcție
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
        
        # Actualizează starea pentru următorul apel
        self.prev_gray = curr_gray.copy()
        if self.points is None or (self.points is not None and len(good_new) < 5):
            self.points, self.roi_box = initialize_roi(curr_gray, new_center, self.roi_size, self.exclusion_zones)
        else:
            self.points = good_new.reshape(-1, 1, 2)
        
        return {"shift": (float(dx), float(dy)),
                "speed": float(speed),
                "direction": direction.strip(),
                "center": new_center,
                "roi_box": self.roi_box}

# Instanță singleton pentru comoditate (opțional):
_tracker_instance = None

def track_reset():
    """
    Resetează tracker-ul global, astfel încât la următorul apel al funcției track_position 
    să se creeze o nouă instanță a tracker-ului.
    """
    global _tracker_instance
    _tracker_instance = None

def track_position(image, scale_down_factor=0.25, roi_size=100, initial_center=None):
    """
    Funcție convenabilă care reține o instanță internă a tracker-ului.
    La primul apel se creează tracker-ul, iar la apelurile ulterioare se folosește aceeași stare.
    
    Parametri:
      - image: imaginea curentă (BGR) pentru tracking.
      - scale_down_factor: factorul de reducere pentru mozaic.
      - roi_size: dimensiunea ROI-ului pentru detectarea punctelor.
      - initial_center: opțional, centrul inițial (dacă nu este specificat, se folosește centrul imaginii).
      
    Returnează un dicționar cu:
      - "shift": deplasarea (dx, dy) în pixeli între ultimele două cadre,
      - "speed": mărimea deplasării,
      - "direction": text cu direcția (ex. "Dreapta Jos"),
      - "center": noul centru estimat,
      - "roi_box": ROI-ul sub forma (x1, y1, x2, y2).
    """
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = PositionTracker(scale_down_factor=scale_down_factor,
                                            roi_size=roi_size,
                                            initial_center=initial_center)
    return _tracker_instance.track_position(image)

def analyze_detailed_position(image, bbox, hsv_lower, hsv_upper):
    """
    Analizează un ROI definit de 'bbox' (format: (x1, y1, x2, y2)) din imaginea 'image'
    pentru a detecta detalii pe baza culorii. Convertim ROI-ul în HSV, aplicăm un threshold
    folosind valorile 'hsv_lower' și 'hsv_upper', apoi calculăm centroidul regiunii detectate.
    Dacă nu se detectează regiuni semnificative, se returnează centrul ROI-ului.
    
    Parametri:
      - image: imaginea curentă (BGR).
      - bbox: tuple (x1, y1, x2, y2) care definește ROI-ul.
      - hsv_lower: tuple cu valorile inferioare pentru threshold (H, S, V).
      - hsv_upper: tuple cu valorile superioare pentru threshold (H, S, V).
      
    Returnează un dicționar cu:
      - "refined_center": centrul calculat (x, y) în ROI,
      - "refined_bbox": bounding box-ul (x1, y1, x2, y2) extins pe baza regiunii detectate.
    """
    x1, y1, x2, y2 = bbox
    roi = image[y1:y2, x1:x2]
    hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv_roi, np.array(hsv_lower), np.array(hsv_upper))
    
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if contours:
        c = max(contours, key=cv2.contourArea)
        M = cv2.moments(c)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"]) + x1
            cy = int(M["m01"] / M["m00"]) + y1
            x, y, w, h = cv2.boundingRect(c)
            refined_bbox = (x1 + x, y1 + y, x1 + x + w, y1 + y + h)
            return {"refined_center": (cx, cy),
                    "refined_bbox": refined_bbox}
    center_roi = ((x1 + x2) // 2, (y1 + y2) // 2)
    return {"refined_center": center_roi,
            "refined_bbox": bbox}

def track_with_detailed_analysis(image, hsv_lower, hsv_upper, 
                                 scale_down_factor=0.25, roi_size=100, initial_center=None):
    """
    Combină tracking-ul standard cu o analiză detaliată a regiunii de interes.
    Se aplică tracking-ul pentru a obține un ROI aproximativ, apoi se folosește
    analyze_detailed_position pentru a rafina poziția obiectului pe baza analizei culorii.
    
    Returnează un dicționar ce conține:
      - "tracking_result": rezultatul tracking-ului standard (shift, speed, direction, center, roi_box),
      - "detailed_result": rezultatul analizei detaliate (refined_center, refined_bbox).
    """
    tracking_result = track_position(image, scale_down_factor, roi_size, initial_center)
    detailed_result = analyze_detailed_position(image, tracking_result["roi_box"],
                                                hsv_lower, hsv_upper)
    return {"tracking_result": tracking_result, "detailed_result": detailed_result}

def track_point(image, initial_center=[256,256], reset=False, scale_down_factor=0.25, roi_size=500, need_points=False):
    """
    Procesează imaginea primită pentru tracking și returnează noul centru estimat.
    
    Parametri:
      - image: imaginea curentă (BGR) de la sursa externă.
      - initial_center: centrul inițial pentru tracking, folosit dacă trackerul este resetat.
      - reset: flag boolean; dacă True, se resetează trackerul folosind track_reset().
      - scale_down_factor: factorul de reducere pentru aplicarea efectului mozaic.
      - roi_size: dimensiunea ROI-ului pentru detectarea punctelor.
      - need_points: dacă True, funcția va returna și punctele folosite pentru tracking.
    
    Returnează:
      - Dacă need_points este False (implicit): un tuple (x, y) reprezentând noul centru.
      - Dacă need_points este True: un tuple (center, points) unde:
            center: un tuple (x, y) al noului centru estimat.
            points: un array NumPy cu punctele urmărite (sau None dacă nu există).
    """
    if reset:
        track_reset()
    track_img = image.copy()
    result = track_position(track_img, scale_down_factor=scale_down_factor, roi_size=roi_size, initial_center=initial_center)
    
    if need_points:
        global _tracker_instance
        return (result["center"], _tracker_instance.points)
    else:
        return result["center"]

if __name__ == "__main__":
    cap = cv2.VideoCapture(0)
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        result = track_position(frame)
        print("Tracking:", result)
        
        detailed = analyze_detailed_position(frame, result["roi_box"], (30, 50, 50), (90, 255, 255))
        print("Detaliat:", detailed)
        
        x1, y1, x2, y2 = result["roi_box"]
        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
        cv2.circle(frame, result["center"], 10, (0, 0, 255), 2)
        
        dx1, dy1, dx2, dy2 = detailed["refined_bbox"]
        cv2.rectangle(frame, (dx1, dy1), (dx2, dy2), (0, 255, 255), 2)
        cv2.circle(frame, detailed["refined_center"], 5, (0, 255, 255), -1)
        
        cv2.imshow("Tracking Test", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()
