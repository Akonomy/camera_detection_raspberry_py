import time
from UTILS.send_code_to_stm32 import send_encoded_directions
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



# Sample directions (MAX 14)




directions= [1,3]
# Optional mode (default is -1 to skip mode command)
result = send_encoded_directions(directions, mode=1)





data =  read_response(300);

print(data);

# Output the result like a proud parent
if result['success']:
    print("✅ Success:", result['message'])
else:
    print("❌ Failure:", result['message'])









