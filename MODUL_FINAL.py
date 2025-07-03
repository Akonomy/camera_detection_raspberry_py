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


from SOURCES.WEB.robot_api_client.py import RobotAPIClient


client = RobotAPIClient()







#------<pornire robot initializare>

initializare()
init_camera()
client.update_robot_status('idle', message='Robotul a pornit')



#---------<calibrare robot si citire first tag to update

result=calibrate_tag_position()
print(result)





#----------<get first task from WMS and process it
client.update_robot_status('busy', message='Robotul cere si executa un task')

data=process_and_resolve_move_task()
# returneaza {task_id, box_id and path_id}
task_id=data["task_id"]
path_id=data["path_id"]
box_id=data["box_id"]

#extragere detalii despre cutie
box_color=get_param_task(task_id,"color")
box_letter=get_param_task(task_id,"letters")
box=box_color+box_letter



print(f"SE EXECUTA TASKUL  {task_id}")
traseu=get_param_task(task_id,"path_stm32")

client.update_task_status(task_id, 'accepted', reason='Transferat catre robot')

#-----------<trimitere traseu catre executie la stm32

print(f"SE EFECTUEAZA TRASEUL {traseu[0]} ")
data=send_path(traseu[0])
print(f"DATA PRIMIT DE LA STM{ data}")  #pas FAULTY eroare

client.update_task_status(task_id, 'in_progress', reason='Transferat catre robot')




-------------<PRELUAREA CUTIEI

client.update_robot_status('busy', message='Robotul ia cutia')

print(f" SE PREIA CUTIA {box_color} cu ID {box_letter} ")
boxdone=0
risc=0
initial_coords=None

while not boxdone:
    image,session=capture_and_process_session()

    boxdone, initial_coords,risc=run_box_tracking(session,task_id,box_color,box_letter,risc,initial_coords)



moved=move_to_initial(initial_coords)   #revenire la start, la pozitia de parcare
time.sleep(1)
revenire_la_traseu(moved) #revenire la traseu adica la linie







#verificare daca a revenit la traseu  daca nu ruleaza modelul de urmarire linie pe baza camerei
# I HOPE EVERYTHING IS GOOD AND DONT NEED THAT MODULE



#ruleaza modelul , trimite comanda , asteapta raspuns(de implementat pe stm raspuns si can dnu gasest elinia sa stiu)




#-----------<execute second path to next zone
send_path(traseu[1])

client.update_task_status(task_id, 'in_progress', reason='Cutie preluata')




#-----------<predare cutie

image,session=capture_and_process_session()
predare_cutie(image,session,box)






#revenire la task sau la dock

client.update_task_status(task_id, 'completed', reason='Cutie livrata ')
client.update_robot_status('idle', message='Asteapta comenzi')


# actualizare task ca fiind completat



stop_camera()


print(f"REZULTAT{test}, moved {moved}")


