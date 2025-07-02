

import os
import sys
import time



# Path adjustments
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..','..'))
if project_root not in sys.path:
    sys.path.append(project_root)


from SOURCES.CAMERA.camera_session import init_camera, stop_camera, capture_raw_image
from SOURCES.LINE_PROCESS.get_line import (
    extract_dual_data,
    confirm_analyzed_points,
    get_direction_from_confirmed_results,
    new_classify_direction,
)

from SOURCES.USART_COM.serial_module import process_command,receive_octet

sensor_names_ordered = [
    (4, "far_left"),
    (0, "left"),
    (1, "mid"),
    (3, "right"),
    (6, "far_right")
]



def find_line(num_slices=8,image_width=512):
    process_command(5, 11, 1, [0])



    init_camera()
    try:
        while True:
            frame = capture_raw_image()
            if frame is None:
                continue

            data = extract_dual_data(frame.copy(), num_slices=num_slices)
            confirmed = confirm_analyzed_points(data)
            CMD = new_classify_direction(confirmed)

            if CMD:
                pass
                #process_command(CMD[0],CMD[1],CMD[2],CMD[3])
            #     #print(CMD)



            time.sleep(1)  # ~30 fps
            data=receive_octet()



            # Normalize input
            if isinstance(data, int):
                byte = data
            elif isinstance(data, list) and data and isinstance(data[0], int):
                byte = data[0]
            else:
                print("Unusable data received. Possibly haunted.")
                byte = None

            # Decode sensor bits if byte is valid
            if byte is not None:
                line_display = ""
                label_display = ""
                for index, name in sensor_names_ordered:
                    state = (byte >> index) & 1
                    line_display += f"<{state}>------"
                    #label_display += f"{name:^7}"  # centered label

                print(label_display)
                print(line_display.rstrip('-'))  # strip trailing dashes for cleanliness


    except KeyboardInterrupt:
        print("Stopped by user.")
    finally:
        stop_camera()


if __name__ == "__main__":

    #process_command(5, 1, 1, [0])

    #time.sleep(10)
    find_line()

