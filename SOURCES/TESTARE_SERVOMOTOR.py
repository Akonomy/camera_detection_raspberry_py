#TESTARE_SERVOMOTOR.py
# ===================================================
# IMPORTURI
# ===================================================

# Importuri pentru modulele interne
from USART_COM.serial_module import process_command
from UTILS.get_directions import get_next_move_command_for_position, get_all_move_commands_for_position
from UTILS.REAL import getRealCoordinates
from UTILS.COARSE_DIRECTIONS import getFirstCommand
from UTILS.BOX_ALIGNMENT_FINE import BoxTracker, evaluate_target_box
from UTILS.FINE_DIRECTIONS import getFINEcmd
from UTILS.CONTROL_SERVO import executa_comanda



import cv2
import time
from CAMERA.camera_session import init_camera, stop_camera, capture_raw_image, capture_and_process_session
from CAMERA.tracked_position import track_position, track_with_detailed_analysis






app=executa_comanda(9,1)
print(f"CMD91{app[0]}")

app=executa_comanda(9,0)
print(f"CMD90{app}")

app=executa_comanda(10,1)
print(app)

app=executa_comanda(10,0)
print(app)

#app=executa_comanda(5,1)
# print(app)

