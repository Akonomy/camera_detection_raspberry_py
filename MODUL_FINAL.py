import time
from HIGHUTILS.ZONA_ACTIONS.PRELUARE_BOX import  run_box_tracking
from HIGHUTILS.ZONA_ACTIONS.REVENIRE_LA_START import  move_to_initial,revenire_la_traseu
from HIGHUTILS.ZONA_ACTIONS.PREDARE_BOX import predare_cutie


#pornire robot initializare


#calibrare robot si citire first tag to update


#get first task from WMS



#execute first path to zone



test=run_box_tracking(30, "Green", "A")   #preluare CUTIE

moved=move_to_initial(test[1])   #revenire la start

time.sleep(1)

revenire_la_traseu(moved) #revenire la traseu



#execute second path to next zone



#predare cutie


#revenire la task sau la dock





print(f"REZULTAT{test}, moved {moved}")


