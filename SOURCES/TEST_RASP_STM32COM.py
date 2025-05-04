import time
from USART_COM.serial_module import process_command



def read_response(timeout_sec=10):
    start = time.time()
    while time.time() - start < timeout_sec:
        data = process_command(3, 0, 0, [0])
        if data:
            print("STM32 response:", data)
            return data
        time.sleep(0.5)
    print("No response in time.")
    return None


process_command(3,1,1,[0])


data =	read_response(3);

print(data);