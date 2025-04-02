# ===================================================
# IMPORTURI
# ===================================================

# Importuri pentru modulele interne
from USART_COM.serial_module import process_command
from UTILS.get_directions import get_next_move_command_for_position, get_all_move_commands_for_position
from UTILS.REAL import getRealCoordinates
from UTILS.COARSE_DIRECTIONS import getFirstCommand

import cv2
import time
from CAMERA.camera_session import init_camera, stop_camera, capture_raw_image, capture_and_process_session
from CAMERA.tracked_position import track_position, track_with_detailed_analysis

# Hartă de culori pentru desen
color_map = {
    "A": (0, 255, 0),
    "K": (255, 0, 255),
    "O": (255, 255, 255),
    "Green": (0, 255, 0),
    "Red": (255, 0, 0),
    "Sample": (255, 255, 255),
    "Blue": (0, 0, 255)
}

# ===================================================
# FUNCTII DE PROCESARE A PACHETULUI ȘI EXECUȚIE AUTOMATĂ
# ===================================================

def process_tracked_package(tracked_pkg):
    """Procesează pachetul urmărit: determină coordonatele reale și comanda de mișcare, apoi
       afișează informațiile și loghează rezultatele.

       PRIMESTE UN BOX; RETURNEAZĂ comenzile pentru funcția process_command.
    """
    # Extrage poziția din pachetul urmărit
    x, y = tracked_pkg["position"]
    cmds = getRealCoordinates(x, y)
    x_real, y_real = cmds
    print("Coordonate reale:", x_real, y_real)
    comanda = getFirstCommand(x_real, y_real)
    
    latest_cmds = cmds
    latest_comanda = comanda
   
    return latest_cmds, latest_comanda

if __name__ == "__main__":
    try:
        # Inițializarea camerei
        init_camera()
        print("Camera a fost inițializată. Apasă 'q' în fereastra imaginii pentru a opri.")

        # Flag pentru a verifica dacă poziția inițială a fost setată
        initial_position_set = False
        # Variabila în care se va stoca poziția actualizată a pachetului
        tracked_center = None

        # Loop-ul principal
        while True:
            # Capturează o imagine raw și sesiunea de procesare
            image, session = capture_and_process_session()

            if session is not None:
                box = session.get('GreenA')
                if box is not None:
                    if not initial_position_set:
                        # La prima detectare se setează poziția inițială din pachet
                        tracked_center = box["position"]
                        initial_position_set = True
                    else:
                        # Actualizează poziția folosind funcția de tracking
                        # Tracking-ul poate fi realizat fie pe baza imaginii curente,
                        # fie folosind alte date din pachet, aici folosim funcția track_position
                        tracking_result = track_position(image)
                        # Se presupune că 'center' reprezintă poziția actualizată
                        tracked_center = tracking_result["center"]
                    
                    # Desenează un cerc pe poziția actuală a pachetului
                    cv2.circle(image, tracked_center, 10, color_map["Green"], 2)

                    # Procesează pachetul urmărit și execută comanda corespunzătoare
                    comenzi, CMD = process_tracked_package(box)
                    print("Comanda calculată:", CMD)
                    process_command(CMD[0], CMD[1], CMD[2], CMD[3])

            # Afișează imaginea procesată
            cv2.imshow("Raw Image", image)

            # Verifică dacă s-a apăsat tasta 'q' pentru a opri loop-ul
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cv2.destroyAllWindows()

    except Exception as e:
        print("A apărut o eroare:", e)
    finally:
        # Oprește camera înainte de a ieși
        stop_camera()
