import os
import sys
import time

import cv2

# Path adjustments
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..','..'))
if project_root not in sys.path:
    sys.path.append(project_root)

# Internal imports
from SOURCES.USART_COM.serial_module import process_command
from SOURCES.UTILS.get_directions import get_next_move_command_for_position, get_all_move_commands_for_position
from SOURCES.UTILS.REAL import getRealCoordinates
from SOURCES.UTILS.COARSE_DIRECTIONS import getFirstCommand
from SOURCES.UTILS.BOX_ALIGNMENT_FINE import BoxTracker, evaluate_target_box
from SOURCES.UTILS.FINE_DIRECTIONS import getFINEcmd
from SOURCES.UTILS.CONTROL_SERVO import executa_comanda
from SOURCES.CAMERA.camera_session import init_camera, stop_camera, capture_and_process_session

# Color map for reference
color_map = {
    "A": (0, 255, 0),
    "K": (255, 0, 255),
    "O": (255, 255, 255),
    "Green": (0, 255, 0),
    "Red": (255, 0, 0),
    "Sample": (255, 255, 255),
    "Blue": (0, 0, 255)
}

# Initialize tracker
tracker = BoxTracker()

def process_tracked_package(tracked_pkg, session):
    x, y = tracked_pkg["position"]
    cmds = getRealCoordinates(x, y)
    x_real, y_real = cmds

    abs_x = abs(x_real)
    abs_y = abs(y_real)

    if abs_x > 3 or abs_y > 3:
        comanda = getFirstCommand(x_real, y_real)
        latest_comanda = comanda
    else:
        label, status, overlaps = evaluate_target_box(session, "Green", "A")
        set_cmds = getFINEcmd(overlaps)
        if set_cmds:
            latest_comanda = set_cmds[0]
        else:
            latest_comanda = None
            executa_comanda(9, 1)

    print(f"COORDONATE EXTRASE: {x_real}, {y_real}")
    return cmds, latest_comanda

def run_box_tracking(session_id, color, label):
    try:
        init_camera()
        print("Camera inițializată pentru sesiune.")
        boxdone = 0
        move_commands_history = []
        initial_coords = None

        while True:
            image, session = capture_and_process_session()
            if session is not None:
                box = tracker.track_box(session, color, label, session_id=session_id)
                if box is not None:
                    comenzi, CMD = process_tracked_package(box, session)

                    if initial_coords is None:
                        initial_coords = comenzi

                    x_real, y_real = comenzi
                    if abs(x_real) > 3 or abs(y_real) > 3:
                        move_commands_history.append(CMD)

                    print(CMD)
                    if CMD and not boxdone:
                        process_command(CMD[0], CMD[1], CMD[2], CMD[3])
                    else:
                        counter = 0
                        while counter < 2 and not boxdone:
                            counter += 1
                            confirm9 = executa_comanda(9, 1)
                            time.sleep(1)
                            print(f"{confirm9} CONFIRMARE9")
                            if confirm9:
                                executa_comanda(5)
                                time.sleep(3)
                                confirm10 = executa_comanda(10, 1)
                                if confirm10:
                                    executa_comanda(9, 0)
                                    counter = 20
                                    boxdone = 1
            if boxdone:
                return 1, initial_coords, move_commands_history

    except Exception as e:
        print("A apărut o eroare:", e)
    finally:
        stop_camera()
