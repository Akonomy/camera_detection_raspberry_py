#!/usr/bin/env python3
"""
main.py

This script imports the usart module (which should be saved as usart.py) and
performs a series of tests:
  - Initializes the serial communication with the STM and toggles control
    by sending the 200 200 command.
  - Sends direction commands (RIGHT, BACK, FRONT, LEFT) using the 'direction' mode.
  - Sends an initial movement command at speed 3.
  - Iterates over all defined movement commands in the move_car mode at speed 7,
    waiting 3 seconds between each move.
  
Each command prints to the terminal what movement is executed and what is sent to the STM.
"""

import time
# Import your usart module (adjust the import according to your project structure)
# For example, if your usart.py is in a folder named USART_COM, use:
# from USART_COM import usart
# Otherwise, if they are in the same directory, simply:
from USART_COM import usart

def initialize_control():
    """
    Sends the toggle_control command to request control of the car.
    The command sends (200, 200) and waits for a confirmation response
    from the STM (for example, "413\n"). The response is printed.
    """
    print("[INIT] Toggling control...")
    response = usart.write_usart('toggle_control', [])
    if response is None:
        print("[INIT] No response received. Check connection and try again.")
    else:
        print(f"[INIT] Received response: {response}")
    # Optionally, wait a moment after toggling control before proceeding
    time.sleep(1)

def test_direction_commands():
    """
    Test the basic direction commands using the 'direction' mode.
    The commands include: RIGHT, BACK, FRONT, LEFT.
    """
    directions = ['RIGHT', 'BACK', 'FRONT', 'LEFT']
    for d in directions:
        print(f"[DIRECTION] Sending command: {d}")
        usart.write_usart('direction', [d])
        time.sleep(3)  # Wait 3 seconds between commands

def test_all_movements():
    """
    Iterate through all the available movement commands defined in the move_car mode
    using a fixed speed value (7 in this case). Wait 3 seconds between each move.
    """
    movements = [
        "STOP", "FORWARD", "RIGHT", "LEFT", "SLIGHTLY RIGHT", "SLIGHTLY LEFT",
        "DIAGONAL RIGHT", "DIAGONAL LEFT", "HARD TURN LEFT", "HARD TURN RIGHT",
        "LEFT ROTATE", "RIGHT ROTATE", "BACKWARD"
    ]
    speed = 7
    for move in movements:
        print(f"[MOVE_CAR - ALL MOVEMENTS] Sending command: Speed={speed}, Direction={move}")
        usart.write_usart('move_car', [speed, move])
        time.sleep(3)

def main():
    print("Initializing USART communication with STM...")
    # (If any additional initialization is required, add it here.)
    time.sleep(2)  # Wait a moment for the connection to settle

    # Step 1: Toggle control (send 200 200) and wait for confirmation.
    initialize_control()

    print("\n--- Testing Basic Direction Commands ---")
    test_direction_commands()

    print("\n--- Testing Initial Movement at Speed 3 ---")
    # Send one initial movement command at speed 3 (e.g., FORWARD)
    usart.write_usart('move_car', [3, 'FORWARD'])
    time.sleep(3)

    print("\n--- Testing All Defined move_car Movements at Speed 7 ---")
    test_all_movements()

    print("\nAll tests completed.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Test interrupted by user.")
    finally:
        # It is good practice to clean up the GPIO resources when finished.
        import RPi.GPIO as GPIO
        GPIO.cleanup()
