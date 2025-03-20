if __name__ == "__main__":
    # Pentru testare, putem importa funcția de captură din modulul de cameră
    from CAMERA.camera_session import capture_raw_image
    from ZONE_DETECT.get_zone import  detect_zone
    
    # Capturează o imagine (512x512)
    image_copy = capture_raw_image()
    # Exemplu: verificăm dacă pozițiile date sunt în zonă
    test_positions = [(-20, 5), (0, 0), (10, 20)]
    limits, flags = detect_zone(image_copy, positions=test_positions, debug=False)
    print("Limitele zonei:", limits)
    print("Rezultatul verificării pozițiilor:", flags)
