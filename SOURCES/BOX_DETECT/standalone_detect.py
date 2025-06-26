import cv2
import numpy as np
import random
import tflite_runtime.interpreter as tflite
from picamera2 import Picamera2

confidence = 0.5

class_info = {
    0: {"label": "Green", "color": (0, 255, 0)},
    1: {"label": "Red", "color": (0, 0, 255)},
    2: {"label": "Sample", "color": (255, 255, 255)},
    3: {"label": "Blue", "color": (255, 0, 0)},
}

interpreter = tflite.Interpreter(model_path="model8.tflite")
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

def detect_objects_raw_debug(picam2, show=True, glitch_simulation=False):
    image = picam2.capture_array()
    image = cv2.resize(image, (512, 512))
    input_image = image / 255.0
    input_image = np.expand_dims(input_image, axis=0).astype(np.float32)

    interpreter.set_tensor(input_details[0]['index'], input_image)
    interpreter.invoke()

    output_data = interpreter.get_tensor(output_details[0]['index'])
    output = np.reshape(output_data, (1, 8, 5376))

    xc, yc, w, h = output[0, 0, :], output[0, 1, :], output[0, 2, :], output[0, 3, :]
    c1, c2, c3, c4 = output[0, 4, :], output[0, 5, :], output[0, 6, :], output[0, 7, :]

    detections = []
    for i in range(5376):
        confs = [c1[i], c2[i], c3[i], c4[i]]
        if max(confs) > confidence:
            x, y, width, height = int(xc[i]*512), int(yc[i]*512), int(w[i]*512), int(h[i]*512)
            class_id = np.argmax(confs)

            if glitch_simulation:
                offset = i % 5
                if offset == 1:
                    x += 1
                elif offset == 2:
                    x -= 1
                elif offset == 3:
                    y += 1
                elif offset == 4:
                    y -= 1

            detections.append({
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "class_id": class_id,
                "confidence": max(confs),
                "label": class_info[class_id]["label"]
            })

            if show:
                color = class_info[class_id]["color"]
                top_left = (x - width // 2, y - height // 2)
                bottom_right = (x + width // 2, y + height // 2)
                cv2.rectangle(image, top_left, bottom_right, color, 1)
                label_text = f'{class_info[class_id]["label"]} {max(confs):.2f}'
                cv2.putText(image, label_text, (top_left[0], top_left[1] - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

    if show:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        cv2.imshow("Raw Model Output (with simulated variation)", image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    return detections

if __name__ == "__main__":
    picam2 = Picamera2()
    picam2.configure(picam2.create_still_configuration())
    picam2.start()

    print("Rulăm detecția brută cu simulare de variații...")
    raw_detections = detect_objects_raw_debug(picam2, show=True, glitch_simulation=True)
    print(f"Total detecții brute: {len(raw_detections)}")
    for det in raw_detections:
        print(det)

    picam2.stop()
