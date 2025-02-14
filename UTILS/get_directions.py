# Y calibration: (pixel_y, distance_cm) from y=87 => 0 cm, up to y=342 => 13 cm
y_calibration = [
    (100.0,  0.00),
    (129.0, 2.00),
    (152.0, 3.00),
    (164.0, 3.50),
    (177.0, 4.00),
    (187.0, 4.50),
    (197.0, 5.00),
    (208.0, 5.50),
    (238.0, 7.00),
    (248.0, 7.50),
    (257.0, 8.00),
    (276.0, 9.00),
    (285.0, 9.50),
    (295.0, 10.00),
    (315.0, 11.00),
    (342.0, 13.00)
]

# X calibration to the RIGHT: (pixel_x, distance_cm) from x=233 => 0 cm
x_calibration_right = [
    (233.0, 0.00),
    (228.0, 0.50),
    (221.0, 1.00),
    (206.0, 1.50),
    (199.0, 2.00),
    (194.0, 2.50),
    (181.0, 3.00),
    (168.0, 3.50),
    (165.0, 4.00),
    (150.0, 4.50),
    (142.0, 5.00),
    (130.0, 5.50),
    (128.0, 6.00),
    (107.0, 7.00),
    (89.0,  8.00),
    (72.0,  9.00),
    (49.0,  10.00),
    (40.0,  11.00),
    (30.0,  12.00)
]

# X calibration to the LEFT: (pixel_x, distance_cm) from x=233 => 0 cm
x_calibration_left = [
    (233.0, 0.00),
    (242.0, 0.50),
    (255.0, 1.00),
    (263.0, 1.50),
    (273.0, 2.00),
    (284.0, 2.50),
    (296.0, 3.00),
    (308.0, 3.50),
    (319.0, 4.00),
    (323.0, 4.50),
    (332.0, 5.00),
    (342.0, 5.50),
    (352.0, 6.00),
    (363.0, 7.00),
    (370.0, 8.00),
    (390.0, 9.00),
    (410.0, 10.00),
    (450.0, 11.00),
    (470.0, 12.00)
]


def interpolate_distance(calib_list, pixel_value):
    """
    Dând o listă sortată de tuple (pixel, distance_cm) și o valoare pixel,
    returnează distanța aproximativă în cm prin interpolare liniară.
    """
    if pixel_value <= calib_list[0][0]:
        (x0, d0), (x1, d1) = calib_list[0], calib_list[1]
        slope = (d1 - d0) / (x1 - x0)
        return d0 + slope * (pixel_value - x0)
    if pixel_value >= calib_list[-1][0]:
        (xA, dA), (xB, dB) = calib_list[-2], calib_list[-1]
        slope = (dB - dA) / (xB - xA)
        return dA + slope * (pixel_value - xA)
    
    for i in range(len(calib_list) - 1):
        x0, d0 = calib_list[i]
        x1, d1 = calib_list[i+1]
        if x0 <= pixel_value <= x1:
            slope = (d1 - d0) / (x1 - x0)
            return d0 + slope * (pixel_value - x0)
    
    return calib_list[-1][1]


def get_distance_y(image_y):
    """
    Convertește poziția y din imagine în distanță (cm) pe axa Y.
    """
    dist_from_87 = interpolate_distance(y_calibration, image_y)
    sign = 1.0 if image_y >= 87 else -1.0
    return sign * abs(dist_from_87)


def get_distance_x(image_x):
    """
    Convertește poziția x din imagine în distanță (cm) pe axa X.
    Distanța este negativă pentru deplasare spre dreapta și pozitivă pentru stânga.
    """
    if image_x == 233:
        return 0.0
    if image_x < 233:
        dist = interpolate_distance(x_calibration_right, image_x)
        return -dist
    else:
        dist = interpolate_distance(x_calibration_left, image_x)
        return dist


# Datele pentru comenzile de mișcare înainte/înapoi
forward_table_data = {
    (1, 110): 3.50, (1, 120): 3.30, (1, 130): 3.00, (1, 140): 2.00, (1, 150): 1.80,
    (2, 110): 5.50, (2, 120): 5.00, (2, 130): 4.50, (2, 140): 4.00, (2, 150): 3.50,
    (3, 110):10.00, (3, 120): 9.00, (3, 130): 8.00, (3, 140): 7.50, (3, 150): 7.00,
    (4, 110):13.00, (4, 120):11.00, (4, 130):11.50, (4, 140):10.00, (4, 150): 9.50,
}
forward_speed_priority = [110, 120, 130, 140, 150]

# Datele pentru comenzile laterale
lateral_table_data = {
    (1, 70): 1.00,  (1, 110): 1.00,  (1, 150): 0.50,
    (2, 70): 2.00,  (2, 110): 2.00,
    (3, 70): 4.00,  (3, 110): 3.00,
    (4, 70): 6.00,  (4, 110): 5.50,
    (5, 70): 9.00,  (5, 110): 7.00,
    (6, 70):11.00,  (6, 110): 9.00,
    (7, 70):14.00,  (7, 110):11.00,
    (8, 70):16.00,  (8, 110):12.00,
    (9, 70):18.00,  (9, 110):13.00,
    (10,70):20.00
}
lateral_speed_priority = [70, 110, 150]  # 150 se folosește doar pentru ajustări mici


def pick_one_forward_command(distance_needed):
    """
    Pentru o deplasare înainte/înapoi necesară (distance_needed > 0),
    returnează tuple-ul (ticks, speed, distance_achieved) potrivit.
    """
    for sp in forward_speed_priority:
        for t in [1, 2, 3, 4]:
            dist = forward_table_data[(t, sp)]
            if dist >= distance_needed and dist <= distance_needed + 3:
                return (t, sp, dist)
    
    best_t = 1
    best_sp = forward_speed_priority[0]
    best_dist = 0.0
    for sp in forward_speed_priority:
        for t in [4, 3, 2, 1]:
            dist = forward_table_data[(t, sp)]
            if dist > best_dist:
                best_dist = dist
                best_t = t
                best_sp = sp
        if best_dist > 0:
            break
    return (best_t, best_sp, best_dist)


def pick_one_lateral_command(distance_needed):
    """
    Pentru o deplasare laterală necesară (distance_needed > 0),
    returnează tuple-ul (ticks, speed, distance_achieved) potrivit.
    """
    for sp in lateral_speed_priority:
        possible_ticks = [t for (t, s) in lateral_table_data.keys() if s == sp]
        possible_ticks.sort()
        for t in possible_ticks:
            dist = lateral_table_data[(t, sp)]
            if dist >= distance_needed and dist <= distance_needed + 3:
                return (t, sp, dist)
    
    best_t = None
    best_sp = None
    best_dist = 0.0
    for sp in lateral_speed_priority:
        possible_ticks = [tt for (tt, ss) in lateral_table_data.keys() if ss == sp]
        for t in possible_ticks:
            dist = lateral_table_data[(t, sp)]
            if dist > best_dist:
                best_dist = dist
                best_t = t
                best_sp = sp
        if best_t is not None:
            break
    return (best_t, best_sp, best_dist)


def move_forward_back_commands(dist_y_target, commands_list, max_iter=10):
    """
    Generează comenzi de deplasare înainte/înapoi până când |dist_y_target| 
    se încadrează în intervalul [5, 10] (sau până se ajunge la max_iter iterații).
    """
    for _ in range(max_iter):
        ay = abs(dist_y_target)
        if 5 <= ay <= 10:
            break
        move_needed = ay - 10 if ay > 10 else 5 - ay
        move_needed = max(move_needed, 1e-3)
        t, sp, dist_achieved = pick_one_forward_command(move_needed)
        direction = 1 if dist_y_target > 0 else 2  # 1: forward, 2: backward
        commands_list.append((1, direction, t, sp))
        if direction == 1:
            dist_y_target -= dist_achieved
        else:
            dist_y_target += dist_achieved
    return dist_y_target


def move_lateral_until_x_below(dist_x_target, threshold, commands_list, max_iter=10):
    """
    Generează comenzi laterale până când |dist_x_target| < threshold
    (sau până se ajunge la max_iter iterații).

    Atenție: Direcțiile pentru mișcare laterală au fost modificate:
      - Dacă dist_x_target > 0 (se dorește deplasare spre stânga), se folosește 9.
      - Dacă dist_x_target < 0 (spre dreapta), se folosește 10.
    """
    for _ in range(max_iter):
        ax = abs(dist_x_target)
        if ax < threshold:
            break
        move_needed = ax - threshold
        move_needed = max(move_needed, 1e-3)
        t, sp, dist_achieved = pick_one_lateral_command(move_needed)
        # Schimbare de direcție: dacă dist_x_target > 0 (stânga), direcția 9; dacă < 0 (dreapta), 10.
        direction = 9 if dist_x_target > 0 else 10
        commands_list.append((1, direction, t, sp))
        if direction == 9:
            dist_x_target -= dist_achieved
        else:
            dist_x_target += dist_achieved
    return dist_x_target


def move_forward_back_until_y_below(dist_y_target, threshold, commands_list, max_iter=10):
    """
    Generează comenzi de deplasare înainte/înapoi până când |dist_y_target| < threshold
    (sau până se ajunge la max_iter iterații).
    """
    for _ in range(max_iter):
        ay = abs(dist_y_target)
        if ay < threshold:
            break
        move_needed = ay - threshold
        move_needed = max(move_needed, 1e-3)
        t, sp, dist_achieved = pick_one_forward_command(move_needed)
        direction = 1 if dist_y_target > 0 else 2
        commands_list.append((1, direction, t, sp))
        if direction == 1:
            dist_y_target -= dist_achieved
        else:
            dist_y_target += dist_achieved
    return dist_y_target


def get_all_move_commands_for_position(x_image, y_image):
    """
    Pentru coordonatele (x_image, y_image) din imagine, calculează
    secvența de comenzi necesare pentru a ajunge în zona de toleranță.
    Returnează o listă de tuple: (cmd_type, direction, ticks, speed).
    """
    dist_x = get_distance_x(x_image)  # negativ => dreapta, pozitiv => stânga
    dist_y = get_distance_y(y_image)    # pozitiv => forward (y>=87), negativ => backward
    commands = []
    
    # Pasul 1: Ajustare înainte/înapoi pentru a ajunge în intervalul [5,10] cm
    ay = abs(dist_y)
    if not (5 <= ay <= 10):
        dist_y = move_forward_back_commands(dist_y, commands)
    
    # Pasul 2: Ajustare laterală până când |dist_x| < 3 cm
    dist_x = move_lateral_until_x_below(dist_x, 3.0, commands)
    
    # Pasul 3: Ajustare înainte/înapoi până când |dist_y| < 2 cm
    dist_y = move_forward_back_until_y_below(dist_y, 2.0, commands)
    
    # Pasul 4: Ajustare laterală până când |dist_x| < 1 cm
    dist_x = move_lateral_until_x_below(dist_x, 1.0, commands)
    
    # Pasul 5: Ajustare înainte/înapoi până când |dist_y| < 1 cm
    dist_y = move_forward_back_until_y_below(dist_y, 1.0, commands)
    
    return commands


def get_next_move_command_for_position(x_image, y_image):
    """
    Calculează toate comenzile de mișcare pentru poziția dată și returnează
    doar prima comandă (dacă există). Aceasta poate fi executată, apoi se
    actualizează imaginea/poziția și se solicită o nouă comandă.
    """
    commands = get_all_move_commands_for_position(x_image, y_image)
    return commands[0] if commands else None
