import sys
import os
import time
import re

# Add the "FINAL" directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from SOURCES.WEB.robot_api_client import RobotAPIClient
from SOURCES.TRASEU import find_route


from find_cross import request_cross
# --- Helper Functions ---

def extract_task_info(task):
    # Extract fields from the task dictionary
    task_data = task.get('task', {})
    task_id = task_data.get('id')
    task_type = task_data.get('task_type')
    source_section = task_data.get('source_section', {})
    target_section = task_data.get('target_section', {})

    # Extract type and number from the 'name' field using regex pattern (e.g., "Depozit_4")
    source_type = source_section.get('type', '')
    target_type = target_section.get('type', '')
    source_name = source_section.get('name', '')
    target_name = target_section.get('name', '')

    nr_source = re.search(r'_(\d+)', source_name)
    nr_target = re.search(r'_(\d+)', target_name)

    if nr_source and nr_target:
        nr_source = int(nr_source.group(1))
        nr_target = int(nr_target.group(1))

    source_name = (source_type + str(nr_source)).upper()
    target_name = (target_type + str(nr_target)).upper()

    return task_id, task_type, source_name, target_name


def find_zone(zone_name, zones):
    # Search for a zone where the name contains the zone_name substring
    for key, name in zones.items():
        if zone_name in name:
            return key, name
    return None, None


def calculate_route(current_loc, destination_key):
    if current_loc.startswith('I'):
        fast_path = find_route.getfastPathFromCross(current_loc, destination_key)
        complete_path = find_route.getPathFromCross(current_loc, destination_key)
    elif current_loc.startswith('Z'):
        fast_path = find_route.getfastPath(current_loc, destination_key)
        complete_path = find_route.getPath(current_loc, destination_key)
    else:
        return None, None
    return fast_path, complete_path


# --- PathManager Class ---

class PathManager:
    def __init__(self):
        # Each task is stored as:
        # task_id: {
        #    'source': {'key': <zone key>, 'name': <full zone name>},
        #    'target': {'key': <zone key>, 'name': <full zone name>},
        #    'visited_source': bool
        # }
        self.tasks = {}

    def add_task(self, task_id, source_key, source_zone, target_key, target_zone):
        """
        Add a new task with its source and target keys and full zone names.
        Initially, the source is not yet visited.
        """
        self.tasks[task_id] = {
            'source': {'key': source_key, 'name': source_zone},
            'target': {'key': target_key, 'name': target_zone},
            'visited_source': False,
        }
        print(f"Added task {task_id}: source={source_key} ({source_zone}), target={target_key} ({target_zone})")

    def get_task_info(self, task_id):
        """
        Return task info (source, target, visited flag) for a given task ID.
        """
        return self.tasks.get(task_id)

    def set_source_visited(self, task_id):
        """
        Manually mark the source as visited for the task.
        """
        if task_id in self.tasks:
            self.tasks[task_id]['visited_source'] = True

    def remove_task(self, task_id):
        """
        Remove a task from the manager.
        """
        if task_id in self.tasks:
            del self.tasks[task_id]
            print(f"Task {task_id} removed.")

    def update_task(self, task_id, source_key=None, target_key=None):
        """
        Update the source or target keys for a task.
        If the source key is changed, reset the visited flag.
        """
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")
        if source_key is not None:
            self.tasks[task_id]['source']['key'] = source_key
            self.tasks[task_id]['visited_source'] = False
        if target_key is not None:
            self.tasks[task_id]['target']['key'] = target_key

    def update_location(self, task_id, current_location):
        """
        With the provided task ID and current location, this method:
          - Normalizes the current location if it matches a full zone name.
          - Checks if the current destination is the source (if not yet visited) or the target.
          - If current_location matches the current destination (either key or full name):
              * If it was the source, marks it as visited and updates the destination to the target.
              * If it was the target, removes the task (completing it) and returns a completion message.
          - Otherwise, calculates the route (both fast and complete) from the normalized current_location to the destination.
        
        Returns a dict containing:
          - 'current_location': the normalized current location (zone key)
          - 'destination': the current target (source or target key)
          - 'fast_path': the fast route as computed by calculate_route()
          - 'complete_path': the complete route as computed by calculate_route()
          - 'message': any additional message
        """
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")

        task = self.tasks[task_id]
        message = ""
        source_info = task['source']
        target_info = task['target']

        # Normalize current location: if it matches a full zone name, use the zone key.
        normalized_current = current_location
        if current_location == source_info['name']:
            normalized_current = source_info['key']
        elif current_location == target_info['name']:
            normalized_current = target_info['key']

        # Determine current destination:
        if not task['visited_source']:
            destination = source_info['key']
            if normalized_current == source_info['key']:
                task['visited_source'] = True
                message = f"Arrived at source {source_info['name']}. Now heading to target {target_info['name']}."
                destination = target_info['key']
        else:
            destination = target_info['key']
            if normalized_current == target_info['key']:
                self.remove_task(task_id)
                return {
                    'message': f"Task {task_id} completed at target {target_info['name']}.",
                    'current_location': normalized_current,
                    'destination': None,
                    'fast_path': None,
                    'complete_path': None
                }

        fast_path, complete_path = calculate_route(normalized_current, destination)
        return {
            'message': message,
            'current_location': normalized_current,
            'destination': destination,
            'fast_path': fast_path,
            'complete_path': complete_path
        }
    
    def get_next_step(self, task_id, current_location):
        """
        Calculates the route from the current location to the destination and returns only the next node (step)
        and the corresponding instruction from the complete path.
        This method iterates over the fast path and returns the first node that, when normalized,
        is different from the current normalized location.
        """
        result = self.update_location(task_id, current_location)
        # If no valid fast path exists or the task is complete, return None.
        if not result['fast_path'] or len(result['fast_path']) == 0:
            return None, None, result

        normalized_current = result['current_location']
        task = self.tasks.get(task_id, None)
        if task is None:
            return None, None, result

        # Helper function to normalize a node using task info.
        def normalize_node(node):
            if node == task['source']['name']:
                return task['source']['key']
            elif node == task['target']['name']:
                return task['target']['key']
            else:
                return node

        next_index = None
        for i, node in enumerate(result['fast_path']):
            if normalize_node(node) != normalized_current:
                next_index = i
                break
        if next_index is None:
            return None, None, result
        next_node = result['fast_path'][next_index]
        instruction = result['complete_path'][next_index] if len(result['complete_path']) > next_index else ""
        return next_node, instruction, result


# --- Main Execution Block (Simulation) ---

if __name__ == '__main__':
    # Initialize API client and fetch task
    client = RobotAPIClient()
    task = client.fetch_first_task()

    # Load route data
    find_route.load_data()

    # Extract task information from API
    task_id, task_type, source_name, target_name = extract_task_info(task)
    zones = find_route.getAll()
    source_key, source_zone = find_zone(source_name, zones)
    target_key, target_zone = find_zone(target_name, zones)

    # Debug: print retrieved task/zone info from API
    print("API Task Info:")
    print(f"Task ID: {task_id}")
    print(f"Source: {source_key} - {source_zone}")
    print(f"Target: {target_key} - {target_zone}")

    # Create a PathManager instance and add the API task.
    path_manager = PathManager()
    path_manager.add_task(task_id, source_key, source_zone, target_key, target_zone)

    # --- Simulation of Step-by-Step Movement ---
    # Start with the initial current location.
    current_location = "I1"  # For example, the car starts at an intersection "I1"
    print(f"\nStarting simulation from: {current_location}\n")

    while task_id in path_manager.tasks:
        next_node, instruction, full_result = path_manager.get_next_step(task_id, current_location)
        # If the update indicates the task is completed, break out.
        if full_result['destination'] is None:
            print(full_result.get('message', "Task completed."))
            break

        if not next_node:
            print("No valid next step returned. Exiting simulation.")
            break

        # Parse the instruction for direction cues.
        direction_msg = ""
        if "[LEFT]" in instruction:
            direction_msg = "Turn left"
        elif "[RIGHT]" in instruction:
            direction_msg = "Turn right"
        elif "[FORWARD]" in instruction:
            direction_msg = "Keep lane"
        else:
            direction_msg = "Proceed"

        # Print the next step information.
        print(f"Departing from {current_location}.")
        print(f"Next step: {next_node}.")
        print(f"Instruction: {instruction} ({direction_msg}).")

        # Update the current location to the next step.
        current_location = next_node
        time.sleep(1)  # Simulate delay between moves

    print("\nSimulation finished.")
