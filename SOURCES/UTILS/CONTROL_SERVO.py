#CONTROL_SERVO.py



import time
import os
import sys


# Add parent directory to sys.path (you're welcome, future self)
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)



#from SOURCES.USART_COM.serial_module import process_command

from USART_COM.serial_module import process_command


def read_response(timeout_sec=10):
    start = time.time()
    while time.time() - start < timeout_sec:
        data = process_command(3, 0, 0, [0])
        if data:
            print("STM32 response:", data)
            data_str = str(data)
            if '0' in data_str:
                return 0
            elif '1' in data_str:
                return 1
            return data
        time.sleep(0.5)
    print("No response in time.")
    return None


def executa_comanda(idA, state=0):
    if idA in (9, 10):  # Servo 9 or 10
        process_command(2, idA, state, [0])

        return read_response()

    elif idA == 3:  # Ajustare automata
        process_command(2, 10, 2, [0])
        return read_response()

    elif idA == 4:  # Ajustare bla bla (Calibrare LOW BUDGET)
        process_command(2, 10, 0, [0])
        time.sleep(2)
        process_command(2, 10, 4, [0])
        time.sleep(2)
        process_command(2, 10, 0, [0])
        response = read_response()
        time.sleep(2)
        return response

    elif idA == 5:  # Ajustare cutie
        process_command(8, 8, 0, [0])
        time.sleep(1)
        return 1
    else:
        print("Comanda necunoscută.")
        return None


