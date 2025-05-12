#!/usr/bin/env python3
import serial
import time

def main():
    # Configure your serial port (update the port and baud rate as needed)
    port = '/dev/ttyS0'  # e.g., '/dev/ttyUSB0' or '/dev/serial0'
    baud_rate = 38400
    ser = serial.Serial(port, baud_rate, timeout=0.5)
    print("Serial port opened:", ser.name)
    
    
  
    # For demonstration, we assume the STM32 alternates:
    # first sending an 8-byte array, then a single byte.
    expected_message_length = 8

    while True:
        # Read the expected number of bytes from the serial port
        data = ser.read(expected_message_length)
        if len(data) == expected_message_length:
            # Convert the incoming bytes to a list of integers (0-255)
            sensor_message = list(data)
            print("Received:", sensor_message)
            # Alternate: if we just read 8 bytes, next expect 1; if 1, then expect 8.
            expected_message_length = 1 if expected_message_length == 8 else 8
        else:
            # Incomplete data may be received due to timing; try again.
            time.sleep(0.1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Test interrupted by user.")
