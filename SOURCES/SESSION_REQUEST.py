import cv2
import numpy as np
from CAMERA.camera_session import init_camera, stop_camera, capture_and_process_session
from UTILS.BOX_ALIGNMENT_FINE import evaluate_box_alignment,find_closest_box , evaluate_target_box

# Hartă de culori pentru desen
color_map = {
    "A": (0, 255, 0),
    "K": (255, 0, 255),
    "O": (255, 255, 255),
    "Green": (0, 255, 0),
    "Red": (255, 0, 0),
    "Sample": (255, 255, 255),
    "Blue": (0, 0, 255)
}

zone_top_left = (223, 346)
zone_bottom_right = (307, 474)



TARGET_LETTER = "A"
TARGET_COLOR = "Green"
REFERENCE_POINT = (261, 433)




def draw_rotated_boxes(image, session_data, color_map=None):
    """
    Desenează pătrate rotite pentru fiecare pachet în funcție de unghiul dat.
    Include: bounding box rotit, etichetă cu ID și litera.

    Args:
        image: imaginea pe care se desenează
        session_data: dict cu informațiile despre cutii
        color_map: dict opțional cu mapare de culori
    Returns:
        imaginea adnotată
    """
    if color_map is None:
        color_map = {
            "A": (0, 255, 0),
            "K": (255, 0, 255),
            "O": (255, 255, 255),
            "Green": (0, 255, 0),
            "Red": (0, 0, 255),
            "Sample": (255, 255, 255),
            "Blue": (255, 0, 0)
        }

    for pkg_id, pkg in session_data.items():
        try:
            pos = pkg.get("position", (0, 0))
            size = pkg.get("size", (30, 30))
            angle = pkg.get("angle", 0)
            letters = pkg.get("letters", [])
            label_letter = letters[0] if letters else "?"
            color_key = pkg.get("box_color", "Sample")
            color = color_map.get(color_key, (150, 150, 150))

            x, y = pos
            w, h = size

            # Definire rotire
            rect = ((x, y), (w, h), -angle)  # OpenCV face rotirea în sens orar
            box = cv2.boxPoints(rect)
            box = np.int0(box)

            # Desenare pătrat rotit
            cv2.drawContours(image, [box], 0, color, 2)

            # Etichetă
            text = f"{pkg_id} ({label_letter})"
            cv2.putText(image, text, (box[0][0], box[0][1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        except Exception as e:
            print(f"Eroare la desenare pentru {pkg_id}: {e}")
            continue

    return image




if __name__ == "__main__":
    try:
        init_camera()
        print("Camera a fost inițializată. Apasă 'q' în fereastra imaginii pentru a opri.")

        while True:
            image, session = capture_and_process_session()

            if session:
                print("=========SESIUNE==========")
                print(session)
                print("========END SESIUNE ========")

                label, status, overlaps = evaluate_target_box(session, "Green", "A")
                if label:
                    print(f"[{label}] => Status: {status} | Depășiri [Top, Right, Bottom, Left]: {overlaps}")
                else:
                    print("Nicio cutie validă găsită în sesiune.")



            #image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            #cv2.imshow("Raw Image", image)

            annotated = draw_rotated_boxes(image.copy(), session, color_map=color_map)
            annotated = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
            cv2.imshow("Annotated", annotated)


            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cv2.destroyAllWindows()

    except Exception as e:
        print("A apărut o eroare:", e)
    finally:
        stop_camera()
