from CAMERA.camera_session import init_camera, stop_camera, capture_raw_image
import cv2

def stream_camera():
    try:
        init_camera()
        print("Streaming camera... Press 'q' to quit.")
        
        while True:
            frame = capture_raw_image()  # Grab a raw frame
            cv2.imshow("Camera Stream", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cv2.destroyAllWindows()
    except Exception as e:
        print("Something broke. Probably your code:", e)
    finally:
        stop_camera()

if __name__ == "__main__":
    stream_camera()
