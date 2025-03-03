import cv2
import time
import threading
import tkinter as tk
from tkinter import ttk

# Importurile pentru modulele de detecție (presupunem că funcționează conform codului existent)
from picamera2 import Picamera2
from BOX_DETECT.letter_detect import detect_letters
from BOX_DETECT.box_detect import detect_objects
from BOX_DETECT.utils import (
    assign_letters_to_packages,
    calculate_box_distance,
    build_session_data,
    get_high_priority_package,
    update_tracked_package,
    compute_movement_command,
    fine_adjustment_command
)
from USART_COM.serial_module import process_command
from USART_COM import usart

# --------------------------------------------------
# VARIABILE GLOBALE
# --------------------------------------------------
# Această variabilă va fi actualizată după fiecare iterație de detecție.
latest_session_data = {}  # de forma: {"PACKAGE1": {..}, "PACKAGE2": {..}, ...}

# Dicționar pentru valorile individuale (fiecare slot are propria valoare fixă, inițial setată la startup)
# Nu se actualizează ulterior în update_gui – se modifică doar manual de către utilizator
fixed_individual_values = {}

# Mapează culorile din datele pachetului la culori Tkinter
tk_color_map = {
    "Green": "green",
    "Red": "red",
    "Blue": "dodgerblue",  # albastru plăcut
    "Sample": "beige"      # se folosește bej pentru Sample/simple
}
default_tk_color = "gray"  # folosit dacă nu se recunoaște culoarea

# --------------------------------------------------
# FUNCȚIE AJUTĂTOARE PENTRU FUZIONAREA CUTIILOR
# --------------------------------------------------
def merge_boxes(boxes, threshold=100):
    """
    Pentru o listă de cutii (cu literă), unește (îmbină) acele cutii care sunt la distanță <= threshold.
    Fiecare cutie are:
      - "position": (x, y)
      - "size": (width, height)
    Se calculează bounding-box-ul care acoperă toate cutiile din cluster, iar poziția nouă este centrul.
    """
    n = len(boxes)
    parent = list(range(n))
    
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        rx = find(x)
        ry = find(y)
        if rx != ry:
            parent[ry] = rx

    # Compară fiecare pereche de cutii
    for i in range(n):
        for j in range(i + 1, n):
            pos_i = boxes[i]["position"]
            pos_j = boxes[j]["position"]
            dx = pos_i[0] - pos_j[0]
            dy = pos_i[1] - pos_j[1]
            dist = (dx**2 + dy**2) ** 0.5
            if dist <= threshold:
                union(i, j)

    # Grupează cutiile pe baza părintelui lor (cluster)
    clusters = {}
    for i in range(n):
        root = find(i)
        clusters.setdefault(root, []).append(boxes[i])

    merged_list = []
    for cluster in clusters.values():
        if len(cluster) == 1:
            merged_list.append(cluster[0])
        else:
            lefts, tops, rights, bottoms = [], [], [], []
            for box in cluster:
                x, y = box["position"]
                # Se presupune că există "size" (width, height)
                w, h = box.get("size", (0, 0))
                lefts.append(x - w / 2)
                tops.append(y - h / 2)
                rights.append(x + w / 2)
                bottoms.append(y + h / 2)
            merged_left = min(lefts)
            merged_top = min(tops)
            merged_right = max(rights)
            merged_bottom = max(bottoms)
            new_w = merged_right - merged_left
            new_h = merged_bottom - merged_top
            new_x = (merged_left + merged_right) / 2
            new_y = (merged_top + merged_bottom) / 2
            merged_box = cluster[0].copy()
            merged_box["position"] = (int(new_x), int(new_y))
            merged_box["size"] = (int(new_w), int(new_h))
            merged_list.append(merged_box)
    return merged_list

# --------------------------------------------------
# FUNCȚIA PENTRU FILTRAREA ȘI COMBINAREA CUTIILOR
# --------------------------------------------------
def filter_and_merge_session_data(session_data):
    """
    Preprocesează datele de sesiune astfel încât:
      - Pentru cutiile cu literă: 
          • Se grupează după (box_color, literă).
          • În cadrul fiecărui grup, se unesc (dacă sunt la o distanță <= 100) în funcție de limitele cutiilor.
      - Cutiile fără literă se adaugă doar dacă mai sunt sloturi libere (maxim 5).
    Returnează un dicționar cu chei "PACKAGE1", "PACKAGE2", ... pentru maxim 5 pachete.
    """
    boxes = list(session_data.values())
    boxes_with_letter = []
    boxes_without_letter = []
    for box in boxes:
        letters = box.get("letters", [])
        if letters and letters[0].strip() != "":
            boxes_with_letter.append(box)
        else:
            boxes_without_letter.append(box)
    
    merged_boxes = []
    # Grupează cutiile cu literă după (box_color, literă)
    grouped = {}
    for box in boxes_with_letter:
        key = (box.get("box_color", ""), box["letters"][0])
        grouped.setdefault(key, []).append(box)
    
    # Pentru fiecare grup, îmbină cutiile apropiate (distanță <= 100)
    for key, group in grouped.items():
        merged_group = merge_boxes(group, threshold=100)
        merged_boxes.extend(merged_group)
    
    # Sortează după coordonata x detectată (din imagine)
    merged_boxes.sort(key=lambda b: b["position"][0])
    boxes_without_letter.sort(key=lambda b: b.get("position", (float('inf'), 0))[0])
    
    # Selectează pachetele: întâi cele cu literă, apoi, dacă sunt locuri libere, cele fără literă
    selected = merged_boxes
    if len(selected) < 5:
        needed = 5 - len(selected)
        selected.extend(boxes_without_letter[:needed])
    selected = selected[:5]
    
    new_session_data = {}
    for i, box in enumerate(selected, start=1):
        new_session_data[f"PACKAGE{i}"] = box
    return new_session_data

# --------------------------------------------------
# CLASA PENTRU INTERFAȚA GRAFICĂ CU TKINTER
# --------------------------------------------------
class PackageGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Interfață pachete detectate")
        self.package_frames = {}   # Elementele GUI pentru fiecare dintre cele 5 secțiuni
        self.package_data = {}     # Pozițiile actuale pentru fiecare pachet
        
        # Dimensiuni pentru pătratele grafice
        self.canvas_width = 100
        self.canvas_height = 100

        # Setăm valorile individuale fixate pentru fiecare slot (acestea reprezintă poziția x reală în cm)
        # Valorile default pentru sloturi: slot1: -10, slot2: -5, slot3: 0, slot4: 5, slot5: 10
        self.default_individual_values = [-10, -5, 0, 5, 10]

        # Creăm un container pentru secțiunile pachetelor
        self.packages_frame = ttk.Frame(self.root)
        self.packages_frame.pack(padx=10, pady=10)

        self.num_packages = 5
        for i in range(1, self.num_packages + 1):
            frame = ttk.Frame(self.packages_frame, borderwidth=2, relief="groove", padding=5)
            # Inițial se pack-uiesc; ordonarea se face în update_gui()
            frame.pack(side="left", padx=5, pady=5)
            lbl = ttk.Label(frame, text=f"Pachet {i}")
            lbl.pack()

            # Câmpul de intrare individual (valoare fixă) – nu se va modifica automat
            ind_entry = ttk.Entry(frame, width=8)
            ind_entry.insert(0, str(self.default_individual_values[i-1]))
            ind_entry.pack(pady=(5, 2))
            # Actualizarea se va face doar când utilizatorul modifică manual
            ind_entry.bind("<FocusOut>", lambda e, slot=i: self.update_fixed_value(slot))
            
            # Canvas pentru afișarea cutiei și literei detectate
            canvas = tk.Canvas(frame, width=self.canvas_width, height=self.canvas_height, bg=default_tk_color)
            canvas.pack()

            # Etichetă pentru poziție
            pos_label = ttk.Label(frame, text="Poz: -")
            pos_label.pack(pady=(2, 5))

            self.package_frames[i] = {
                "frame": frame,
                "canvas": canvas,
                "pos_label": pos_label,
                "identity": None  # Identitatea curentă a pachetului (box_color, letter) sau None
            }
            self.package_data[i] = ("-", "-")

            # Salvăm valoarea fixă în dicționarul nostru (cheie: numărul slotului)
            fixed_individual_values[i] = self.default_individual_values[i-1]

        # Câmpul de intrare comun și butonul SAVE (afișate sub secțiunile pachetelor)
        self.common_frame = ttk.Frame(self.root)
        self.common_frame.pack(pady=10)

        ttk.Label(self.common_frame, text="Valoare comună:").pack(side="left", padx=5)
        self.common_entry = ttk.Entry(self.common_frame, width=8)
        self.common_entry.insert(0, "0")
        self.common_entry.pack(side="left", padx=5)

        self.save_button = ttk.Button(self.common_frame, text="SAVE", command=self.save_data)
        self.save_button.pack(side="left", padx=5)

        # Etichetă pentru afișarea ultimei valori comune salvate
        self.last_saved_label = ttk.Label(self.common_frame, text="Ultima valoare comună salvată: N/A")
        self.last_saved_label.pack(side="left", padx=10)

        # Pornim actualizarea periodică a datelor în GUI
        self.update_gui()

    def update_fixed_value(self, slot):
        """Actualizează valoarea fixă pentru slotul respectiv atunci când utilizatorul modifică câmpul de intrare."""
        fixed_individual_values[slot] = self.individual_entries[slot].get() if hasattr(self, 'individual_entries') else None

    def update_gui(self):
        """
        Actualizează la fiecare 500ms secțiunile GUI cu ultimele date din latest_session_data.
        Se actualizează canvas-ul și eticheta poziției; câmpul de valoare individuală rămâne fix (nu se modifică automat).
        """
        global latest_session_data

        for i in range(1, self.num_packages + 1):
            pkg_key = f"PACKAGE{i}"
            frame_data = self.package_frames[i]
            canvas = frame_data["canvas"]

            if pkg_key in latest_session_data:
                pkg = latest_session_data[pkg_key]
                box_color = pkg.get("box_color", "")
                bg_color = tk_color_map.get(box_color, default_tk_color)
                letters = pkg.get("letters", [])
                letter = letters[0] if letters else ""
                pos = pkg.get("position", ("-", "-"))
                pos_text = f"Poz: {pos[0]}, {pos[1]}"

                # Actualizează canvas-ul: se va afișa culoarea și litera detectată
                canvas.configure(bg=bg_color)
                canvas.delete("all")
                canvas.create_text(self.canvas_width // 2, self.canvas_height // 2,
                                   text=letter, font=("Helvetica", 24, "bold"), fill="black")
                frame_data["pos_label"].configure(text=pos_text)
                self.package_data[i] = pos

                # Actualizează identitatea (dar nu modifică câmpul de intrare)
                if letter.strip() != "":
                    identity = (box_color, letter)
                else:
                    identity = None
                frame_data["identity"] = identity
            else:
                # Resetăm slotul dacă nu există date
                canvas.configure(bg=default_tk_color)
                canvas.delete("all")
                canvas.create_text(self.canvas_width // 2, self.canvas_height // 2,
                                   text="N/A", font=("Helvetica", 16), fill="black")
                frame_data["pos_label"].configure(text="Poz: -")
                self.package_data[i] = ("-", "-")
                frame_data["identity"] = None

        # Reordonăm secțiunile în funcție de coordonata x detectată (pentru sloturile cu date valide)
        order_list = []
        for i in range(1, self.num_packages + 1):
            pos = self.package_data[i]
            try:
                x_val = float(pos[0])
            except (ValueError, TypeError):
                x_val = float('inf')
            order_list.append((i, x_val))
        sorted_order = sorted(order_list, key=lambda item: item[1])

        for i in range(1, self.num_packages + 1):
            self.package_frames[i]["frame"].pack_forget()
        for (i, _) in sorted_order:
            self.package_frames[i]["frame"].pack(side="left", padx=5, pady=5)

        self.root.after(500, self.update_gui)

    def save_data(self):
        """
        La apăsarea butonului SAVE se citesc:
         - Pentru fiecare slot: poziția detectată (din imagine) și valoarea fixă (care reprezintă poziția x în realitate, în cm)
         - Valoarea comună (care reprezintă poziția y în realitate, în cm)
        Se salvează datele într-un format machine-friendly în fișierul packages_output.txt,
        folosind delimitatori cu linii "___________________".
        
        După salvare:
         - Se actualizează eticheta care afișează ultima valoare comună salvată.
         - Câmpul comun se incrementează automat cu 0.5.
        """
        common_val = self.common_entry.get().strip()
        try:
            common_val_float = float(common_val)
        except ValueError:
            print("Valoarea comună trebuie să fie numerică (poate zecimală)!")
            return

        output_lines = []
        # Format: slot, detected_x, detected_y, real_x, real_y
        for i in range(1, self.num_packages + 1):
            pos = self.package_data.get(i, ("-", "-"))
            # Valoarea fixă a slotului (real_x) este valoarea introdusă de utilizator la acel slot
            ind_val = self.package_frames[i]["frame"].winfo_children()[1].get()  # presupunând că al doilea widget e Entry
            line = f"slot: {i}, detected_x: {pos[0]}, detected_y: {pos[1]}, real_x: {ind_val}, real_y: {common_val}"
            output_lines.append(line)

        try:
            with open("packages_output.txt", "a") as f:
                f.write("\n___________________\n")
                f.write("\n".join(output_lines))
                f.write("\n___________________\n")
            print("Datele au fost salvate în packages_output.txt")
            # Actualizează eticheta pentru ultima valoare comună salvată
            self.last_saved_label.configure(text=f"Ultima valoare comună salvată: {common_val}")
            # Incrementăm automat valoarea comună cu 0.5
            new_common = common_val_float + 0.5
            self.common_entry.delete(0, tk.END)
            self.common_entry.insert(0, str(new_common))
        except Exception as e:
            print("Eroare la salvare:", e)

# --------------------------------------------------
# FUNCȚII SUPLIMENTARE DE DESEN PENTRU OPENCV
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
        top_left = (x - w // 2, y - h // 2)
        bottom_right = (x + w // 2, y + h // 2)
        cv2.rectangle(image, top_left, bottom_right, color, 2)
        cv2.putText(image, label, (x + 5, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

def draw_tracked_package(image, tracked_pkg, color=(255, 255, 0)):
    x, y = tracked_pkg["position"]
    w, h = tracked_pkg.get("size", (None, None))
    box_label = f"TRACKED: {tracked_pkg['box_color']} / {tracked_pkg['letters']}"
    
    if w is None or h is None:
        cv2.circle(image, (int(x), int(y)), 10, color, -1)
        cv2.putText(image, box_label, (int(x) + 5, int(y) - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        return

    top_left = (int(x - w/2), int(y - h/2))
    bottom_right = (int(x + w/2), int(y + h/2))
    cv2.rectangle(image, top_left, bottom_right, color, 3)
    cv2.putText(image, box_label, (int(x) + 5, int(y) - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

# --------------------------------------------------
# FUNCȚIA DE DETECȚIE (RULATĂ ÎNTR-UN FIR SEPARAT)
# --------------------------------------------------
def detection_loop():
    global latest_session_data

    # Configurare cameră și zonă
    picam2 = Picamera2()
    picam2.configure(picam2.create_still_configuration())
    picam2.start()

    zone_top_left = (200, 40)
    zone_bottom_right = (295, 160)
    zone_center = ((zone_top_left[0] + zone_bottom_right[0]) // 2,
                   (zone_top_left[1] + zone_bottom_right[1]) // 2)

    # Variabile pentru urmărirea pachetelor
    tracked_package = None      
    MISS_THRESHOLD = 5          
    DISTANCE_JUMP_THRESHOLD = 150  

    while True:
        # 1) Capturează imaginea, redimensionează și rotește
        image = picam2.capture_array()
        image = cv2.resize(image, (512, 512))
        image = cv2.rotate(image, cv2.ROTATE_180)

        # 2) Detectează litere și pachete
        detections_letters = detect_letters(picam2)
        detections_boxes   = detect_objects(picam2)

        # 3) Asociază literele cu pachetele și calculează distanțele față de centru
        matched_packages = assign_letters_to_packages(detections_letters, detections_boxes, threshold=5)
        box_distances    = calculate_box_distance(detections_boxes, zone_center, pass_threshold=20, max_distance=30)

        # 4) Construiește datele de sesiune și aplică preprocesarea (fuzionarea cutiilor)
        session_data = build_session_data(matched_packages, box_distances, detections_boxes)
        session_data = filter_and_merge_session_data(session_data)
        latest_session_data = session_data

        # 5) Actualizează logica de urmărire a pachetului
        if tracked_package is None:
            high_pkg_key, high_pkg_info = get_high_priority_package(session_data)
            if high_pkg_key is not None:
                high_pkg_info["miss_detections"] = 0
                tracked_package = high_pkg_info
        else:
            result = update_tracked_package(
                tracked_package, 
                session_data, 
                distance_threshold=DISTANCE_JUMP_THRESHOLD
            )
            if result is False:
                if not tracked_package["letters"]:
                    print("Pachetul fără litere nu mai este detectat => alegem un alt pachet.")
                    high_pkg_key, high_pkg_info = get_high_priority_package(session_data)
                    tracked_package = high_pkg_info if high_pkg_key is not None else None
                else:
                    tracked_package["miss_detections"] += 1
                    if tracked_package["miss_detections"] > MISS_THRESHOLD:
                        print("Pachetul urmărit a lipsit prea mult => renunțăm la urmărire.")
                        tracked_package = None
            elif result == "TOO_FAR":
                print("Salt mare de distanță => renunțăm la urmărire și alegem un nou pachet.")
                tracked_package = None
                high_pkg_key, high_pkg_info = get_high_priority_package(session_data)
                tracked_package = high_pkg_info if high_pkg_key is not None else None
            else:
                tracked_package = result

        # 6) Desenează detecțiile pe imagine (pentru afișarea OpenCV)
        draw_detections(image, detections_boxes, {})
        if tracked_package is not None:
            draw_tracked_package(image, tracked_package, color=(255, 255, 0))

        mark_zone(image, zone_top_left, zone_bottom_right, label="Defined Zone")
        add_grid(image, grid_size=64)

        cv2.imshow("Detection Output", cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    picam2.stop()
    cv2.destroyAllWindows()

# --------------------------------------------------
# PUNEM TOTUL SĂ RULEZE
# --------------------------------------------------
if __name__ == "__main__":
    # Pornim firul pentru detecție (folosind OpenCV)
    detection_thread = threading.Thread(target=detection_loop, daemon=True)
    detection_thread.start()

    # Pornim interfața grafică Tkinter (în firul principal)
    root = tk.Tk()
    app = PackageGUI(root)
    root.mainloop()
