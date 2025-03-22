from picamera2 import Picamera2
import tflite_runtime.interpreter as tflite
import numpy as np
import cv2

# Load the TFLite model
interpreter = tflite.Interpreter(model_path="model8.tflite")
interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

confidence = 0.5

class_info = {
    0: {"label": "Green", "color": (0, 255, 0)},
    1: {"label": "Red", "color": (0, 0, 255)},
    2: {"label": "Sample", "color": (255, 255, 255)},
    3: {"label": "Blue", "color": (255, 0, 0)},
}

from .utils import filter_close_points  # Import new filtering function
#hug (: 
def detect_objects(picam2):
    """
    Captures an image from the camera, runs inference, and returns detected objects.

    Args:
        picam2: An instance of Picamera2.

    Returns:
        List of dictionaries with detected objects.
    """

    image = picam2.capture_array()
    image = cv2.resize(image, (512, 512))
    #image = cv2.rotate(image, cv2.ROTATE_180)

    input_image = image / 255.0
    input_image = np.expand_dims(input_image, axis=0).astype(np.float32)

    interpreter.set_tensor(input_details[0]['index'], input_image)
    interpreter.invoke()

    output_data = interpreter.get_tensor(output_details[0]['index'])
    output = np.reshape(output_data, (1, 8, 5376))

    xc, yc, w, h = output[0, 0, :], output[0, 1, :], output[0, 2, :], output[0, 3, :]
    c1, c2, c3, c4 = output[0, 4, :], output[0, 5, :], output[0, 6, :], output[0, 7, :]

    detected_objects = []
    for i in range(5376):
        if max(c1[i], c2[i], c3[i], c4[i]) > confidence:
            x, y, width, height = int(xc[i] * 512), int(yc[i] * 512), int(w[i] * 512), int(h[i] * 512)
            max_class = np.argmax([c1[i], c2[i], c3[i], c4[i]])
            detected_objects.append((x, y, width, height, max_class))

    # Apply filtering
    filtered_points = filter_close_points(detected_objects)

    # Convert to dictionary format
    results = [
        {"label": class_info[p[4]]["label"], "x": p[0], "y": p[1], "width": p[2], "height": p[3]}
        for p in filtered_points
    ]

    return results
