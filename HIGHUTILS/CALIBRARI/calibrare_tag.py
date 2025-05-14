import os
import sys
import time

# Add project root to path (2 folders up)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from DATABASE import db
from SOURCES.UTILS.send_code_to_stm32 import send_encoded_directions
from SOURCES.USART_COM.serial_module import process_command
from SOURCES.TAG_RFID.mfrc_reader import read_mifare_data

# Read response from STM32 with timeout
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

# Log in HEX format
def log_code_as_hex(code):
    print(f"STM32 HEX code: {code:#04x}")

# Send directions
print("Sending directions...")
directions = [1,1,1,4, 1,1,1,5]
result = send_encoded_directions(directions, mode=1)

# Read tag once
counter = 0
previous = None

while counter < 1:
    date = read_mifare_data()
    if date and date[1] and date != previous:
        print(date)
        previous = date
        counter += 1

# Read response from STM32
data = read_response(120)
print(data)

# Check STM32 response and update DB accordingly
if data and isinstance(data, list) and len(data) > 0:
    code = data[0]
    log_code_as_hex(code)
    if code == 0xFA:
        db.SET("tag", date[1])
        db.SET("calibrated", time.time())
        db.SET("tag_ready", True)
        print("✅ Calibration success: tag + flags set.")
    else:
        db.SET("danger", hex(code))
        print("⚠️ Calibration failed: danger set to", hex(code))
else:
    print("❌ No valid response received.")

# Output the result like a proud parent
if result['success']:
    print("✅ Success:", result['message'])
else:
    print("❌ Failure:", result['message'])
