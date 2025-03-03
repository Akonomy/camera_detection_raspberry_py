#!/usr/bin/env python3
"""
usart.py

This module implements multiple ways to communicate with an STM32 over UART.
It supports several communication modes:
  - direction: send a directional command (e.g., FRONT, RIGHT, etc.)
  - toggle_control: send a toggle command (200 200) and wait for a confirmation response
  - move_car: send movement commands with a speed and a direction
  - move_servo: send servo commands with a servo identifier and angle
  - read_sensors: request sensor data from the STM32
  - debug: a placeholder for debugging

It also contains helper functions to send/receive data over UART and (optionally)
to run a background thread that continuously reads incoming data.
"""

import serial
import time
import threading
import RPi.GPIO as GPIO

# ===========================
# Configuration and Globals
# ===========================

SERIAL_PORT = "/dev/ttyS0"  # Replace with the correct port (e.g., /dev/ttyUSB0 or /dev/serial0)
BAUD_RATE = 38400           # Must match the baud rate of the STM32
MAX_BYTES = 16              # Maximum bytes to read at a time

# Initialize the serial connection
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)

# Setup GPIO (if needed)
GPIO.setmode(GPIO.BCM)  # Use BCM numbering

# ===========================
# Core Communication Functions
# ===========================

def send_two_values(value1, value2):
    """
    Send two integer values separated by a space over UART.
    """
    data_to_send = f"{value1} {value2}\n"
    ser.write(data_to_send.encode('utf-8'))
    print(f"[SEND] {data_to_send.strip()}")

def read_uart(timeout=3, max_attempts=50):
    """
    Attempt to read data from the serial port with a timeout and maximum attempts.
    
    Args:
        timeout (int): Maximum time (in seconds) to attempt a read.
        max_attempts (int): Maximum number of read attempts.
        
    Returns:
        str or None: The received data (stripped) if available, otherwise None.
    """
    start_time = time.time()
    attempts = 0
    while attempts < max_attempts:
        if ser.in_waiting > 0:
            data = ser.read(MAX_BYTES).decode('utf-8', errors='ignore').strip()
            if data:
                return data
        attempts += 1
        if time.time() - start_time > timeout:
            break
        time.sleep(0.05)
    return None

def read_usart_via_gpio(gpio_pin=17, data_sample="101"):
    """
    Check the given GPIO pin state. If HIGH, attempt to read data from UART.
    Compare the received data with data_sample.
    
    Returns:
        bool: True if the received data matches data_sample, False otherwise.
    """
    GPIO.setup(gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    if GPIO.input(gpio_pin) == GPIO.HIGH:
        data = read_uart(timeout=3, max_attempts=50)
        if data is not None:
            return data == data_sample
        return False
    else:
        return False

def start_serial_read(callback, poll_interval=0.1):
    """
    Start a background thread that continuously reads from the serial port
    and calls the provided callback with each non-empty data received.
    
    Args:
        callback (function): A function that takes one parameter (the data string).
        poll_interval (float): Delay between read attempts.
    
    Returns:
        Thread: The background thread (daemon).
    """
    def read_loop():
        print("[THREAD] Serial read thread started.")
        while True:
            if ser.in_waiting > 0:
                data = ser.read(MAX_BYTES).decode('utf-8', errors='ignore').strip()
                if data:
                    callback(data)
            time.sleep(poll_interval)
    t = threading.Thread(target=read_loop, daemon=True)
    t.start()
    return t

# ===========================
# Multi-Mode Write Function
# ===========================

def write_usart(mode='direction', params=[]):
    """
    Write data to UART based on a specified mode and parameters.
    
    Modes and their expected parameters:
      - 'direction': 
           params: [direction_string] 
           (direction_string from {FRONT, RIGHT, LEFT, BACK, STOP})
           Sends (195, mapped_value).
      
      - 'toggle_control': 
           Sends (200, 200) and waits for a confirmation response.
      
      - 'move_car': 
           params: [speed_value, direction_string]
           speed_value: Integer (1 to 7)
           direction_string: One of {"STOP", "FORWARD", "RIGHT", "LEFT", 
                                        "SLIGHTLY RIGHT", "SLIGHTLY LEFT",
                                        "DIAGONAL RIGHT", "DIAGONAL LEFT",
                                        "HARD TURN LEFT", "HARD TURN RIGHT",
                                        "LEFT ROTATE", "RIGHT ROTATE", "BACKWARD"}
      
      - 'move_servo': 
           params: [servo_name, angle]
           servo_name: One of {"SERVO1", "SERVO2", "SERVO3", ...}
           angle: Integer between 0 and 180.
      
      - 'read_sensors': 
           Sends (190, 0) and returns the sensor data received.
      
      - 'debug':
           Prints the debug parameters.
    
    Returns:
        The response from UART for modes that read data (e.g. 'toggle_control', 'read_sensors'),
        or None.
    """
    if mode == 'direction':
        if len(params) != 1:
            print("[ERROR] 'direction' mode requires a single parameter.")
            return
        direction = params[0].upper()
        direction_map = {
            'FRONT': 1,
            'RIGHT': 2,
            'LEFT': 3,
            'BACK': 4,
            'STOP': 0
        }
        if direction in direction_map:
            send_two_values(195, direction_map[direction])
            print(f"[CMD] Direction command: {direction} -> (195, {direction_map[direction]})")
        else:
            print("[ERROR] Invalid direction parameter. Use FRONT, RIGHT, LEFT, BACK, STOP.")
    
    elif mode == 'toggle_control':
        send_two_values(200, 200)
        print("[CMD] Toggle control command sent: (200, 200)")
        # Wait for a confirmation response (if any)
        data = read_uart(timeout=3, max_attempts=50)
        if data:
            print(f"[RECV] Toggle control response: {data}")
        else:
            print("[RECV] No response received for toggle control.")
        return data
        
    elif mode == 'move_car':
        if len(params) != 2:
            print("[ERROR] 'move_car' mode requires two parameters [speed_value, direction].")
            return
        speed_value = params[0]
        direction = params[1].upper()
        if not isinstance(speed_value, int) or not (1 <= speed_value <= 7):
            print("[ERROR] Speed value must be an integer between 1 and 7.")
            return
        direction_map = {
            "STOP": 0,
            "FORWARD": 1,
            "RIGHT": 2,
            "LEFT": 3,
            "SLIGHTLY RIGHT": 4,
            "SLIGHTLY LEFT": 5,
            "DIAGONAL RIGHT": 6,
            "DIAGONAL LEFT": 7,
            "HARD TURN LEFT": 8,
            "HARD TURN RIGHT": 9,
            "LEFT ROTATE": 10,
            "RIGHT ROTATE": 11,
            "BACKWARD": 12,
        }
        direction_value = direction_map.get(direction, "UNKNOWN")
        if direction_value == "UNKNOWN":
            print(f"[ERROR] Invalid direction '{direction}'.")
            return
        send_two_values(speed_value, direction_value)
        print(f"[CMD] move_car command: Speed={speed_value}, Direction={direction} -> ({speed_value}, {direction_value})")
    
    elif mode == 'move_servo':
        if len(params) != 2:
            print("[ERROR] 'move_servo' mode requires two parameters [servo_name, angle].")
            return
        servo_name = params[0].upper()
        angle = params[1]
        servo_map = {
            "SERVO1": 180,
            "SERVO2": 181,
            "SERVO3": 182,
            "SERVO4": 183,
            "SERVO5": 184,
            "SERVO6": 185,
        }
        if servo_name not in servo_map:
            print(f"[ERROR] Invalid servo name '{servo_name}'. Use one of {list(servo_map.keys())}.")
            return
        if not isinstance(angle, int) or not (0 <= angle <= 180):
            print("[ERROR] Angle must be an integer between 0 and 180.")
            return
        value1 = servo_map[servo_name]
        send_two_values(value1, angle)
        print(f"[CMD] move_servo command: Servo={servo_name} -> ({value1}, {angle})")
    
    elif mode == 'read_sensors':
        send_two_values(190, 0)
        print("[CMD] Sensor read command sent: (190, 0)")
        data = read_uart(timeout=3, max_attempts=50)
        if data:
            print(f"[RECV] Sensor data: {data}")
        else:
            print("[RECV] No sensor data received.")
        return data
    
    elif mode == 'debug':
        print("[DEBUG] Mode: debug, params:", params)
    
    else:
        print(f"[ERROR] Unknown mode: {mode}. Please define a valid mode.")

# ===========================
# Test/Standalone Section
# ===========================

if __name__ == "__main__":
    # Example test routine when this module is run directly.
    print("==== Testing Toggle Control ====")
    response = write_usart('toggle_control', [])
    print(f"Toggle control response: {response}")
    time.sleep(1)
    
    print("==== Testing Direction Command (FRONT) ====")
    write_usart('direction', ['FRONT'])
    time.sleep(1)
    
    print("==== Testing Move Car (speed=3, LEFT) ====")
    write_usart('move_car', [3, 'LEFT'])
    time.sleep(1)
    
    print("==== Testing Move Servo (SERVO1, angle=90) ====")
    write_usart('move_servo', ['SERVO1', 90])
    time.sleep(1)
    
    print("==== Testing Read Sensors ====")
    sensor_data = write_usart('read_sensors', [])
    print(f"Sensor data: {sensor_data}")
    
    # Optionally, start a background thread to print all incoming serial data.
    def print_incoming(data):
        print(f"[THREAD RECV] {data}")
    
    print("==== Starting background serial read thread ====")
    start_serial_read(print_incoming)
    
    # Keep the main thread alive to allow background thread to run.
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting module test.")
        ser.close()
        GPIO.cleanup()
