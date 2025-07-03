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

        if x != 0:
            x += 2 * (1 if x > 0 else -1)

        if y != 0:
            y += 2 * (1 if y > 0 else -1)



    commands=getAllCommands(x,y)
    if commands :

        for CMD in commands:

                process_command(CMD[0], CMD[1], CMD[2], CMD[3])
                time.sleep(3)

        return CMD[2]

    return 0



def round_to_half(x):
    return round(x * 2) / 2



def get_free_spot(image_copy,session_data,box_id):

    
    # Apelează funcția de analiză pentru a căuta un loc liber, cu max_boxes=3 și debug=True
    result = analyze_zone_and_find_spot(image_copy, session_data, max_boxes=3, ignore_box_id=box_id, debug=False)


    if isinstance(result, tuple) and len(result) == 2:
        x,y=result
        x_norm = round_to_half(x)
        y_norm = round_to_half(y)
        return x_norm,y_norm


    
    return result





def predare_cutie(image,session,box_id):


    coords=get_free_spot(image,session,box_id)
    print(coords)






    if isinstance(coords, tuple) and len(coords) == 2:
        move_to_initial(coords)



        predare9=executa_comanda(9,1)
        time.sleep(0.5)
        if predare9:
            executa_comanda(10,0)

            executa_comanda(9,0)

            time.sleep(1)

            last_cmd=move_to_initial(coords,1)

            time.sleep(0.5)

            if last_cmd in (10,9):


                process_command(5, last_cmd, 1, [0])

            else:
                process_command(5, 10, 1, [0])

            return 1





    else:
        print(f"ZONA ESTE FULL: STATUS:{coords}")
        time.sleep(10)

        coords=get_free_spot(image,session,box_id)
        print(coords)


        if isinstance(coords, tuple) and len(coords) == 2:
            move_to_initial(coords)




            predare9=executa_comanda(9,1)
            time.sleep(0.5)
            if predare9:
                executa_comanda(10,0)

                executa_comanda(9,0)

                time.sleep(1)

                last_cmd=move_to_initial(coords,1)

                time.sleep(0.5)

                if last_cmd in (10,9):


                    process_command(5, last_cmd, 1, [0])

                else:
                    process_command(5, 10, 1, [0])

                return 1










    return 0






if __name__ == "__main__":
    predare_cutie("GreenA");




