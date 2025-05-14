import os
import sys
import json

# Asigurăm importul clientului
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from robot_api_client import RobotAPIClient



def request_box(ID_CODE):
    client = RobotAPIClient()

    try:

        container = client.check_container(ID_CODE)
        return container

    except:
        print(f"[ERROR handle_container] NU s-a putut prelua detaliile cutiei pentru id {ID_CODE}")
        return -1
    