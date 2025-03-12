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

# last_command_info va fi un tuple: (cmd_str, direction)
last_command_info = None  
# last_saved_command va reține stringul ultimei comenzi salvate
last_saved_command = None

last_command_label = None  # Label ce afișează ultima comandă
save_indicator_canvas = None  # Indicatorul de salvare (cerc)

# Funcție pentru actualizarea indicatorului de salvare
def update_indicator(color):
    global save_indicator_canvas
    save_indicator_canvas.delete("all")
    # Desenează un cerc plin de culoarea specificată (cerc de 20x20 pixeli)
    save_indicator_canvas.create_oval(2, 2, 22, 22, fill=color, outline=color)








def on_mousewheel(event, var, delta):
    try:
        current = int(var.get())
    except ValueError:
        current = 0
    new_val = current + delta
    var.set(str(new_val))
    return "break"

def bind_mousewheel(entry, var):
    if sys.platform.startswith('linux'):
        # Pe Linux, folosim evenimentele Button-4 și Button-5
        entry.bind("<Button-4>", lambda event: on_mousewheel(event, var, +1))
        entry.bind("<Button-5>", lambda event: on_mousewheel(event, var, -1))
    else:
        # Pe Windows, folosim evenimentul MouseWheel
        entry.bind("<MouseWheel>", lambda event: on_mousewheel(event, var, 1 if event.delta > 0 else -1))





# Funcție ce actualizează valoarea default la checkbox-ul procent
def update_wheel_default(toggle_var, var):
    if toggle_var.get():
        var.set("100")
    else:
        var.set("160")

# Funcție helper pentru a crea un panou de input pentru o roată
def create_wheel_frame(parent, wheel_name):
    frame = tk.Frame(parent, bg="white", bd=2, relief=tk.GROOVE)
    lbl = tk.Label(frame, text=wheel_name, bg="white", font=("Helvetica", 14))
    lbl.pack()
    # Default pentru valoare: 160 (ne-bifat)
    var = tk.StringVar(value="160")
    entry = tk.Entry(frame, textvariable=var, font=("Helvetica", 20), width=5, justify="center")
    entry.pack(padx=5, pady=5)
    bind_mousewheel(entry, var)
    # Checkbutton pentru a selecta dacă valoarea e în procente
    toggle_var = tk.BooleanVar(value=False)
    chk = tk.Checkbutton(frame, text="%", variable=toggle_var, bg="white", font=("Helvetica", 12),
                          command=lambda: update_wheel_default(toggle_var, var))
    chk.pack(padx=5, pady=5)
    return frame, var, toggle_var

# Funcția care preia valorile și apelează process_command
def send_command(direction):
    global last_command_info, last_command_label, last_saved_command
    tick = tick_var.get()
    mode = speed_mode_var.get()
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
            entry_value = wheel_speed_vars[wheel].get()
            try:
                val = float(entry_value)
            except ValueError:
                print(f"Eroare: Valoarea pentru {wheel} trebuie să fie un număr!")
                return
            if wheel_mode_vars[wheel].get():
                # Interpretare ca procent din viteza generală
                computed = int(round(gen_speed * (val / 100)))
                computed = max(0, min(255, computed))
                speeds.append(computed)
            else:
                abs_speed = int(round(val))
                abs_speed = max(0, min(255, abs_speed))
                speeds.append(abs_speed)
        speed_vector = speeds
    try:
        process_command(1, tick, direction, speed_vector)
        print(f"Comanda trimisă: 1 {tick} {direction} {speed_vector}")
    except Exception as e:
        print(f"Eroare la trimiterea comenzii: {e}")
        return

    # Formatează comanda ca string
    cmd_str = f"1 {tick} {direction} {speed_vector}"
    # Salvează ca tuple: (comanda, directia)
    last_command_info = (cmd_str, direction)
    direction_names = {1: "Forward", 2: "Backward", 9: "Side Left", 10: "Side Right"}
    dir_text = direction_names.get(direction, str(direction))
    if mode == "uniform":
        disp_speed = speed_vector[0]
    else:
        disp_speed = speed_vector  # se poate calcula o medie, dacă dorești
    last_command_label.config(text=f"Ultima comandă: Direcție: {dir_text}, Speed: {disp_speed}")
    # Dacă comanda trimisă este diferită de ultima comandă salvată, LED-ul devine roșu
    if last_saved_command != cmd_str:
        update_indicator("red")

# Funcția care salvează comanda afişată (ultima comandă) în fișierul corespunzător,
# folosind formatul Python (literal de dicționar)
def save_command():
    global last_command_info, last_saved_command
    if last_command_info is None:
        print("Nu există nicio comandă de salvat!")
        update_indicator("red")
        return

    try:
        # Citește valoarea DISTANCE din câmpul de input dedicat
        distance = float(distance_var.get())
    except ValueError:
        print("Distance must be a number!")
        update_indicator("red")
        return

    # Dacă distanța este 0, întreabă utilizatorul înainte de salvare
    if distance == 0:
        ok = messagebox.askyesno("Atenție", "Distanța este 0. Ești sigur că dorești să salvezi comanda cu distanță 0?")
        if not ok:
            print("Salvare anulată de utilizator.")
            update_indicator("red")
            return

    cmd_str, direction = last_command_info
    # Formatul de salvare specific Python: un literal de dicționar
    line = f"{{'cmd': '{cmd_str}', 'distance': {distance}}}\n"

    try:
        # Se salvează în fișierul corespunzător direcției
        if direction == 1:
            with open("CAR_forward.txt", "a") as f:
                f.write(line)
        elif direction == 2:
            with open("CAR_back.txt", "a") as f:
                f.write(line)
        elif direction == 9:
            with open("CAR_left.txt", "a") as f:
                f.write(line)
        elif direction == 10:
            with open("CAR_right.txt", "a") as f:
                f.write(line)
        else:
            print("Direcție necunoscută; nu s-a salvat comanda în fișierul direcțional.")

        # Se salvează ultima comandă în CAR_last.txt (suprascriere)
        with open("CAR_last.txt", "w") as f_last:
            f_last.write(line)

        print("Comanda a fost salvată cu succes în fișierele corespunzătoare.")
        last_saved_command = cmd_str
        update_indicator("green")
    except Exception as e:
        print(f"Eroare la salvarea comenzii: {e}")
        update_indicator("red")

# Funcția principală
def main():
    global tick_var, speed_mode_var, general_speed_var, last_command_label, save_indicator_canvas, distance_var
    global wheel_speed_vars, wheel_mode_vars

    root = tk.Tk()
    root.title("Control Mașină - Debug")
    root.configure(bg="lightgray")

    # Bara de Ticks (1-10)
    ticks_frame = tk.LabelFrame(root, text="Ticks (1-10)", bg="lightblue")
    ticks_frame.pack(fill=tk.X, padx=10, pady=5)
    tick_var = tk.IntVar(value=5)
    for t in range(1, 11):
        rb = tk.Radiobutton(ticks_frame, text=str(t), variable=tick_var, value=t, bg="lightblue")
        rb.pack(side=tk.LEFT, padx=5, pady=5)

    # Zona Speed Mode
    mode_frame = tk.LabelFrame(root, text="Speed Mode", bg="lightgreen", padx=20, pady=10)
    mode_frame.pack(fill=tk.X, padx=10, pady=5)
    speed_mode_var = tk.StringVar(value="individual")
    rb_uniform = tk.Radiobutton(mode_frame, text="Uniform Speed", variable=speed_mode_var,
                                value="uniform", bg="lightgreen", width=15)
    rb_individual = tk.Radiobutton(mode_frame, text="Individual Speed", variable=speed_mode_var,
                                   value="individual", bg="lightgreen", width=15)
    rb_uniform.pack(side=tk.LEFT, padx=5, pady=5)
    rb_individual.pack(side=tk.LEFT, padx=5, pady=5)
    
    # Input pentru DISTANCE și butonul Save
    distance_label = tk.Label(mode_frame, text="DISTANCE:", bg="lightgreen", font=("Helvetica", 12))
    distance_label.pack(side=tk.LEFT, padx=5)
    distance_var = tk.StringVar(value="0")
    # ipady pentru mărirea înălțimii input-ului
    distance_entry = tk.Entry(mode_frame, textvariable=distance_var, width=8, font=("Helvetica", 12))
    distance_entry.pack(side=tk.LEFT, padx=5, ipady=5)
    save_button = tk.Button(mode_frame, text="Save", font=("Helvetica", 12),
                            command=save_command)
    save_button.pack(side=tk.LEFT, padx=5)

    # Layoutul comun (zona centrală)
    main_frame = tk.Frame(root, bg="white", bd=2, relief=tk.GROOVE)
    main_frame.pack(padx=10, pady=10)

    # Rândul 1: [Input (Front Left)]  [Buton Forward]  [Input (Front Right)]
    fl_frame, fl_var, fl_toggle = create_wheel_frame(main_frame, "Front Left")
    fr_frame, fr_var, fr_toggle = create_wheel_frame(main_frame, "Front Right")
    wheel_speed_vars["Front Left"] = fl_var
    wheel_speed_vars["Front Right"] = fr_var
    wheel_mode_vars["Front Left"] = fl_toggle
    wheel_mode_vars["Front Right"] = fr_toggle
    fl_frame.grid(row=0, column=0, padx=10, pady=10)
    btn_forward = tk.Button(main_frame, text="Forward", width=12, height=3, command=lambda: send_command(1))
    btn_forward.grid(row=0, column=1, padx=10, pady=10)
    fr_frame.grid(row=0, column=2, padx=10, pady=10)

    # Rândul 2: [Buton Side Left]  [Input Viteza Generală]  [Buton Side Right]
    btn_side_left = tk.Button(main_frame, text="Side Left", width=12, height=3, command=lambda: send_command(9))
    btn_side_left.grid(row=1, column=0, padx=10, pady=10)
    general_speed_var = tk.StringVar(value="130")
    center_frame = tk.Frame(main_frame, bg="white")
    tk.Label(center_frame, text="Viteza Generală", bg="white", font=("Helvetica", 16)).pack()
    center_entry = tk.Entry(center_frame, textvariable=general_speed_var, font=("Helvetica", 20),
                            width=5, justify="center")
    center_entry.pack(padx=5, pady=5)
    bind_mousewheel(center_entry, general_speed_var)
    center_frame.grid(row=1, column=1, padx=10, pady=10)
    btn_side_right = tk.Button(main_frame, text="Side Right", width=12, height=3, command=lambda: send_command(10))
    btn_side_right.grid(row=1, column=2, padx=10, pady=10)

    # Rândul 3: [Input (Back Left)]  [Buton Backward]  [Input (Back Right)]
    bl_frame, bl_var, bl_toggle = create_wheel_frame(main_frame, "Back Left")
    br_frame, br_var, br_toggle = create_wheel_frame(main_frame, "Back Right")
    wheel_speed_vars["Back Left"] = bl_var
    wheel_speed_vars["Back Right"] = br_var
    wheel_mode_vars["Back Left"] = bl_toggle
    wheel_mode_vars["Back Right"] = br_toggle
    bl_frame.grid(row=2, column=0, padx=10, pady=10)
    btn_backward = tk.Button(main_frame, text="Backward", width=12, height=3, command=lambda: send_command(2))
    btn_backward.grid(row=2, column=1, padx=10, pady=10)
    br_frame.grid(row=2, column=2, padx=10, pady=10)

    # Label pentru ultima comandă (afișat ca un rând suplimentar)
    global last_command_label
    last_command_label = tk.Label(root, text="Ultima comandă: ", bg="lightgray", font=("Helvetica", 14))
    last_command_label.pack(padx=10, pady=5)

    # Indicatorul de salvare (cercul mic)
    global save_indicator_canvas
    save_indicator_canvas = tk.Canvas(root, width=24, height=24, bg="lightgray", highlightthickness=0)
    save_indicator_canvas.pack(pady=5)
    # Inițial, indicatorul este roșu (comanda curentă nu este salvată)
    update_indicator("red")

    root.mainloop()

if __name__ == "__main__":
    main()
