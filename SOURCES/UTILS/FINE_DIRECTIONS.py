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


if __name__ == "__main__":
    test_input = [30, 10, 28, 8]  # top, right, bottom, left
    print("Test input:", test_input)

    cmds = getPrioritizedSmoothCommands(test_input)

    print("Comenzi generate:")
    for cmd in cmds:
        print(f"  -> {cmd}")
