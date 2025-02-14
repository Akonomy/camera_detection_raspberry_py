import cv2
import time
import threading
import tkinter as tk
from tkinter import ttk
from picamera2 import Picamera2

# Importă funcțiile de comunicare și de calcul a comenzilor
from USART_COM.serial_module import process_command
from UTILS.get_directions import get_next_move_command_for_position
from UTILS.get_directions import get_all_move_commands_for_position
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
    w, h = tracked_pkg["size"]
    box_label = f"TRACKED: {tracked_pkg['box_color']} / {tracked_pkg['letters']}"
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
# HARTĂ DE CULORI PENTRU DESEN
# --------------------------------------------------
color_map = {
    "A": (0, 255, 0),      # Verde
    "K": (255, 0, 255),    # Magenta
    "O": (255, 255, 255),  # Alb
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
    # Preia poziția pachetului urmărit
    x, y = tracked_pkg["position"]
    # Obține coordonatele reale
    cmds = getRealCoordinates(x, y)
    x_real, y_real = cmds
    # Obține comanda de mișcare (ultima valoare este un flag boolean)
    comanda = getFirstCommand(x_real, y_real)
    # Actualizează variabilele globale pentru interfață
    latest_cmds = cmds
    latest_comanda = comanda
    print(f"Tracked Package Position: {tracked_pkg['position']}")
    print("Move Commands:")
    print(cmds)
    print(comanda)
    # COMANDA ce misca mașina (se execută doar la confirmare din interfață)
    # process_command(param1, param2, param3, param4)

# --------------------------------------------------
# BUCLEA PRINCIPALĂ DE PROCESARE A CAMEREI (rulează într-un thread separat)
# --------------------------------------------------
def camera_loop():
    global tracked_package
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

        # 4) Construiește datele de sesiune
        session_data = build_session_data(matched_packages, box_distances, detections_boxes)

        # 5) Alege sau actualizează pachetul urmărit
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
                    if tracked_package is not None:
                        if "miss_detections" not in tracked_package:
                            tracked_package["miss_detections"] = 0
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

        # 6) Desenează toate detecțiile pe imagine
        draw_detections(image, detections_boxes, color_map)

        # 7) Dacă există un pachet urmărit, îl desenăm și generăm comenzile de mișcare
        if tracked_package is not None:
            draw_tracked_package(image, tracked_package, color=(255, 255, 0))
            status = tracked_package["status"]
            if status != "PASS":
                print("SE PROCESEAZA COORDONATELE")
                for pkg_key, pkg_info in session_data.items():
                    print(f"{pkg_key} => {pkg_info}")
                process_tracked_package(tracked_package)

        # 8) Desenează zona definită și grid-ul
        mark_zone(image, zone_top_left, zone_bottom_right, label="Defined Zone")
        add_grid(image)

        # 9) (Opțional) Afișează datele de sesiune în consolă
        print("\n--- SESSION DATA ---")
        for pkg_key, pkg_info in session_data.items():
            print(f"{pkg_key} => {pkg_info}")
        print("--- END SESSION DATA ---")

        # 10) Afișează cadrul final
        cv2.imshow("Detection Output", cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    picam2.stop()
    cv2.destroyAllWindows()

# --------------------------------------------------
# INTERFAȚA TKINTER PENTRU CONFIRMAREA MANUALĂ A COMENZILOR
# --------------------------------------------------
def run_interface():
    global tracked_package, latest_cmds, latest_comanda
    root = tk.Tk()
    root.title("Interfață Comenzi")

    # Slotul vizual: un canvas cu un pătrat care va fi colorat conform box_color-ului pachetului urmărit
    canvas = tk.Canvas(root, width=100, height=100)
    canvas.pack(pady=10)
    square = canvas.create_rectangle(10, 10, 90, 90, fill="grey")
    text_id = canvas.create_text(50, 50, text="?", font=("Arial", 24))

    # Etichetă pentru afișarea informațiilor despre comandă (distanță și comanda completă)
    command_label = tk.Label(root, text="Informații comandă", font=("Arial", 14))
    command_label.pack(pady=10)

    # Butonul "Confirm Command" – extrage primele 4 valori din latest_comanda și apelează process_command
    def confirm_command():
        if latest_comanda is not None:
            command_params = latest_comanda[:4]  # Ignoră ultimul element (boolean)
            process_command(*command_params)
            print("Confirm Command executat:", command_params)
        else:
            print("Nu există comandă disponibilă.")

    confirm_button = tk.Button(root, text="Confirm Command", command=confirm_command, width=20)
    confirm_button.pack(pady=5)

    # Butonul "Adjust Command" – apelează process_command(1, 13, 1, 140)
    def adjust_command():
        process_command(1, 13, 1, 140)
        print("Adjust Command executat: (1, 13, 1, 140)")

    adjust_button = tk.Button(root, text="Adjust Command", command=adjust_command, width=20)
    adjust_button.pack(pady=5)

    # Funcția de update a interfeței, rulată la fiecare 2 secunde
    def update_interface():
        # Actualizează slotul cu culoare și literă, în funcție de tracked_package
        if tracked_package is not None:
            color_mapping = {
                "Green": "green",
                "Red": "red",
                "Blue": "blue",
                "Sample": "#F5F5DC"  # bej
            }
            box_color = tracked_package.get("box_color", "grey")
            square_color = color_mapping.get(box_color, "grey")
            canvas.itemconfig(square, fill=square_color)
            letters = tracked_package.get("letters", [])
            display_letter = letters[0] if letters else "?"
            canvas.itemconfig(text_id, text=display_letter)
        else:
            canvas.itemconfig(square, fill="grey")
            canvas.itemconfig(text_id, text="?")
        # Actualizează informațiile despre comandă
        info_text = ""
        if latest_cmds is not None:
            info_text += f"Distanță: {latest_cmds[0]} cm\n"
        if latest_comanda is not None:
            info_text += f"Comanda: {latest_comanda}\n"
        else:
            info_text += "Nu există comandă disponibilă."
        command_label.config(text=info_text)
        # Actualizează culoarea butonului "Adjust Command": devine verde dacă ultimul element din latest_comanda este True
        if latest_comanda is not None and len(latest_comanda) > 0:
            if latest_comanda[-1] == True:
                adjust_button.config(bg="green")
            else:
                adjust_button.config(bg="lightgrey")
                
        else:
            adjust_button.config(bg="lightgrey")
            
        root.after(2000, update_interface)

    update_interface()
    root.mainloop()

# --------------------------------------------------
# Pornirea aplicației: bucla camerei rulează într-un thread separat,
# iar interfața Tkinter rulează în thread-ul principal.
# --------------------------------------------------
if __name__ == '__main__':
    camera_thread = threading.Thread(target=camera_loop, daemon=True)
    camera_thread.start()
    run_interface()
