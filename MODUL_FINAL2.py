import time
import cv2


from HIGHUTILS.CALIBRARI.calibrare import  calibrate_tag_position


from HIGHUTILS.WEB_REQUEST.task_resolver import process_and_resolve_move_task


from HIGHUTILS.DATABASE_ACTIONS.handler_database import set_param_task, get_param_task,get_task_info
from HIGHUTILS.ZONA_ACTIONS.PRELUARE_BOX import  run_box_tracking
from HIGHUTILS.ZONA_ACTIONS.REVENIRE_LA_START import  move_to_initial,revenire_la_traseu,initializare
from HIGHUTILS.ZONA_ACTIONS.PREDARE_BOX import predare_cutie
from HIGHUTILS.ZONA_ACTIONS.COM_STM32 import send_path,read2




from SOURCES.CAMERA.camera_session import init_camera, stop_camera, capture_and_process_session


from SOURCES.WEB.robot_api_client import RobotAPIClient


client = RobotAPIClient()




#------<pornire robot initializare>

initializare()
init_camera()


client.update_robot_status('idle', message='Asteapta comenzi')




def etapa_calibrare():
    result = calibrate_tag_position()
    print(result)
    return result

def etapa_primire_task():
    data = process_and_resolve_move_task()
    task_id = data["task_id"]
    path_id = data["path_id"]
    box_id = data["box_id"]
    id_task=task_id.strip("task_")

    print (f" IN PROGRESS  {task_id}, with code {box_id} ")
    client.update_task_status(id_task, 'accepted', reason='thanks')
    client.update_robot_status('busy', message=f'Efectueaza taskul {task_id}')
    return task_id, path_id, box_id,id_task

def etapa_extragere_detalii(task_id):
    box_color = get_param_task(task_id, "color")
    box_letter = get_param_task(task_id, "letters")
    box = box_color + box_letter
    traseu = get_param_task(task_id, "path_stm32")
    target_zone=  get_param_task(task_id, "zone_target")

    return box_color, box_letter, box, traseu,target_zone

def etapa_trimitere_traseu(traseu):
    print(f"SE EFECTUEAZA TRASEUL {traseu[0]} ")
    data = send_path(traseu[0])
    print(f"SEND { data}")
    time.sleep(15)
    data=read2()

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

def etapa_predare_cutie(box,box_id,target_zone):
    image, session = capture_and_process_session()
    predare_cutie(image, session, box)


    # 3. Modificare zonă container
    change_resp = client.change_container_zone(box_id, target_zone)




def executa_task_complet():


    etapa_calibrare()



    task_id, path_id, box_id ,id_task = etapa_primire_task()
    box_color, box_letter, box, traseu, target_zone = etapa_extragere_detalii(task_id)


    etapa_trimitere_traseu(traseu)
    print(f" SE PREIA CUTIA {box_color} cu ID {box_letter} ")
    initial_coords = etapa_preluare_cutie(task_id, box_color, box_letter)
    moved = etapa_revenire_la_start(initial_coords)
    send_path(traseu[1])


    etapa_predare_cutie(box,box_id,target_zone)
    stop_camera()

    client.update_task_status(id_task, 'completed', reason='finalizat')
    client.update_robot_status('idle', message=f'Finalizat task')
    print(f"REZULTAT: moved={moved}")











executa_task_complet()
