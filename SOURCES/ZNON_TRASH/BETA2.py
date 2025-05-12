import cv2
import time
import threading
import tkinter as tk
import copy
import math
from picamera2 import Picamera2
import logging

# Configurare logare: logurile vor fi scrise în fișierul "session_log.txt"
logging.basicConfig(filename="session_log.txt", level=logging.INFO, 
                    format="%(asctime)s - %(message)s")

# Variabile globale pentru contorizarea sesiunilor de detecție între comenzi
session_counter = 0

# Variabile suplimentare pentru monitorizarea distanței
last_logged_distance = None
distance_session_counter = 0

# Variabile globale pentru stocarea parametrilor (vechi, se păstrează pentru referință)
session_records = []       # Vechea metodă de stocare, pentru referință
last_session_data = {}     # Ultima sesiune de pachete (session_data)
distance_changed = False
distance_change_timestamp = None

# Parametru pentru pragul de îmbinare a pachetelor similare
MERGE_DISTANCE_THRESHOLD = 50  # Distanța minimă între centre pentru a considera două pachete ca fiind același obiect

# ---------------------------
# Definirea cozii de comenzi
# ---------------------------
MAX_QUEUE_SIZE = 2
NORMAL_PRIORITY = 1
ADJUST_PRIORITY = 2
command_queue = []  # Fiecare element: {"cmd": (param1, param2, param3, param4), "priority": int}

def add_command_to_queue(cmd, priority):
    """Adaugă sau actualizează o comandă în coadă, respectând capacitatea și prioritatea."""
    global command_queue
    replaced = False
    # Dacă există deja o comandă cu aceeași prioritate, o actualizează
    for i, existing in enumerate(command_queue):
        if existing["priority"] == priority:
            command_queue[i] = {"cmd": cmd, "priority": priority}
            replaced = True
            break
    if not replaced:
        if len(command_queue) < MAX_QUEUE_SIZE:
            command_queue.append({"cmd": cmd, "priority": priority})
        else:
            # Găsește comanda cu cea mai mică prioritate
            lowest_priority = min(command_queue, key=lambda x: x["priority"])
            if priority > lowest_priority["priority"]:
                for i, existing in enumerate(command_queue):
                    if existing["priority"] == lowest_priority["priority"]:
                        command_queue[i] = {"cmd": cmd, "priority": priority}
                        break
            else:
                # Dacă noua comandă are prioritate mai mică, o ignoră
                pass

def execute_command_from_queue():
    """Execută comanda din coadă cu cea mai mare prioritate și o elimină din coadă."""
    global command_queue, skip_next_session, session_manager, command_phase
    if command_queue:
        # Selectează comanda cu cea mai mare prioritate (prioritatea mai mare înseamnă execuție preferată)
        command_to_execute = max(command_queue, key=lambda x: x["priority"])
        cmd = command_to_execute["cmd"]
        process_command(*cmd)
        logging.info("AUTO EXECUTED COMMAND FROM QUEUE: {}".format(cmd))
        # Elimină comanda executată din coadă
        command_queue = [c for c in command_queue if c != command_to_execute]
        skip_next_session = True
        session_manager.sessions = []
        # Setează command_phase în funcție de comandă
        if cmd == (1, 13, 1, 140):
            command_phase = "adjust"
        else:
            command_phase = None

# -----------------------------------------
# Importă funcțiile de comunicare și direcționare
# -----------------------------------------
from USART_COM.serial_module import process_command
from UTILS.get_directions import get_next_move_command_for_position, get_all_move_commands_for_position
from UTILS.REAL import getRealCoordinates
from UTILS.COARSE_DIRECTIONS import getFirstCommand

# Module de detecție
from BOX_DETECT.letter_detect import detect_letters
from BOX_DETECT.box_detect import detect_objects

# Funcții utilitare din BOX_DETECT/utils.py
from BOX_DETECT.utils import (
    assign_letters_to_packages,
    calculate_box_distance,
    build_session_data,
    get_high_priority_package,
    update_tracked_package,
    compute_movement_command,
    fine_adjustment_command
)

# Importul modulului USART
from USART_COM import usart

# --------------------------------------------------
# Variabile globale pentru interfață și procesare
# --------------------------------------------------
tracked_package = None       # Pachetul curent urmărit
latest_cmds = None           # Comenzile obținute din getRealCoordinates
latest_comanda = None        # Comanda obținută din getFirstCommand

MISS_THRESHOLD = 5           # După 5 sesiuni fără detecție, se renunță la urmărire
DISTANCE_JUMP_THRESHOLD = 150  # Salt maxim permis în distanță

# --------------------------------------------------
# START COMUNICATIE
# --------------------------------------------------
process_command(3, 2, 0, 0)

# --------------------------------------------------
# CONFIGURAREA CAMEREI ȘI A ZONEI
# --------------------------------------------------
picam2 = Picamera2()
picam2.configure(picam2.create_still_configuration())
picam2.start()

zone_top_left = (200, 40)
zone_bottom_right = (295, 160)
zone_center = ((zone_top_left[0] + zone_bottom_right[0]) // 2,
               (zone_top_left[1] + zone_bottom_right[1]) // 2)

# --------------------------------------------------
# CLASA PENTRU MEMORAREA SESIUNILOR
# --------------------------------------------------
class SessionManager:
    def __init__(self, max_sessions=5):
        self.sessions = []   # Listă de sesiuni memorate
        self.max_sessions = max_sessions

    def add_session(self, session_data, tracked_pkg):
        """
        Adaugă o sesiune pe baza datelor curente: session_data și tracked_package.
        Se caută în session_data pachetul care corespunde tracked_pkg, comparând culoarea și,
        în mod normal, litera. Dacă pachetul urmărit nu are litera, se caută un pachet fără literă
        cu aceeași culoare, iar dacă diferența dintre poziția pachetului urmărit și poziția găsită
        este <= 50, se consideră că a fost găsit.
        Dacă nu se găsește, se șterg toate sesiunile (istoric eronat) și se returnează False.
        Altfel, se adaugă sesiunea cu un id incremental.
        """
        tracked_letters = tracked_pkg.get("letters", [])
        tracked_letter = tracked_letters[0] if tracked_letters else None
        tracked_color = tracked_pkg.get("box_color", None)
        if tracked_color is None:
            return False, "Informații insuficiente pentru pachetul urmărit (culoare lipsă)."

        found = False
        found_position = None
        if tracked_letter is not None:
            for pkg in session_data.values():
                pkg_letters = pkg.get("letters", [])
                pkg_letter = pkg_letters[0] if pkg_letters else None
                pkg_color = pkg.get("box_color", None)
                if pkg_letter == tracked_letter and pkg_color == tracked_color:
                    found = True
                    found_position = pkg.get("position", None)
                    break
        else:
            for pkg in session_data.values():
                pkg_letters = pkg.get("letters", [])
                pkg_letter = pkg_letters[0] if pkg_letters else None
                pkg_color = pkg.get("box_color", None)
                if pkg_letter is None and pkg_color == tracked_color:
                    tracked_pos = tracked_pkg.get("position")
                    pkg_pos = pkg.get("position")
                    if tracked_pos is not None and pkg_pos is not None:
                        dx = tracked_pos[0] - pkg_pos[0]
                        dy = tracked_pos[1] - pkg_pos[1]
                        dist = (dx**2 + dy**2)**0.5
                        if dist <= 50:
                            found = True
                            found_position = pkg_pos
                            break

        if not found:
            self.sessions.clear()
            return False, "Pachetul urmărit nu a fost găsit în datele sesiunii; s-a curățat istoricul."

        session_id = self.sessions[-1]["id"] + 1 if self.sessions else 1
        session_record = {
            "id": session_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tracked_info": {
                "position": found_position,
                "letter": tracked_letter,
                "color": tracked_color
            },
            "session_data": copy.deepcopy(session_data)
        }
        if len(self.sessions) >= self.max_sessions:
            self.sessions.pop(0)
        self.sessions.append(session_record)
        return True, f"Sesiune adăugată cu id {session_id}."

    def check_validity(self):
        n = len(self.sessions)
        if n < 3:
            return False, f"Nu sunt suficiente sesiuni pentru validare (memorate: {n})."
        
        sessions_to_check = self.sessions[-3:]
        xs, ys = [], []
        for sess in sessions_to_check:
            pos = sess["tracked_info"].get("position")
            if pos is None:
                return False, "Nu s-a găsit poziția pachetului urmărit într-o sesiune."
            xs.append(pos[0])
            ys.append(pos[1])
        if (max(xs) - min(xs)) < 6 and (max(ys) - min(ys)) < 6:
            return True, "Sesiunile sunt stabile."
        else:
            return False, "Variația poziției este prea mare; sesiunile sunt instabile."

    def get_session_count(self):
        return len(self.sessions)

# Instanțiem managerul de sesiuni (maxim 5 sesiuni memorate)
session_manager = SessionManager(max_sessions=5)

# --------------------------------------------------
# FUNCȚII PENTRU DESENAREA PE CADRU
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
    box_label = f"TRACKED: {tracked_pkg.get('box_color')} / {tracked_pkg.get('letters')}"
    if w is None or h is None:
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
# NOUA FUNCȚIE: FUZIONAREA PACHETELOR SIMILARE
# --------------------------------------------------
def euclidean_distance(p1, p2):
    return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

def merge_similar_packages(session_data, merge_distance_threshold=50):
    """
    Primește un dicționar cu pachete detectate și îmbină pe cele care au:
      - Aceeași culoare și (dacă există) aceeași literă (sau niciuna)
      - Centrele pachetelor sunt mai apropiate decât merge_distance_threshold
    Returnează un nou dicționar cu pachete "îmbinate" astfel încât pentru un obiect real să
    existe doar o singură detectare (cu centru și bounding box actualizate).
    """
    groups = {}
    for key, pkg in session_data.items():
        color = pkg.get("box_color")
        letters = pkg.get("letters", [])
        letter = letters[0] if letters else None
        group_key = (color, letter)
        groups.setdefault(group_key, []).append(pkg)

    merged_packages = {}
    merged_id = 1
    for group_key, pkg_list in groups.items():
        clusters = []
        for pkg in pkg_list:
            pos = pkg.get("position")
            added = False
            for cluster in clusters:
                cluster_centroid = (
                    sum([p[0] for p in cluster["positions"]]) / len(cluster["positions"]),
                    sum([p[1] for p in cluster["positions"]]) / len(cluster["positions"])
                )
                if euclidean_distance(pos, cluster_centroid) < merge_distance_threshold:
                    cluster["positions"].append(pos)
                    cluster["packages"].append(pkg)
                    added = True
                    break
            if not added:
                clusters.append({"positions": [pos], "packages": [pkg]})
        for cluster in clusters:
            if len(cluster["packages"]) == 1:
                merged_pkg = cluster["packages"][0]
            else:
                positions = [pkg.get("position") for pkg in cluster["packages"]]
                xs = [p[0] for p in positions]
                ys = [p[1] for p in positions]
                new_center = (sum(xs)/len(xs), sum(ys)/len(ys))
                boxes = []
                for pkg in cluster["packages"]:
                    pos = pkg.get("position")
                    size = pkg.get("size")
                    if size is not None and None not in size:
                        w, h = size
                        top_left = (pos[0] - w/2, pos[1] - h/2)
                        bottom_right = (pos[0] + w/2, pos[1] + h/2)
                        boxes.append((top_left, bottom_right))
                if boxes:
                    min_x = min([b[0][0] for b in boxes])
                    min_y = min([b[0][1] for b in boxes])
                    max_x = max([b[1][0] for b in boxes])
                    max_y = max([b[1][1] for b in boxes])
                    new_size = (int(max_x - min_x), int(max_y - min_y))
                else:
                    new_size = None
                merged_pkg = {
                    "box_color": group_key[0],
                    "letters": [group_key[1]] if group_key[1] is not None else [],
                    "position": (int(new_center[0]), int(new_center[1])),
                    "size": new_size
                }
            merged_packages[f"merged_{merged_id}"] = merged_pkg
            merged_id += 1
    return merged_packages

# --------------------------------------------------
# HARTĂ DE CULORI PENTRU DESEN
# --------------------------------------------------
color_map = {
    "A": (0, 255, 0),
    "K": (255, 0, 255),
    "O": (255, 255, 255),
    "Green": (0, 255, 0),
    "Red": (255, 0, 0),
    "Sample": (255, 255, 255),
    "Blue": (0, 0, 255)
}

# --------------------------------------------------
# FUNCȚIE PENTRU PROCESAREA PACHETULUI URMĂRIT
# --------------------------------------------------
def process_tracked_package(tracked_pkg):
    global latest_cmds, latest_comanda
    x, y = tracked_pkg["position"]
    cmds = getRealCoordinates(x, y)
    x_real, y_real = cmds
    comanda = getFirstCommand(x_real, y_real)
    latest_cmds = cmds
    latest_comanda = comanda
    print(f"Tracked Package Position: {tracked_pkg['position']}")
    print("Move Commands:")
    print(cmds)
    print(comanda)
    logging.info("Suggested command: latest_cmds: {} ; latest_comanda: {}".format(cmds, comanda))
    # process_command(...)  # Execuție la confirmare, nu aici

# --------------------------------------------------
# BUCLEA PRINCIPALĂ DE PROCESARE A CAMEREI (într-un thread separat)
# --------------------------------------------------
def camera_loop():
    global tracked_package, last_session_data
    while True:
        image = picam2.capture_array()
        image = cv2.resize(image, (512, 512))
        image = cv2.rotate(image, cv2.ROTATE_180)

        detections_letters = detect_letters(picam2)
        detections_boxes   = detect_objects(picam2)

        matched_packages = assign_letters_to_packages(detections_letters, detections_boxes, threshold=5)
        box_distances    = calculate_box_distance(detections_boxes, zone_center, pass_threshold=20, max_distance=30)

        session_data = build_session_data(matched_packages, box_distances, detections_boxes)
        # Aplicăm funcția de îmbinare a pachetelor similare
        session_data = merge_similar_packages(session_data, merge_distance_threshold=MERGE_DISTANCE_THRESHOLD)
        last_session_data = session_data

        detected_packages_log = ", ".join([f"{key}: color {info['box_color']}, letter {info['letters']}, position {info['position']}" 
                                           for key, info in session_data.items()])
        logging.info("Detected packages: " + detected_packages_log)

        if tracked_package is None:
            high_pkg_key, high_pkg_info = get_high_priority_package(session_data)
            if high_pkg_key is not None:
                high_pkg_info["miss_detections"] = 0
                high_pkg_info["stable"] = False
                tracked_package = high_pkg_info
        else:
            result = update_tracked_package(tracked_package, session_data, distance_threshold=DISTANCE_JUMP_THRESHOLD)
            if result is False:
                if not tracked_package["letters"]:
                    logging.info("Pachetul fără litere nu mai este detectat => alegem un alt pachet.")
                    print("Pachetul fără litere nu mai este detectat => alegem un alt pachet.")
                    high_pkg_key, high_pkg_info = get_high_priority_package(session_data)
                    tracked_package = high_pkg_info if high_pkg_key is not None else None
                else:
                    if tracked_package is not None:
                        if "miss_detections" not in tracked_package:
                            tracked_package["miss_detections"] = 0
                        tracked_package["miss_detections"] += 1
                        if tracked_package["miss_detections"] > MISS_THRESHOLD:
                            logging.info("Pachetul urmărit a lipsit prea mult => renunțăm la urmărire.")
                            print("Pachetul urmărit a lipsit prea mult => renunțăm la urmărire.")
                            tracked_package = None
            elif result == "TOO_FAR":
                logging.info("Salt mare de distanță => renunțăm la urmărire și alegem un nou pachet.")
                print("Salt mare de distanță => renunțăm la urmărire și alegem un nou pachet.")
                tracked_package = None
                high_pkg_key, high_pkg_info = get_high_priority_package(session_data)
                tracked_package = high_pkg_info if high_pkg_key is not None else None
            else:
                tracked_package = result

        draw_detections(image, detections_boxes, color_map)

        if tracked_package is not None:
            draw_tracked_package(image, tracked_package, color=(255, 255, 0))
            status = tracked_package.get("status")
            if status != "PASS":
                print("SE PROCESEAZA COORDONATELE")
                for pkg_key, pkg_info in session_data.items():
                    print(f"{pkg_key} => {pkg_info}")
                process_tracked_package(tracked_package)

        mark_zone(image, zone_top_left, zone_bottom_right, label="Defined Zone")
        add_grid(image)

        print("\n--- SESSION DATA ---")
        for pkg_key, pkg_info in session_data.items():
            print(f"{pkg_key} => {pkg_info}")
        print("--- END SESSION DATA ---")

        cv2.imshow("Detection Output", cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    picam2.stop()
    cv2.destroyAllWindows()

# --------------------------------------------------
# Variabile pentru logica automată de trimitere a comenzilor
# --------------------------------------------------
command_phase = "normal"  # "normal", "adjust", None
skip_next_session = False

# --------------------------------------------------
# INTERFAȚA TKINTER
# --------------------------------------------------
def run_interface():
    global tracked_package, latest_cmds, latest_comanda, session_counter, last_logged_distance, distance_session_counter, distance_changed, distance_change_timestamp, last_session_data, command_phase, skip_next_session

    root = tk.Tk()
    root.title("Interfață Comenzi")

    canvas = tk.Canvas(root, width=100, height=100)
    canvas.pack(pady=10)
    square = canvas.create_rectangle(10, 10, 90, 90, fill="grey")
    text_id = canvas.create_text(50, 50, text="?", font=("Arial", 24))

    led_canvas = tk.Canvas(root, width=50, height=50)
    led_canvas.pack(pady=10)
    session_led = led_canvas.create_rectangle(10, 10, 40, 40, fill="red")
    led_label = tk.Label(root, text="Sesiuni instabile", font=("Arial", 10))
    led_label.pack()

    command_label = tk.Label(root, text="Informații comandă", font=("Arial", 14))
    command_label.pack(pady=10)

    distance_label = tk.Label(root, text="Distanță stabilă", font=("Arial", 12))
    distance_label.pack(pady=5)

    # -----------------------------
    # BUTONUL: Confirm Command
    # -----------------------------
    def confirm_command():
        global session_counter, command_phase, skip_next_session
        if latest_comanda is not None:
            # Dacă comanda nu este "1 0 0 0", se adaugă în coadă cu prioritate normală
            if tuple(latest_comanda[:4]) != (1, 0, 0, 0):
                add_command_to_queue(tuple(latest_comanda[:4]), NORMAL_PRIORITY)
            else:
                print("Nu există o comandă validă diferită de (1, 0, 0, 0).")
            execute_command_from_queue()
            print("Confirm Command executat (manual) cu comanda din coadă.")
            logging.info("MANUAL EXECUTED COMMAND (Confirm): {}".format(latest_comanda[:4]))
            session_counter = 0
            skip_next_session = True  # Flag: sesiunea următoare va fi ignorată complet
            session_manager.sessions = []
            if latest_comanda[-1] == True:
                command_phase = "adjust"
            else:
                command_phase = None
        else:
            print("Nu există comandă disponibilă.")
            logging.info("Attempt to confirm command but no command available.")

    confirm_button = tk.Button(root, text="Confirm Command", command=confirm_command, width=20)
    confirm_button.pack(pady=5)

    # -----------------------------
    # BUTONUL: Adjust Command
    # -----------------------------
    def adjust_command():
        global session_counter, command_phase, skip_next_session
        # Adăugăm comanda de ajustare în coadă cu prioritate maximă,
        # dar nu o executăm imediat; ea va fi preluată de secțiunea automată.
        add_command_to_queue((1, 13, 1, 140), ADJUST_PRIORITY)
        print("Adjust Command adăugat în coadă (manual): (1, 13, 1, 140)")
        logging.info("MANUAL COMMAND (Adjust) adăugat în coadă: (1, 13, 1, 140)")
        session_counter = 0
        skip_next_session = True  # Flag: sesiunea următoare va fi ignorată complet
        session_manager.sessions = []
        command_phase = "adjust"

    adjust_button = tk.Button(root, text="Adjust Command", command=adjust_command, width=20)
    adjust_button.pack(pady=5)

    def mark_erroneous():
        logging.info("Session marked as erroneous by user. Current tracked_package: {} | suggested command: {} | Session count: {}".format(
            tracked_package, latest_comanda, session_counter))
        print("Sesiunea a fost marcată ca având date eronate.")

    erroneous_button = tk.Button(root, text="Date Eronate", command=mark_erroneous, width=20)
    erroneous_button.pack(pady=5)

    def update_interface():
        global session_counter, last_logged_distance, distance_session_counter, distance_changed, distance_change_timestamp, command_phase, skip_next_session

        session_counter += 1

        current_distance = None
        if tracked_package is not None:
            current_distance = tracked_package.get("distance")
        if current_distance is not None:
            if last_logged_distance is None:
                last_logged_distance = current_distance
                distance_session_counter = 0
            else:
                if abs(current_distance - last_logged_distance) > 0.001:
                    last_logged_distance = current_distance
                    distance_session_counter = 0
                    distance_changed = True
                    distance_change_timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                    logging.info("Distance changed to {} at {}".format(current_distance, distance_change_timestamp))
                else:
                    distance_session_counter += 1
                    distance_changed = False

        if tracked_package is not None:
            color_mapping = {"Green": "green", "Red": "red", "Blue": "blue", "Sample": "#F5F5DC"}
            box_color = tracked_package.get("box_color", "grey")
            square_color = color_mapping.get(box_color, "grey")
            canvas.itemconfig(square, fill=square_color)
            letters = tracked_package.get("letters", [])
            display_letter = letters[0] if letters else "?"
            canvas.itemconfig(text_id, text=display_letter)
        else:
            canvas.itemconfig(square, fill="grey")
            canvas.itemconfig(text_id, text="?")

        info_text = ""
        if latest_cmds is not None:
            info_text += f"Distanță (cmd): {latest_cmds} cm\n"
        if latest_comanda is not None:
            info_text += f"Comanda: {latest_comanda}\n"
        else:
            info_text += "Nu există comandă disponibilă.\n"
        info_text += f"Sesiune: {session_counter}\n"
        if current_distance is not None:
            info_text += f"Distanță pachet: {current_distance} | Sesiuni de la schimbare: {distance_session_counter}\n"
        command_label.config(text=info_text)

        if distance_changed and distance_change_timestamp is not None:
            distance_label.config(text=f"Distanță modificată la: {distance_change_timestamp}")
        else:
            distance_label.config(text="Distanță stabilă")

        if latest_comanda is not None and len(latest_comanda) > 0:
            if latest_comanda[-1] == True:
                adjust_button.config(bg="green")
            else:
                adjust_button.config(bg="lightgrey")
        else:
            adjust_button.config(bg="lightgrey")

        logging.info("Session update {}: tracked_package: {} | suggested command: {}".format(session_counter, tracked_package, latest_comanda))

        # Dacă flag-ul skip_next_session este setat, se ignoră complet sesiunea curentă
        if skip_next_session:
            session_manager.sessions = []
            skip_next_session = False
        else:
            if tracked_package is not None and last_session_data:
                auto_success, auto_msg = session_manager.add_session(last_session_data, tracked_package)
                logging.info("Auto session add: " + auto_msg)

        # ============================================================
        # SECȚIUNEA: EXECUȚIE AUTOMATĂ A COMENZILOR (MODUL DE ACTIONARE)
        # ============================================================
        valid, validity_message = session_manager.check_validity()
        logging.info("Session validity check: Valid={} | Message: {}".format(valid, validity_message))
        if valid:
            led_canvas.itemconfig(session_led, fill="green")
            led_label.config(text="Sesiuni stabile")
            if tracked_package is not None:
                # Dacă există o comandă validă (diferită de (1,0,0,0)) și nu este necesară ajustarea,
                # se adaugă în coadă comanda normală (cu prioritate NORMAL_PRIORITY)
                if latest_comanda is not None and tuple(latest_comanda[:4]) != (1, 0, 0, 0) and command_phase != "adjust":
                    add_command_to_queue(tuple(latest_comanda[:4]), NORMAL_PRIORITY)
                # Se execută comanda din coadă (cea cu cea mai mare prioritate)
                if command_queue:
                    execute_command_from_queue()
        else:
            led_canvas.itemconfig(session_led, fill="red")
            led_label.config(text="Sesiuni instabile")
        # ============================================================

        root.after(2000, update_interface)

    update_interface()
    root.mainloop()

# --------------------------------------------------
# Pornirea aplicației: camera rulează într-un thread separat, iar interfața în thread-ul principal.
# --------------------------------------------------
if __name__ == '__main__':
    camera_thread = threading.Thread(target=camera_loop, daemon=True)
    camera_thread.start()
    run_interface()
