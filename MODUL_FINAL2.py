import time
import cv2


from HIGHUTILS.CALIBRARI.calibrare import  calibrate_tag_position


from HIGHUTILS.WEB_REQUEST.task_resolver import process_and_resolve_move_task


from HIGHUTILS.DATABASE_ACTIONS.handler_database import set_param_task, get_param_task,get_task_info
from HIGHUTILS.ZONA_ACTIONS.PRELUARE_BOX import  run_box_tracking
from HIGHUTILS.ZONA_ACTIONS.REVENIRE_LA_START import  move_to_initial,revenire_la_traseu,initializare
from HIGHUTILS.ZONA_ACTIONS.PREDARE_BOX import predare_cutie
from HIGHUTILS.ZONA_ACTIONS.COM_STM32 import send_path




from SOURCES.CAMERA.camera_session import init_camera, stop_camera, capture_and_process_session


#------<pornire robot initializare>

initializare()
init_camera()



def etapa_calibrare():
    result = calibrate_tag_position()
    print(result)
    return result

def etapa_primire_task():
    data = process_and_resolve_move_task()
    task_id = data["task_id"]
    path_id = data["path_id"]
    box_id = data["box_id"]
    return task_id, path_id, box_id

def etapa_extragere_detalii(task_id):
    box_color = get_param_task(task_id, "color")
    box_letter = get_param_task(task_id, "letters")
    box = box_color + box_letter
    traseu = get_param_task(task_id, "path_stm32")
    return box_color, box_letter, box, traseu

def etapa_trimitere_traseu(traseu):
    print(f"SE EFECTUEAZA TRASEUL {traseu[0]} ")
    data = send_path(traseu[0])
    print(f"DATA PRIMIT DE LA STM{ data}")
    return data

def etapa_preluare_cutie(task_id, box_color, box_letter):
    boxdone = 0
    risc = 0
    initial_coords = None
    while not boxdone:
        image, session = capture_and_process_session()
        boxdone, initial_coords, risc = run_box_tracking(session, task_id, box_color, box_letter, risc, initial_coords)
    return initial_coords

def etapa_revenire_la_start(initial_coords):
    moved = move_to_initial(initial_coords)
    time.sleep(1)
    revenire_la_traseu(moved)
    return moved

def etapa_predare_cutie(box):
    image, session = capture_and_process_session()
    predare_cutie(image, session, box)

def executa_task_complet():


   # etapa_calibrare()



    task_id, path_id, box_id = etapa_primire_task()
    box_color, box_letter, box, traseu = etapa_extragere_detalii(task_id)


    # etapa_trimitere_traseu(traseu)
    # print(f" SE PREIA CUTIA {box_color} cu ID {box_letter} ")
    # initial_coords = etapa_preluare_cutie(task_id, box_color, box_letter)
    # moved = etapa_revenire_la_start(initial_coords)
    # send_path(traseu[1])


    etapa_predare_cutie(box)
    stop_camera()
    print(f"REZULTAT: moved={moved}")











executa_task_complet()
