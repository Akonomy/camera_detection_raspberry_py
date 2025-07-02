
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
        data = receive_octet_confirm(expected=200)
        if data == 1:
            print("✅ Confirmare 200 primită de la STM32.")
            return 1

    print("⛔ Nicio confirmare primită în timp util.")
    return -1



# Sample directions (MAX 14)



def send_path(directions):

    result = send_encoded_directions(directions, mode=1)

    time.sleep(1)
    data =  read_response(30);

    if (data==1): #200 de succes code pt parcare
        process_command(5, 0, 1, [0])  #se trimite modul 0
        return 1
    return(data);

