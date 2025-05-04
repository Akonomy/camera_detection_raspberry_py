from .ENCODER import encode_message
from USART_COM.serial_module import process_command
import os
import sys
import time

# Add parent directory to sys.path (you're welcome, future self)
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)


def send_encoded_directions(directions, mode=-1):
    """
    Sends a list of up to 14 direction values via USART.

    Args:
        directions (list[int]): A list of up to 10 integers (0-7) representing directions.
        mode (int): Optional mode value to send after the directions. Default is -1 (inactive).

    Returns:
        dict: A dictionary with 'success' (bool) and 'message' (str) keys.
    """
    try:
        if not isinstance(directions, list) or len(directions) > 10:
            return {'success': False, 'message': "Directions must be a list with a maximum of 10 values."}

        for d in directions:
            if not isinstance(d, int) or not (0 <= d <= 7):
                return {'success': False, 'message': f"Invalid direction value: {d}. Must be an integer between 0 and 7."}

        cmd_type, val1, val2, data_bytes = encode_message(directions)
        process_command(cmd_type, val1, val2, data_bytes)

        if mode >= 0:
            time.sleep(1)
            process_command(5, mode, 1, [0])

        return {'success': True, 'message': "Commands sent successfully."}

    except Exception as e:
        return {'success': False, 'message': f"An error occurred: {str(e)}"}
