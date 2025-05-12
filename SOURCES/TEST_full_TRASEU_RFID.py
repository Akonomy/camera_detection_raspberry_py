import time
from UTILS.send_code_to_stm32 import send_encoded_directions
from USART_COM.serial_module import process_command
from TAG_RFID.mfrc_reader import read_mifare_data



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
directions = [3,4,3,3,4,1,4,2,5]

directions= [2,4,1,4,2,1,5]

directions= [3,4,3,1,4,1,1,5]

directions= [1,1,4,2,4,1,4,3,1,5]
# Optional mode (default is -1 to skip mode command)
result = send_encoded_directions(directions, mode=1)

counter = 0
previous = None

while counter < 8:
    date = read_mifare_data()

    if date and date[1] and date != previous:
        print(date)
        previous = date
        counter += 1


data =  read_response(300);

print(data);

# Output the result like a proud parent
if result['success']:
    print("✅ Success:", result['message'])
else:
    print("❌ Failure:", result['message'])









