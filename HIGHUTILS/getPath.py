import sys
import os

# Adaugă directorul "FINAL" în sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from SOURCES.WEB.robot_api_client  import RobotAPIClient
from SOURCES.TRASEU import find_route


#importa get current location , pana atunci curerent location e 'C[8][2]'

client=RobotAPIClient()

task=client.fetch_first_task()
print(task)
