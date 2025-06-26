from HIGHUTILS.ZONA_ACTIONS.PRELUARE_BOX import  run_box_tracking
from HIGHUTILS.ZONA_ACTIONS.REVENIRE_LA_START import  move_to_initial




test=run_box_tracking(30, "Green", "A")

moved=move_to_initial(test[1])


print(f"REZULTAT{test}, moved {moved}")
