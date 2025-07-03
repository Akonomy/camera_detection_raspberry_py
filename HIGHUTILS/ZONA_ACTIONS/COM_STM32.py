
import os
import sys
import time



# Path adjustments
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..','..'))
if project_root not in sys.path:
    sys.path.append(project_root)


from SOURCES.USART_COM.serial_module import process_command,receive_octet_confirm


from SOURCES.UTILS.send_code_to_stm32 import send_encoded_directions





def read_response(timeout_sec=60):


    """
    Așteaptă până la timeout_sec secunde pentru a primi un răspuns 200 de la STM32.
    Returnează 1 dacă este primit 200.
    Returnează -1 dacă timpul expiră fără confirmare.
    """
    start = time.time()
    while time.time() - start < timeout_sec:
        data = receive_octet_confirm(expected=48)
        if data == 1:
            print("✅ Confirmare 48  primită de la STM32.")
            return 1

    print("⛔ Nicio confirmare primită în timp util.")
    return -1



# Sample directions (MAX 14)



def send_path(directions):

    result = send_encoded_directions(directions, mode=1)

    return result









# Read response from STM32 with timeout
def read_response2(timeout_sec=10):
    start = time.time()
    while time.time() - start < timeout_sec:
        data = process_command(3, 0, 0, [0])
        if data:
            print("STM32 response:", data)
            return data
        time.sleep(0.5)
    print("No response in time.")
    return None

# Log in HEX format
def log_code_as_hex(code):
    print(f"STM32 HEX code: {code:#04x}")






def read2(timeout_sec=20):

    data = read_response2(timeout_sec)
    print(data)

    # Check STM32 response and update DB accordingly
    if data and isinstance(data, list) and len(data) > 0:
        code = data[0]
        log_code_as_hex(code)
        if code == 0x30:
            return 1
