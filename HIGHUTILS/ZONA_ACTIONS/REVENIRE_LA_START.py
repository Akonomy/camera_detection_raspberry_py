#REVENIRE_LA_START.py
import os
import sys
import time


# Path adjustments
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..','..'))
if project_root not in sys.path:
    sys.path.append(project_root)

# Internal imports
from SOURCES.USART_COM.serial_module import process_command
from SOURCES.UTILS.COARSE_DIRECTIONS import getAllCommands
from SOURCES.UTILS.CONTROL_SERVO import revenire_traseu



def move_to_initial(coords):
    x,y=coords

    if x != 0:
        x += 3 * (1 if x > 0 else -1)

    if y != 0:
        y += 2 * (1 if y > 0 else -1)


    x=-x
    y=-y

    commands=getAllCommands(x,y)
    if commands :

        for CMD in commands:

                process_command(CMD[0], CMD[1], CMD[2], CMD[3])
                time.sleep(3)

        return CMD[2]

    return 0




def revenire_la_traseu(cmd):
    #cmd = 9 if cmd == 10 else 10

    result = revenire_traseu(cmd)

    print( result )

    return 1









def initializare():

    process_command(5, 0, 1, [0])  #se trimite modul 0 ca si start
    time.sleep(0.5)
    process_command(5, 0, 1, [0])  #se retrimite modul 0 ca si start deoarece prima cmd trimisa e trash pt initializare COM
