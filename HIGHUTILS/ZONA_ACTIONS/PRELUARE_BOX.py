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


import time
from SOURCES.UTILS.CONTROL_SERVO import executa_comanda
from SOURCES.USART_COM.serial_module import process_command





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


def process_tracked_package( session,tracked_pkg,mergi_la_risc):
    x, y  = tracked_pkg["position"]
    color = tracked_pkg["box_color"]
    letter= tracked_pkg["letters"]
    letter = letter[0] if letter and isinstance(letter, list) and len(letter) > 0 else 0



    cmds = getRealCoordinates(x, y)
    x_real, y_real = cmds



    abs_x = abs(x_real)
    abs_y = abs(y_real)


    if abs_x > 3 or abs_y > 3:
        comanda = getFirstCommand(x_real, y_real)
        latest_comanda = comanda
        print(f"SET_COARSE_CMDS: {latest_comanda} for X {x_real} and Y {y_real}")
    else:
        label, status, overlaps = evaluate_target_box(session, color, letter)
        set_cmds = getFINEcmd(overlaps)

        if set_cmds:
            latest_comanda = set_cmds[0]
            print(f"SET_FINE_CMDS: {latest_comanda} for X {x_real} and Y {y_real}")
        else:
            latest_comanda = None
            executa_comanda(9, 1)


    if x_real==0 and y_real==0 and mergi_la_risc==0:
        mergi_la_risc+=1;
        latest_comanda=None

    print(f"COORDONATE EXTRASE: {x_real}, {y_real}")
    return cmds, latest_comanda,mergi_la_risc








# State tracker
current_state = 0

# === Step Functions ===
def coborare_servo9():
    global current_state
    print("Executing coborare_servo9")
    success = executa_comanda(9, 1)
    if success:
        current_state = 1
    else:
        current_state = recover_servo9()


def coborare_servo9_fail():
    global current_state
    print("Executing coborare_servo9")
    success = executa_comanda(9, 1)
    if success:
        current_state = 2
    else:
        current_state = recover_servo9()



def adjust_box():
    global current_state
    print("Executing adjust_box")
    executa_comanda(5)
    time.sleep(2.5)
    current_state = 2

def strangere_servo10():
    global current_state
    print("Executing strangere_servo10")
    success = executa_comanda(10, 1)
    if success:
        current_state = 3
    else:
        current_state = recover_servo10()

def ridicare_servo9():
    global current_state
    print("Executing ridicare_servo9")
    executa_comanda(9, 0)
    current_state = 999  # Finished




# === Recovery Functions ===
def recover_servo9():
    print("[Recovery] Trying to recover servo 9...")
    process_command(1, 2, 2, [120]) #muta in spate
    return 0  # retry from the beginning

def recover_servo10():
    print("[Recovery] Trying to recover servo 10...")
    process_command(2, 10, 2, [0])  #recalibreaza senzoru ala prost
    time.sleep(3)
    conf = executa_comanda(9, 1)
    print(f"CONFIRMARE {conf} ca s-a coborat servo 9 ")
    if conf:
        confirm10 = executa_comanda(10, 1)
        if confirm10:
            executa_comanda(9, 0)
            return 999  # Skip to end, fully resolved
    return 4  # retry from strangere_servo10




# === Step Dispatcher ===
def run_box_lift():
    while current_state < 999:
        match current_state:
            case 0:
                coborare_servo9()
            case 1:
                adjust_box()
            case 2:
                strangere_servo10()
            case 3:
                ridicare_servo9()
            case 4:
                coborare_servo9_fail()
            case _:
                print(f"Unknown state: {current_state}")
                break

    print("Lifting sequence completed or exited.")
    return 1













#process_command(2, 10, 2, [0]) #calibrare



def run_box_tracking(session,session_id,color="Green", label="A",mergi_la_risc=1,initial_coords):


    boxdone=0;

    if session is not None:
        box = tracker.track_box(session, color, label, session_id=session_id)
        if box is not None:
            comenzi, CMD ,risc= process_tracked_package(session,color,label,mergi_la_risc)

            if initial_coords is None and not got_initial:
                initial_coords = comenzi


            if CMD and not boxdone:
                process_command(CMD[0], CMD[1], CMD[2], CMD[3])
            else:
                boxdone = run_box_lift()


    return [boxdone, initial_coords,risc]


