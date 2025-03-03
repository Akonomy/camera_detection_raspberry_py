#!/usr/bin/env python3
import requests
import logging
import time

# Configure logging to display test results
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Configuration
SERVER_IP = 'depozitautomat.shop'
BASE_URL = f'https://{SERVER_IP}/robot/api'

# Sample codes for testing (înlocuiește cu coduri valide dacă este cazul)
SAMPLE_BOX_CODE = 'SGsYp36'
SAMPLE_CONTAINER_CODE = 'SGsYp36'  # Codul container pentru testele de container

def get_jwt_token(username, password):
    url = f'{BASE_URL}/token/'
    data = {
        'username': username,
        'password': password,
    }
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        tokens = response.json()
        access_token = tokens.get('access')
        refresh_token = tokens.get('refresh')
        if access_token:
            logging.info('Successfully obtained JWT token')
            return access_token, refresh_token
        else:
            logging.error('Failed to obtain JWT token')
            return None, None
    except requests.RequestException as e:
        logging.error(f'Error obtaining JWT token: {e}')
        return None, None

def test_fetch_tasks(headers):
    logging.info('Testing fetch_tasks...')
    url = f'{BASE_URL}/tasks/'
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        tasks = data.get('tasks', [])
        logging.info(f'Fetched {len(tasks)} tasks')
        if tasks:
            for task in tasks:
                logging.info(f'Task ID: {task.get("id")}')
                logging.info(f'  Task Type: {task.get("task_type")}')
                logging.info(f'  Box Code: {task.get("box_code")}')
                logging.info(f'  Custom Action: {task.get("custom_action")}')
                if task.get('source_section'):
                    source = task['source_section']
                    logging.info(f'  Source Section: {source.get("name")} ({source.get("type")})')
                else:
                    logging.info('  Source Section: None')
                if task.get('target_section'):
                    target = task['target_section']
                    logging.info(f'  Target Section: {target.get("name")} ({target.get("type")})')
                else:
                    logging.info('  Target Section: None')
                logging.info('')  # Blank line for readability
            logging.info('PASS: fetch_tasks')
        else:
            logging.warning('WARN: fetch_tasks returned no tasks')
        return tasks
    except requests.RequestException as e:
        logging.error(f'FAIL: fetch_tasks - {e}')
        return None

def test_update_task_status(task_id, status, reason='', headers=None):
    logging.info(f'Testing update_task_status for task {task_id} to "{status}"...')
    url = f'{BASE_URL}/tasks/{task_id}/update/'
    data = {
        'status': status,
        'reason': reason,
    }
    try:
        response = requests.post(url, data=data, headers=headers)
        response.raise_for_status()
        logging.info(f'PASS: Task {task_id} status updated to "{status}"')
    except requests.RequestException as e:
        logging.error(f'FAIL: update_task_status - {e}')

def test_update_robot_status(status, message='', headers=None):
    logging.info(f'Testing update_robot_status to "{status}"...')
    url = f'{BASE_URL}/robot_status/update/'
    data = {
        'status': status,
        'message': message,
    }
    try:
        response = requests.post(url, data=data, headers=headers)
        response.raise_for_status()
        logging.info(f'PASS: Robot status updated to "{status}"')
    except requests.RequestException as e:
        logging.error(f'FAIL: update_robot_status - {e}')

def test_get_box_details(box_code, headers):
    logging.info(f'Testing get_box_details for box "{box_code}"...')
    url = f'{BASE_URL}/boxes/{box_code}/'
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        box = data.get('box', {})
        if box:
            logging.info(f'PASS: Fetched box details: {box}')
        else:
            logging.warning('WARN: Box not found')
        return box
    except requests.RequestException as e:
        logging.error(f'FAIL: get_box_details - {e}')
        return None

# Funcții pentru testarea endpoint-urilor container

def test_check_container(headers, container_code):
    logging.info(f'Testing check_container for container "{container_code}"...')
    url = f'{BASE_URL}/container/{container_code}/check/'
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        container = data.get('container', {})
        if container:
            logging.info(f'PASS: Container details: {container}')
        else:
            logging.warning('WARN: Container not found')
        return container
    except requests.RequestException as e:
        logging.error(f'FAIL: check_container - {e}')
        return None

def test_reset_container(headers, container_code):
    logging.info(f'Testing reset_container for container "{container_code}"...')
    url = f'{BASE_URL}/container/{container_code}/reset/'
    try:
        response = requests.post(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        logging.info(f'PASS: reset_container response: {data}')
    except requests.RequestException as e:
        logging.error(f'FAIL: reset_container - {e}')

def test_change_container_zone(headers, container_code, new_zone_code):
    logging.info(f'Testing change_container_zone for container "{container_code}" to zone "{new_zone_code}"...')
    url = f'{BASE_URL}/container/{container_code}/change-zone/'
    data = {'zone_code': new_zone_code}  # Parametrul așteptat de API
    try:
        response = requests.post(url, data=data, headers=headers)
        response.raise_for_status()
        data = response.json()
        logging.info(f'PASS: change_container_zone response: {data}')
    except requests.RequestException as e:
        logging.error(f'FAIL: change_container_zone - {e}')

def main():
    logging.info('Starting API tests...\n')

    # Robot credentials (înlocuiește cu cele reale)
    username = 'raspberrypi'
    password = 'robot'

    # Obtain JWT token
    access_token, _ = get_jwt_token(username, password)
    if not access_token:
        logging.error('Cannot proceed without a valid JWT token')
        return

    headers = {
        'Authorization': f'Bearer {access_token}',
    }

    # Test container endpoints
    test_check_container(headers, SAMPLE_CONTAINER_CODE)
    test_reset_container(headers, SAMPLE_CONTAINER_CODE)
    # Specifică codul zonei dorite pentru test, de exemplu "ZONE123"
    test_change_container_zone(headers, SAMPLE_CONTAINER_CODE, new_zone_code='syn8c3B')

    # Test fetch_tasks
    tasks = test_fetch_tasks(headers)
    if tasks is not None:
        if tasks:
            task = tasks[0]
            task_id = task.get('id')
            # Test updating task status to 'accepted'
            test_update_task_status(task_id, 'accepted', headers=headers)

            # Test updating robot status to 'busy'
            test_update_robot_status('busy', 'Processing task', headers=headers)

            # Simulate task processing
            logging.info('Simulating task processing...')
            time.sleep(2)

            # Test updating task status to 'completed'
            test_update_task_status(task_id, 'completed', headers=headers)

            # Test updating robot status to 'idle'
            test_update_robot_status('idle', 'Task completed', headers=headers)
            logging.info('Task processing simulation completed.\n')
        else:
            logging.info('No tasks available to process.\n')
    else:
        logging.error('Failed to fetch tasks.\n')

    # Test get_box_details
    box = test_get_box_details(SAMPLE_BOX_CODE, headers)
    if box is not None:
        logging.info('Box details fetched successfully.\n')
    else:
        logging.error('Failed to get box details.\n')

    logging.info('API tests completed.')

if __name__ == '__main__':
    main()
