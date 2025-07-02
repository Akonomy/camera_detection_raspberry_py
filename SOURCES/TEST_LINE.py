import time
from CAMERA.camera_session import init_camera, stop_camera, capture_raw_image
from LINE_PROCESS.get_line import (
    extract_dual_data,
    confirm_analyzed_points,
    get_direction_from_confirmed_results,
    new_classify_direction,
)

from USART_COM.serial_module import process_command



def main_loop(num_slices=8, image_width=512):
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
                process_command(CMD[0],CMD[1],CMD[2],CMD[3])

            print(f"| New Direction: {CMD}")
            time.sleep(0.7)  # ~30 fps
    except KeyboardInterrupt:
        print("Stopped by user.")
    finally:
        stop_camera()

if __name__ == "__main__":
    main_loop()



