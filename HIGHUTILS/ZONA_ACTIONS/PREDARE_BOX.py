import os
import sys
import time

import cv2

# Path adjustments
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..','..'))
if project_root not in sys.path:
    sys.path.append(project_root)

# Internal imports


from SOURCES.UTILS.REAL import getRealCoordinates


from SOURCES.UTILS.BOX_ALIGNMENT_FINE import BoxTracker, evaluate_target_box
from SOURCES.UTILS.FINE_DIRECTIONS import getFINEcmd
from SOURCES.UTILS.CONTROL_SERVO import executa_comanda
from SOURCES.USART_COM.serial_module import process_command
from SOURCES.UTILS.COARSE_DIRECTIONS import getFirstCommand, getAllCommands
from SOURCES.CAMERA.camera_session import init_camera, stop_camera, capture_and_process_session
from SOURCES.UTILS.GET_FREE import analyze_zone_and_find_spot
from SOURCES.UTILS.COARSE_DIRECTIONS import getAllCommands




def move_to_initial(coords,reverse=0):


    x,y=coords
    if reverse:
        x=-x
        y=-y


    commands=getAllCommands(x,y)
    if commands :

        for CMD in commands:

                process_command(CMD[0], CMD[1], CMD[2], CMD[3])
                time.sleep(3)

        return 1

    return 0






def get_free_spot(box_id):
    init_camera()


    # Capturează imaginea și sesiunea
    image_copy, session_data = capture_and_process_session()
    
    # Apelează funcția de analiză pentru a căuta un loc liber, cu max_boxes=3 și debug=True
    result = analyze_zone_and_find_spot(image_copy, session_data, max_boxes=3, ignore_box_id=box_id, debug=False)
    
    return result





def predare_cutie(box_id):


    coords=get_free_spot(box_id)

    move_to_initial(coords)


    predare9=executa_comanda(9,1)
    time.sleep(0.5)
    if predare9:
        executa_comanda(10,0)

        executa_comanda(9,0)

        time.sleep(1)

        move_to_initial(coords,1)



    else:

        return 0














predare_cutie("GreenA")
