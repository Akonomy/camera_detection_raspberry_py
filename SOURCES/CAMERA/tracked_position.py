#!/usr/bin/env python3
"""
Modul: position_tracker.py

Descriere: Acest modul oferă o clasă PositionTracker și o funcție
          track_position(image, ...) care permite urmărirea deplasării
          între cadre. La primul apel, se reține imaginea inițială, iar la
          apelurile ulterioare se calculează deplasarea (shift), viteza, direcția
          și poziția estimată (center) a obiectului urmărit.
          Se returnează și ROI-ul (regiunea de interes) în care s-au detectat punctele,
          astfel încât să știi aproximativ unde se află obiectul în ultima imagine.

Utilizare exemplu:
    from position_tracker import track_position

    # Presupunând că obții imagini din camera ta:
    result = track_position(image)
    # result este un dicționar de forma:
    # {"shift": (dx, dy), "speed": s, "direction": "Dreapta Jos", 
    #  "center": (x, y), "roi_box": (x1, y1, x2, y2)}
"""

import cv2
import numpy as np

def mosaic_effect(image, scale_down_factor=0.25):
    h, w = image.shape[:2]
    new_size = (int(w * scale_down_factor), int(h * scale_down_factor))
    small = cv2.resize(image, new_size, interpolation=cv2.INTER_NEAREST)
    mosaic = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
    return mosaic

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

class PositionTracker:
    def __init__(self, scale_down_factor=0.25, roi_size=100, initial_center=None):
        self.scale_down_factor = scale_down_factor
        self.roi_size = roi_size
        self.prev_gray = None
        self.points = None
        self.roi_box = None
        self.cum_offset = np.array([0.0, 0.0])
        self.center = initial_center  # Dacă rămâne None, se calculează din prima imagine

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
            self.points, self.roi_box = initialize_roi(curr_gray, self.center, self.roi_size)
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
            if len(good_new) > 0:
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
            self.points, self.roi_box = initialize_roi(curr_gray, new_center, self.roi_size)
        else:
            self.points = good_new.reshape(-1, 1, 2)
        
        return {"shift": (float(dx), float(dy)),
                "speed": float(speed),
                "direction": direction.strip(),
                "center": new_center,
                "roi_box": self.roi_box}

# Instanță singleton pentru comoditate (opțional):
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

if __name__ == "__main__":
    # Exemplu de test folosind o cameră (sau altă sursă de imagini)
    cap = cv2.VideoCapture(0)
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        result = track_position(frame)
        print(result)
        # Desenăm ROI-ul pe imagine pentru vizualizare:
        x1, y1, x2, y2 = result["roi_box"]
        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
        cv2.circle(frame, result["center"], 10, (0, 0, 255), 2)
        cv2.imshow("Tracking Test", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()
