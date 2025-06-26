#!/usr/bin/env python3
import tkinter as tk
import tkinter.messagebox as messagebox

import sys

from USART_COM.serial_module import process_command


# Variabile globale
tick_var = None
speed_mode_var = None
general_speed_var = None  # Inputul central "Viteza Generală"

wheel_speed_vars = {}   # Dicționar pentru valorile de input pentru fiecare roată
wheel_mode_vars = {}    # Dicționar pentru modurile fiecărei roți (False = valoare absolută, True = procent)

# last_command_info va fi un tuple: (tick, speed_vector, direction, cmd_str)
last_command_info = None
# last_saved_command va reține stringul ultimei comenzi salvate (cmd_str)
last_saved_command = None

last_command_label = None  # Label ce afișează ultima comandă
save_indicator_canvas = None  # Indicatorul de salvare (cerc)

def update_indicator(color):
    """Actualizează culoarea indicatorului de salvare."""
    global save_indicator_canvas
    save_indicator_canvas.delete("all")
    save_indicator_canvas.create_oval(2, 2, 22, 22, fill=color, outline=color)


def on_mousewheel(event, var, delta):
    try:
        current = int(var.get())
    except ValueError:
        current = 0
    var.set(str(current + delta))
    return "break"

def bind_mousewheel(entry, var):
    if sys.platform.startswith('linux'):
        entry.bind("<Button-4>", lambda e: on_mousewheel(e, var, +1))
        entry.bind("<Button-5>", lambda e: on_mousewheel(e, var, -1))
    else:
        entry.bind("<MouseWheel>", lambda e: on_mousewheel(e, var, 1 if e.delta > 0 else -1))


def update_wheel_default(toggle_var, var):
    var.set("100" if toggle_var.get() else "160")


def create_wheel_frame(parent, wheel_name):
    frame = tk.Frame(parent, bg="white", bd=2, relief=tk.GROOVE)
    tk.Label(frame, text=wheel_name, bg="white", font=("Helvetica", 14)).pack()
    var = tk.StringVar(value="160")
    entry = tk.Entry(frame, textvariable=var, font=("Helvetica", 20), width=5, justify="center")
    entry.pack(padx=5, pady=5)
    bind_mousewheel(entry, var)
    toggle_var = tk.BooleanVar(value=False)
    tk.Checkbutton(frame, text="%", variable=toggle_var, bg="white", font=("Helvetica", 12),
                   command=lambda: update_wheel_default(toggle_var, var)).pack(padx=5, pady=5)
    return frame, var, toggle_var


def send_command(direction):
    """Trimite comanda către proces și actualizează starea internă."""
    global last_command_info, last_command_label
    tick = tick_var.get()
    mode = speed_mode_var.get()
    # Calculează vectorul de viteze
    if mode == "uniform":
        try:
            speed = int(general_speed_var.get())
        except ValueError:
            print("Eroare: Viteza generală trebuie să fie un număr întreg!")
            return
        speed_vector = [speed]
    else:
        try:
            gen_speed = int(general_speed_var.get())
        except ValueError:
            print("Eroare: Viteza generală trebuie să fie un număr întreg!")
            return
        speeds = []
        for wheel in ["Front Left", "Front Right", "Back Left", "Back Right"]:
            try:
                val = float(wheel_speed_vars[wheel].get())
            except ValueError:
                print(f"Eroare: Valoarea pentru {wheel} trebuie să fie un număr!")
                return
            if wheel_mode_vars[wheel].get():
                comp = int(round(gen_speed * (val / 100)))
            else:
                comp = int(round(val))
            speeds.append(max(0, min(255, comp)))
        speed_vector = speeds

    try:
        process_command(1, tick, direction, speed_vector)
        print(f"Comanda trimisă: 1 {tick} {direction} {speed_vector}")
    except Exception as e:
        print(f"Eroare la trimiterea comenzii: {e}")
        return

    # Pregătește textul pentru afișaj și pentru salvare
    cmd_str = f"1 {tick} {direction} {speed_vector}"
    last_command_info = (tick, speed_vector, direction, cmd_str)

    direction_names = {1: "Forward", 2: "Backward", 9: "Side Left", 10: "Side Right"}
    dir_text = direction_names.get(direction, str(direction))
    disp = speed_vector[0] if mode == "uniform" else speed_vector
    last_command_label.config(text=f"Ultima comandă: Direcție: {dir_text}, Speed: {disp}")
    update_indicator("red")  # ne-salvată deocamdată


def save_command():
    """Salvează în fișierul corespunzător tuple-ul (tick, speeds..., distance)."""
    global last_command_info, last_saved_command
    if last_command_info is None:
        print("Nu există nicio comandă de salvat!")
        update_indicator("red")
        return

    try:
        dist = float(distance_var.get())
    except ValueError:
        print("Distance must be a number!")
        update_indicator("red")
        return

    if dist == 0:
        if not messagebox.askyesno("Atenție", "Distanța este 0. Ești sigur că dorești să salvezi comanda cu distanță 0?"):
            print("Salvare anulată de utilizator.")
            update_indicator("red")
            return

    tick, speeds, direction, cmd_str = last_command_info
    # Formatează linia: dacă un singur element, fără listă
    if len(speeds) == 1:
        line = f"({tick},{speeds[0]},{dist}),\n"
    else:
        line = f"({tick},{speeds},{dist}),\n"

    # Alege fișierul pe baza direcției
    files = {
        1: "CAR_forward.txt",
        2: "CAR_back.txt",
        9: "CAR_left.txt",
        10: "CAR_right.txt",
    }
    target = files.get(direction)
    try:
        if target:
            with open(target, "a") as f:
                f.write(line)
        # Suprascrie întotdeauna ultimul
        with open("CAR_last.txt", "w") as f_last:
            f_last.write(line)

        print("Comanda a fost salvată cu succes.")
        last_saved_command = cmd_str
        update_indicator("green")
    except Exception as e:
        print(f"Eroare la salvarea comenzii: {e}")
        update_indicator("red")


def main():
    global tick_var, speed_mode_var, general_speed_var, last_command_label, save_indicator_canvas, distance_var
    global wheel_speed_vars, wheel_mode_vars

    root = tk.Tk()
    root.title("Control Mașină - Debug")
    root.configure(bg="lightgray")

    # Ticks
    tf = tk.LabelFrame(root, text="Ticks (1-10)", bg="lightblue")
    tf.pack(fill=tk.X, padx=10, pady=5)
    tick_var = tk.IntVar(value=5)
    for t in range(1, 11):
        tk.Radiobutton(tf, text=str(t), variable=tick_var, value=t, bg="lightblue").pack(side=tk.LEFT, padx=5, pady=5)

    # Speed Mode și DISTANCE
    mf = tk.LabelFrame(root, text="Speed Mode", bg="lightgreen", padx=20, pady=10)
    mf.pack(fill=tk.X, padx=10, pady=5)
    speed_mode_var = tk.StringVar(value="individual")
    tk.Radiobutton(mf, text="Uniform Speed", variable=speed_mode_var, value="uniform", bg="lightgreen").pack(side=tk.LEFT, padx=5)
    tk.Radiobutton(mf, text="Individual Speed", variable=speed_mode_var, value="individual", bg="lightgreen").pack(side=tk.LEFT, padx=5)

    tk.Label(mf, text="DISTANCE:", bg="lightgreen").pack(side=tk.LEFT, padx=5)
    distance_var = tk.StringVar(value="0")
    tk.Entry(mf, textvariable=distance_var, width=8).pack(side=tk.LEFT, padx=5)
    tk.Button(mf, text="Save", command=save_command).pack(side=tk.LEFT, padx=5)

    # Panoul central cu roți și butoane de direcție
    main_frame = tk.Frame(root, bg="white", bd=2, relief=tk.GROOVE)
    main_frame.pack(padx=10, pady=10)
    # Front Left, Forward, Front Right
    flf = create_wheel_frame(main_frame, "Front Left")
    frf = create_wheel_frame(main_frame, "Front Right")
    wheel_speed_vars.update({"Front Left": flf[1], "Front Right": frf[1]})
    wheel_mode_vars.update({"Front Left": flf[2], "Front Right": frf[2]})
    flf[0].grid(row=0, column=2)
    tk.Button(main_frame, text="Forward", width=12, height=3, command=lambda: send_command(1)).grid(row=0, column=1)
    frf[0].grid(row=0, column=0)
    # Side Left, General Speed, Side Right
    tk.Button(main_frame, text="Side Left", width=12, height=3, command=lambda: send_command(9)).grid(row=1, column=0)
    general_speed_var = tk.StringVar(value="130")
    cf = tk.Frame(main_frame, bg="white")
    tk.Label(cf, text="Viteza Generală", bg="white").pack()
    tk.Entry(cf, textvariable=general_speed_var, width=5).pack()
    cf.grid(row=1, column=1)
    tk.Button(main_frame, text="Side Right", width=12, height=3, command=lambda: send_command(10)).grid(row=1, column=2)
    # Back Left, Backward, Back Right
    blf = create_wheel_frame(main_frame, "Back Left")
    brf = create_wheel_frame(main_frame, "Back Right")
    wheel_speed_vars.update({"Back Left": blf[1], "Back Right": brf[1]})
    wheel_mode_vars.update({"Back Left": blf[2], "Back Right": brf[2]})
    blf[0].grid(row=2, column=0)
    tk.Button(main_frame, text="Backward", width=12, height=3, command=lambda: send_command(2)).grid(row=2, column=1)
    brf[0].grid(row=2, column=2)

    # Label și indicator
    last_command_label = tk.Label(root, text="Ultima comandă: ", bg="lightgray")
    last_command_label.pack(pady=5)
    save_indicator_canvas = tk.Canvas(root, width=24, height=24, bg="lightgray", highlightthickness=0)
    save_indicator_canvas.pack()
    update_indicator("red")

    root.mainloop()

if __name__ == "__main__":
    main()
