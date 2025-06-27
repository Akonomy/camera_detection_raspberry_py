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
mergi_la_risc=0

def process_tracked_package(tracked_pkg, session):
    x, y = tracked_pkg["position"]
    cmds = getRealCoordinates(x, y)
    x_real, y_real = cmds



    abs_x = abs(x_real)
    abs_y = abs(y_real)


    if abs_x > 3 or abs_y > 3:
        comanda = getFirstCommand(x_real, y_real)
        latest_comanda = comanda
        print(f"SET_COARSE_CMDS: {latest_comanda} for X {x_real} and Y {y_real}")
    else:
        label, status, overlaps = evaluate_target_box(session, "Green", "A")
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
    return cmds, latest_comanda



import time
from SOURCES.UTILS.CONTROL_SERVO import executa_comanda
from SOURCES.USART_COM.serial_module import process_command

import time
from SOURCES.UTILS.CONTROL_SERVO import executa_comanda
from SOURCES.USART_COM.serial_module import process_command

class BoxLifter:
    def __init__(self):
        self.call_count = 0
        self.max_retries = 2

    def lift_box(self):
        # ------------------------------
        # PAS 0: Limita generala de apeluri
        # ------------------------------
        self.call_count += 1
        if self.call_count > 5:
            print("[BoxLifter] Too many overall attempts. Aborting.")
            return False

        # ------------------------------
        # PAS 1: COBORÂRE SERVO 9 (confirm9)
        # ------------------------------
        if not self.attempt_step("confirm9", lambda: executa_comanda(9, 1), recovery=self.recover_servo9):
            return False

        # ------------------------------
        # PAS 2: AJUSTARE CUTIE (fără feedback)
        # ------------------------------
        executa_comanda(5)
        time.sleep(2.5)

        # ------------------------------
        # PAS 3: STRÂNGERE SERVO 10 (confirm10)
        # ------------------------------
        if not self.attempt_step("confirm10", lambda: executa_comanda(10, 1), recovery=self.recover_servo10):
            return False

        # ------------------------------
        # PAS 4: RIDICARE SERVO 9 (finalizare)
        # ------------------------------
        executa_comanda(9, 0)
        print("[BoxLifter] Box lifted successfully.")
        return True

    def attempt_step(self, step_name, func, recovery):
        for attempt in range(1, self.max_retries + 1):
            result = func()
            time.sleep(1)
            if result:
                print(f"[{step_name}] succeeded on attempt {attempt}")
                return True
            else:
                print(f"[{step_name}] failed on attempt {attempt}")

        print(f"[{step_name}] retry limit reached. Running recovery...")
        recovery_result = recovery()

        # interpretare rezultate recovery
        if recovery_result == 1:
            print(f"[{step_name}] entire sequence completed during recovery")
            return True
        elif recovery_result == 2:
            print(f"[{step_name}] step recovered successfully, retrying step...")
            result = func()
            return result
        elif recovery_result == 3:
            print(f"[{step_name}] recovery requested to step down and retry from earlier")
            return False

        print(f"[{step_name}] failed after recovery.")
        return False

    def recover_servo9(self):
        # ------------------------------
        # RECOVERY pentru SERVO 9
        # ------------------------------
        print("[Recovery] Trying to recover servo 9...")
        process_command(1, 2, 2, [120])  # mută în spate
        return 3  # step down to retry from earlier

    def recover_servo10(self):
        # ------------------------------
        # RECOVERY pentru SERVO 10
        # ------------------------------
        print("[Recovery] Trying to recover servo 10...")
        process_command(2, 10, 2, [0])  # calibrare

        conf = executa_comanda(9, 1)
        if conf:
            confirm10 = executa_comanda(10, 1)
            if confirm10:
                executa_comanda(9, 0)
                return 1  # complet rezolvat


        return 3  # nu a mers, încearcă de la început




# def ridica_cutia(count_call):




#     confirm9 = executa_comanda(9, 1)
#     time.sleep(1)
#     print(f"{confirm9} CONFIRMARE9")
#     if confirm9:
#         executa_comanda(5)
#         time.sleep(3)
#         confirm10 = executa_comanda(10, 1)
#         if confirm10:
#             executa_comanda(9, 0)
#             counter = 20
#             boxdone = 1
#         else:
#             confirm10 = executa_comanda(10, 1)
#             if confirm10:
#                 executa_comanda(9, 0)
#                 counter = 20
#                 boxdone = 1









#process_command(2, 10, 2, [0]) #calibrare



def run_box_tracking(session_id, color, label):
    try:
        init_camera()
        print("Camera inițializată pentru sesiune.")
        boxdone = 0
        mergi_la_risc=0;



        move_commands_history = []
        initial_coords = None
        box_lifter = BoxLifter()


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
                        boxdone = box_lifter.lift_box()


            if boxdone:
                return [1, initial_coords, move_commands_history]

    except Exception as e:
        print("A apărut o eroare:", e)
    finally:
        stop_camera()


if __name__ == "__main__":
    run_box_tracking()
