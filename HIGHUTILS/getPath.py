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




import re

def extract_task_info(task):
    # Extract fields from the task dictionary
    task_data = task.get('task', {})
    task_id = task_data.get('id')
    task_type = task_data.get('task_type')
    source_section = task_data.get('source_section', {})
    target_section = task_data.get('target_section', {})

    # Extract type and number from the 'name' field using regex pattern
    # The pattern assumes the format "Type_Number" e.g., "Depozit_4"
    source_type = source_section.get('type', '')
    target_type = target_section.get('type', '')
    
    source_name = source_section.get('name', '')
    target_name = target_section.get('name', '')


    nr_source = re.search(r'_(\d+)', source_name)
    nr_target = re.search(r'_(\d+)', target_name)
    
    if nr_source and nr_target:
        
        nr_source = int(nr_source.group(1))
        nr_target = int(nr_target.group(1))
    
   
    source_name=source_type+str(nr_source)
    target_name=target_type+str(nr_target)
    
    
    source_name,target_name = source_name.upper(),target_name.upper()


    return task_id, task_type, source_name, target_name




def find_zone(zone_name, zones):
    # Search for a zone where the name contains the zone_name substring
    for key, name in zones.items():
        if zone_name in name:
            return key, name
    return None, None





# Define a helper function that calculates the route based on current_location type.
def calculate_route(current_loc, destination_key):
    if current_loc.startswith('I'):
        fast_path = find_route.getfastPathFromCross(current_loc, destination_key)
        complete_path = find_route.getPathFromCross(current_loc, destination_key)
    elif current_loc.startswith('Z'):
        fast_path = find_route.getfastPath(current_loc, destination_key)
        complete_path = find_route.getPath(current_loc, destination_key)
    else:
        print("Unknown current location type:", current_loc)
        return None, None
    return fast_path, complete_path






task_id, task_type, source_name, target_name = extract_task_info(task)
zones = find_route.getAll()

source_key, source_zone = find_zone(source_name, zones)
target_key, target_zone = find_zone(target_name, zones)




zone_info = {
    "source": {"key": source_key, "name": source_zone},
    "target": {"key": target_key, "name": target_zone}
}



# Define the current location.
# For example, it could be a zone "Z1" or an intersection "I5".
current_location = 'Z1'  # Example current location


print("Source zone association:", zone_info["source"])
print("Target zone association:", zone_info["target"])




# Determine the destination based on whether the current location is already the source zone.
if current_location != zone_info["source"]["key"]:
    # Current location is not the source yet; need to go to the source.
    destination_key = zone_info["source"]["key"]
    print(f"Current location ({current_location}) is not the source zone. Routing to source zone: {destination_key}")
else:
    # Already at the source zone, so update destination to the target zone.
    destination_key = zone_info["target"]["key"]
    print(f"Current location ({current_location}) matches the source zone. Routing to target zone: {destination_key}")



# Calculate the route from current_location to the chosen destination.
fast_path, complete_path = calculate_route(current_location, destination_key)

if fast_path and complete_path:
    print("Traseu rapid:", " -> ".join(fast_path))
    print("Traseu complet:", " -> ".join(complete_path))
else:
    print("Could not determine the route.")

# Optionally, once the source is reached, update the current_location to the destination.
# This ensures future route calculations will use the new current_location.
current_location = destination_key
print("Updated current location:", current_location)






