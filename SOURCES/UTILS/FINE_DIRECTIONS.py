
RIGHT_CMDS=[

(2,[0, 0, 95, 95],9.0),
#(2,[127, 115, 115, 127],15.0),
(2,[127, 115, 115, 127],25.0),
(2,[121, 110, 110, 121],15.0),
(2,[138, 125, 125, 138],36.0),
(2,[138, 125, 125, 138],40.0),
(2,[157, 143, 144, 157],43.0),
(2,[185, 178, 165, 185],80.0),
(2,[190, 184, 170, 190],80.0),
(2,[196, 189, 175, 196],80.0),

]


LEFT_CMDS =[


(2,[0, 0, 112, 110],25.0),
#(2,[0, 0, 95, 95],25.0),
(2,[196, 189, 175, 196],61.0),
#(2,[179, 173, 160, 179],50.0),
(2,[168, 162, 150, 168],50.0),
(2,[151, 146, 135, 151],40.0),
(2,[140, 135, 125, 140],21.0),

]


FORWARD_CMDS=[

(1,[95, 95, 95, 95],14.0),
(1,[100, 100, 100, 100],37.0),

]

BACK_CMDS =[

(1,[99, 90, 90, 99],10.0),
(1,[109, 90, 90, 109],15.0),
(1,[95, 95, 95, 95],12.0),

]

def getPrioritizedSmoothCommands(overlap_vector):
    """
    Primește un vector [top, right, bottom, left] și returnează o listă de maxim 4 comenzi
    în ordinea de prioritate: bottom > right > left > top.
    Se aplică:
      - 0: ignoră (nu generează comandă)
      - 1-25: LOW command
      - 26+: HIGH command
    """

    threshold_low = 1
    threshold_high = 26

    # Comenzi predefinite: (tick, speed_vector)
    command_bank = {
        "BOTTOM": {
            "LOW":  (2, [100]),   # forward
            "HIGH": (2, [100])
        },
        "TOP": {
            "LOW":  (2, [100]),   # backward
            "HIGH": (4, [100])
        },
        "RIGHT": {
            "LOW":  (2, [191, 180, 187, 176]),  # mișcare stânga
            "HIGH": (4, [191, 180, 187, 176])
        },
        "LEFT": {
            "LOW":  (2, [167, 169, 185, 194]),  # mișcare dreapta
            "HIGH": (4, [167, 169, 185, 194])
        }
    }

    # Mapare direcție → index în vectorul primit și → direcție numerică
    priority_order = [
        ("BOTTOM", 2, 2),  # bottom ➜ forward ➜ direction 1
        ("RIGHT", 1, 10),   # right ➜ move left ➜ direction 9
        ("LEFT", 3, 9),   # left ➜ move right ➜ direction 10
        ("TOP", 0, 1),     # top ➜ backward ➜ direction 2
    ]

    commands = []

    for name, idx, direction in priority_order:
        value = overlap_vector[idx]
        if value < threshold_low:
            continue  # ignoră
        level = "HIGH" if value >= threshold_high else "LOW"
        tick, speed = command_bank[name][level]
        commands.append((1, tick, direction, speed))

    return commands




def getFINEcmd(test_input):
    priorities = ['bottom', 'right', 'left', 'top']
    index_map = {'top': 0, 'right': 1, 'bottom': 2, 'left': 3}
    direction_codes = {'bottom': 2, 'right': 10, 'left': 9, 'top': 1}
    command_sets = {
        'top': FORWARD_CMDS,
        'right': RIGHT_CMDS,
        'bottom': BACK_CMDS,
        'left': LEFT_CMDS,
    }

    result = []

    for direction in priorities:
        idx = index_map[direction]
        value = test_input[idx]
        max_value = value + 3  # Error margin

        candidates = list(command_sets[direction])
        best = None
        best_diff = float('inf')

        for cmd in candidates:
            cmd_value = cmd[2]
            if cmd_value <= max_value:
                diff = abs(value - cmd_value)
                if diff < best_diff:
                    best = cmd
                    best_diff = diff

        if best:
            ticks = best[0]
            speeds = best[1]
            direction_code = direction_codes[direction]
            result.append((1, ticks, direction_code, speeds))

    return result






if __name__ == "__main__":
    test_input = [30, 10, 28, 8]  # top, right, bottom, left
    print("Test input:", test_input)

    cmds = getPrioritizedSmoothCommands(test_input)

    print("Comenzi generate:")
    for cmd in cmds:
        print(f"  -> {cmd}")


    cmds = getFINEcmd(test_input)

    print("Comenzi generate:")
    for cmd in cmds:
        print(f"  -> {cmd}")

