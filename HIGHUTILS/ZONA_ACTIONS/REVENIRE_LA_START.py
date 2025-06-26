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




def move_to_initial(coords):
    x,y=coords
    x=-x
    y=-y

    commands=getAllCommands(x,y)
    if commands :

        for CMD in commands:

                process_command(CMD[0], CMD[1], CMD[2], CMD[3])
                time.sleep(3)

        return 1

    return 0











