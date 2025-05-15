import cv2
from CAMERA.camera_session import init_camera, stop_camera, capture_and_process_session
from UTILS.BOX_ALIGNMENT_FINE import evaluate_box_alignment

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

                for pkg_id, pkg in session.items():
                    if pkg.get("box_color") == "Green" and "K" in pkg.get("letters", []):
                        pos = pkg.get("position")
                        size = pkg.get("size")
                        color = color_map.get("Green", (100, 100, 100))

                        if pos and size and None not in size:
                            x, y = pos
                            w, h = size
                            top_left = (int(x - w / 2), int(y - h / 2))
                            bottom_right = (int(x + w / 2), int(y + h / 2))

                            # Desenează cutia
                            cv2.rectangle(image, top_left, bottom_right, color, 2)
                            label = f"GreenK"
                            cv2.putText(image, label, (top_left[0], top_left[1] - 5),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

                            # Verifică alinierea cu noul modul
                            status, over = evaluate_box_alignment(
                                pkg,
                                zone_top_left=zone_top_left,
                                zone_bottom_right=zone_bottom_right,
                                thresholds=(30, 6, 6, 6)
                            )

                            print(f"[GreenK] => Status: {status} | Depășiri [Top, Right, Bottom, Left]: {over}")

            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            cv2.imshow("Raw Image", image)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cv2.destroyAllWindows()

    except Exception as e:
        print("A apărut o eroare:", e)
    finally:
        stop_camera()
