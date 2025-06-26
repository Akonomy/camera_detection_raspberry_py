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
    x, y = tracked_pkg["position"]  # eliminat caracterul '/'
    cmds = getRealCoordinates(x, y)
    x_real, y_real = cmds
    print(f"COORDONATE EXTRASE:{x_real},{y_real}")
    comanda = getFirstCommand(x_real, y_real)
    latest_cmds = cmds
    latest_comanda = comanda
   
    return latest_cmds, latest_comanda
    # Execuția se face la confirmare, nu aici.

#process_command(*("cmd_placeholder",))  # linie exemplificativă, se va înlocui cu o comandă reală


if __name__ == "__main__":
    try:
        # Inițializarea camerei
        init_camera()
        print("Camera a fost inițializată. Apasă 'q' în fereastra imaginii pentru a opri.")

        # Exemplu de loop principal cu waitKey:
        while True:

            # Capturează o imagine raw de la cameră
            image , session= capture_and_process_session()

            if session is not None:
                box=session.get('GreenA')
                if box is not None:

                    comenzi, CMD = process_tracked_package(box)

                    print(CMD)
                    

                    process_command(CMD[0],CMD[1],CMD[2],CMD[3])
            # Se poate aplica un proces suplimentar pe imagine dacă este nevoie
            cv2.imshow("Raw Image", image)

           # print(session)



            # Verifică dacă s-a apăsat tasta 'q' pentru a opri loop-ul
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cv2.destroyAllWindows()

    except Exception as e:
        print("A apărut o eroare:", e)
    finally:
        # Oprește camera înainte de a ieși
        stop_camera()
