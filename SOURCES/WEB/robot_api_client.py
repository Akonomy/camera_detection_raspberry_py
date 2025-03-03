#!/usr/bin/env python3
import requests
import logging
import time

# Configurare logging (poți personaliza nivelul și formatul după preferințe)
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Configurații fixe
SERVER_IP = 'depozitautomat.shop'
BASE_URL = f'https://{SERVER_IP}/robot/api'
USERNAME = 'raspberrypi'
PASSWORD = 'robot'

class RobotAPIClient:
    """
    Client API pentru comunicarea cu serverul robot.
    Folosește endpoint-urile definite și gestionează autentificarea JWT.
    """

    def __init__(self, username=USERNAME, password=PASSWORD, base_url=BASE_URL):
        self.username = username
        self.password = password
        self.base_url = base_url
        self.jwt_token = None
        self.headers = {}
        self.authenticate()

    def authenticate(self):
        """Obține token-ul JWT și configurează header-ele de autorizare."""
        url = f'{self.base_url}/token/'
        data = {'username': self.username, 'password': self.password}
        try:
            response = requests.post(url, data=data)
            response.raise_for_status()
            tokens = response.json()
            self.jwt_token = tokens.get('access')
            if self.jwt_token:
                self.headers = {'Authorization': f'Bearer {self.jwt_token}'}
                logging.info('Successfully obtained JWT token')
            else:
                logging.error('Failed to obtain JWT token')
        except requests.RequestException as e:
            logging.error(f'Error obtaining JWT token: {e}')

    def fetch_tasks(self):
        """Returnează lista de task-uri obținută de la server."""
        url = f'{self.base_url}/tasks/'
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            tasks = data.get('tasks', [])
            logging.info(f'Fetched {len(tasks)} tasks')
            return tasks
        except requests.RequestException as e:
            logging.error(f'Error in fetch_tasks: {e}')
            return None
            
            
            
    def fetch_first_task(self):
        """Returnează lista de task-uri obținută de la server."""
        url = f'{self.base_url}/task/first/'
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            tasks = data
            logging.info(f'Fetched {len(tasks)} tasks')
            return tasks
        except requests.RequestException as e:
            logging.error(f'Error in fetch_tasks: {e}')
            return None

    def update_task_status(self, task_id, status, reason=''):
        """
        Actualizează statusul unui task.
        
        :param task_id: ID-ul task-ului de actualizat.
        :param status: Noua stare (ex: 'accepted', 'completed').
        :param reason: Opțional, motivul schimbării stării.
        :return: Răspunsul JSON de la server.
        """
        url = f'{self.base_url}/tasks/{task_id}/update/'
        data = {'status': status, 'reason': reason}
        try:
            response = requests.post(url, data=data, headers=self.headers)
            response.raise_for_status()
            result = response.json()
            logging.info(f'Updated task {task_id} status to "{status}"')
            return result
        except requests.RequestException as e:
            logging.error(f'Error in update_task_status: {e}')
            return None

    def update_robot_status(self, status, message=''):
        """
        Actualizează statusul robotului.
        
        :param status: Noua stare a robotului (ex: 'busy', 'idle').
        :param message: Mesaj adițional.
        :return: Răspunsul JSON de la server.
        """
        url = f'{self.base_url}/robot_status/update/'
        data = {'status': status, 'message': message}
        try:
            response = requests.post(url, data=data, headers=self.headers)
            response.raise_for_status()
            result = response.json()
            logging.info(f'Robot status updated to "{status}"')
            return result
        except requests.RequestException as e:
            logging.error(f'Error in update_robot_status: {e}')
            return None

    def get_box_details(self, box_code):
        """
        Obține detaliile unui box.
        
        :param box_code: Codul box-ului.
        :return: Răspunsul JSON de la server cu detaliile box-ului.
        """
        url = f'{self.base_url}/boxes/{box_code}/'
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            result = response.json()
            logging.info(f'Fetched box details for {box_code}')
            return result
        except requests.RequestException as e:
            logging.error(f'Error in get_box_details: {e}')
            return None

    def check_container(self, container_code):
        """
        Verifică detaliile unui container.
        
        :param container_code: Codul containerului.
        :return: Răspunsul JSON de la server cu detaliile containerului.
        """
        url = f'{self.base_url}/container/{container_code}/check/'
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            result = response.json()
            logging.info(f'Fetched container details for {container_code}')
            return result
        except requests.RequestException as e:
            logging.error(f'Error in check_container: {e}')
            return None

    def reset_container(self, container_code):
        """
        Resetează un container.
        
        :param container_code: Codul containerului.
        :return: Răspunsul JSON de la server după resetare.
        """
        url = f'{self.base_url}/container/{container_code}/reset/'
        try:
            response = requests.post(url, headers=self.headers)
            response.raise_for_status()
            result = response.json()
            logging.info(f'Container {container_code} has been reset')
            return result
        except requests.RequestException as e:
            logging.error(f'Error in reset_container: {e}')
            return None

    def change_container_zone(self, container_code, new_zone_code):
        """
        Schimbă zona unui container.
        
        :param container_code: Codul containerului.
        :param new_zone_code: Codul noii zone.
        :return: Răspunsul JSON de la server după schimbare.
        """
        url = f'{self.base_url}/container/{container_code}/change-zone/'
        data = {'zone_code': new_zone_code}
        try:
            response = requests.post(url, data=data, headers=self.headers)
            response.raise_for_status()
            result = response.json()
            logging.info(f'Container {container_code} zone changed to {new_zone_code}')
            return result
        except requests.RequestException as e:
            logging.error(f'Error in change_container_zone: {e}')
            return None

# Funcții expuse (dacă dorești să folosești funcții independente, fără clasa)
def get_jwt_token_module():
    """Funcție pentru obținerea token-ului JWT (returnează token și header-ele corespunzătoare)."""
    url = f'{BASE_URL}/token/'
    data = {'username': USERNAME, 'password': PASSWORD}
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        tokens = response.json()
        access_token = tokens.get('access')
        if access_token:
            headers = {'Authorization': f'Bearer {access_token}'}
            logging.info('Successfully obtained JWT token (module)')
            return access_token, headers
        else:
            logging.error('Failed to obtain JWT token (module)')
            return None, None
    except requests.RequestException as e:
        logging.error(f'Error obtaining JWT token (module): {e}')
        return None, None

def fetch_tasks_module(headers):
    url = f'{BASE_URL}/tasks/'
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        logging.info('Fetched tasks (module)')
        return response.json()
    except requests.RequestException as e:
        logging.error(f'Error in fetch_tasks_module: {e}')
        return None
        
        
def fetch_first_tasks_module(headers):
    url = f'{BASE_URL}/task/first'
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        logging.info('Fetched tasks (module)')
        return response.json()
    except requests.RequestException as e:
        logging.error(f'Error in fetch_tasks_module: {e}')
        return None

def update_task_status_module(task_id, status, reason='', headers=None):
    url = f'{BASE_URL}/tasks/{task_id}/update/'
    data = {'status': status, 'reason': reason}
    try:
        response = requests.post(url, data=data, headers=headers)
        response.raise_for_status()
        logging.info(f'Updated task {task_id} status to {status} (module)')
        return response.json()
    except requests.RequestException as e:
        logging.error(f'Error in update_task_status_module: {e}')
        return None

def update_robot_status_module(status, message='', headers=None):
    url = f'{BASE_URL}/robot_status/update/'
    data = {'status': status, 'message': message}
    try:
        response = requests.post(url, data=data, headers=headers)
        response.raise_for_status()
        logging.info(f'Updated robot status to {status} (module)')
        return response.json()
    except requests.RequestException as e:
        logging.error(f'Error in update_robot_status_module: {e}')
        return None

def get_box_details_module(box_code, headers):
    url = f'{BASE_URL}/boxes/{box_code}/'
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        logging.info(f'Fetched box details for {box_code} (module)')
        return response.json()
    except requests.RequestException as e:
        logging.error(f'Error in get_box_details_module: {e}')
        return None

def check_container_module(container_code, headers):
    url = f'{BASE_URL}/container/{container_code}/check/'
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        logging.info(f'Fetched container details for {container_code} (module)')
        return response.json()
    except requests.RequestException as e:
        logging.error(f'Error in check_container_module: {e}')
        return None

def reset_container_module(container_code, headers):
    url = f'{BASE_URL}/container/{container_code}/reset/'
    try:
        response = requests.post(url, headers=headers)
        response.raise_for_status()
        logging.info(f'Container {container_code} reset (module)')
        return response.json()
    except requests.RequestException as e:
        logging.error(f'Error in reset_container_module: {e}')
        return None

def change_container_zone_module(container_code, new_zone_code, headers):
    url = f'{BASE_URL}/container/{container_code}/change-zone/'
    data = {'zone_code': new_zone_code}
    try:
        response = requests.post(url, data=data, headers=headers)
        response.raise_for_status()
        logging.info(f'Changed container {container_code} zone to {new_zone_code} (module)')
        return response.json()
    except requests.RequestException as e:
        logging.error(f'Error in change_container_zone_module: {e}')
        return None

# Exemplu de utilizare a modulului (acest bloc va fi executat doar dacă rulăm direct acest fișier)
if __name__ == '__main__':
    client = RobotAPIClient()
    # Testăm câteva endpoint-uri folosind instanța clasei
    print("Tasks:", client.fetch_tasks())
    print("Box details:", client.get_box_details('SGsYp36'))
    print("Container check:", client.check_container('SGsYp36'))
    print("Container reset:", client.reset_container('SGsYp36'))
    print("Container zone change:", client.change_container_zone('SGsYp36', 'syn8c3B'))
