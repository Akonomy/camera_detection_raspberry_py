#NEW_DEBUG.py


#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk
import time
# Importă funcția de comunicare cu noua semnătură:
# process_command(cmd_type, val1, val2, vector)
from USART_COM.serial_module import process_command

# Variabile globale pentru parametrii selectați
tick_var = None
speed_mode_var = None
uniform_speed_var = None
individual_speed_vars = []  # Listă pentru cele 4 viteze (string variables)

def send_command(direction):
    """
    Preia valorile curente pentru ticks și viteză și trimite comanda.
    Se apelează process_command astfel:
       process_command(1, ticks, direction, speed_vector)
    unde:
      - 1 este tipul comenzii,
      - ticks reprezintă numărul de ticks,
      - direction este valoarea direcției (0-10),
      - speed_vector este viteza, fie ca un singur element (uniform), fie ca 4 elemente (individual).
    """
    tick = tick_var.get()
    mode = speed_mode_var.get()
    if mode == "uniform":
        speed = uniform_speed_var.get()
        speed_vector = [speed]  # vector cu un singur element
    else:
        try:
            speeds = [int(var.get()) for var in individual_speed_vars]
        except ValueError:
            print("Eroare: Viteza individuală trebuie să fie un număr întreg!")
            return
        speed_vector = speeds

    try:
        process_command(1, tick, direction, speed_vector)
        print(f"Comandă trimisă: 1 {tick} {direction} {speed_vector}")
    except Exception as e:
        print(f"Eroare la trimiterea comenzii: {e}")

def toggle_speed_mode():
    """
    Actualizează vizibilitatea controalelor de viteză în funcție de modul selectat.
    """
    mode = speed_mode_var.get()
    if mode == "uniform":
        uniform_speed_frame.pack(pady=5)
        individual_speed_frame.pack_forget()
    else:
        uniform_speed_frame.pack_forget()
        individual_speed_frame.pack(pady=5)

def main():
    global tick_var, speed_mode_var, uniform_speed_var, individual_speed_vars
    global uniform_speed_frame, individual_speed_frame

    # Crează fereastra principală
    root = tk.Tk()
    root.title("Debug & Setup Parametri")

    # =====================
    # Secțiunea de parametri
    # =====================
    top_frame = tk.Frame(root)
    top_frame.pack(pady=10)

    # --- Ticks ---
    tick_frame = tk.LabelFrame(top_frame, text="Ticks")
    tick_frame.pack(side=tk.LEFT, padx=10)
    tick_var = tk.IntVar(value=7)  # valoare implicită 7
    for t in range(1, 11):
        rb = tk.Radiobutton(tick_frame, text=str(t), variable=tick_var, value=t)
        rb.pack(anchor=tk.W)

    # --- Mod de viteză ---
    speed_mode_frame = tk.LabelFrame(top_frame, text="Speed Mode")
    speed_mode_frame.pack(side=tk.LEFT, padx=10)
    speed_mode_var = tk.StringVar(value="uniform")
    rb_uniform = tk.Radiobutton(speed_mode_frame, text="Uniform Speed", variable=speed_mode_var,
                                value="uniform", command=toggle_speed_mode)
    rb_individual = tk.Radiobutton(speed_mode_frame, text="Individual Speed", variable=speed_mode_var,
                                   value="individual", command=toggle_speed_mode)
    rb_uniform.pack(anchor=tk.W)
    rb_individual.pack(anchor=tk.W)

    # --- Viteză uniformă ---
    uniform_speed_frame = tk.LabelFrame(top_frame, text="Uniform Speed (0-255)")
    uniform_speed_frame.pack(side=tk.LEFT, padx=10)
    uniform_speed_var = tk.IntVar(value=130)
    for s in [70, 80, 90, 100, 110, 120, 130, 140, 150, 180, 200, 220, 240]:
        rb = tk.Radiobutton(uniform_speed_frame, text=str(s), variable=uniform_speed_var, value=s)
        rb.pack(anchor=tk.W)

    # --- Viteză individuală ---
    individual_speed_frame = tk.LabelFrame(top_frame, text="Individual Speeds (0-255)")
    individual_speed_vars = []
    wheel_labels = ["Front Left", "Front Right", "Back Left", "Back Right"]
    for label_text in wheel_labels:
        frame = tk.Frame(individual_speed_frame)
        frame.pack(fill=tk.X, padx=5, pady=2)
        lbl = tk.Label(frame, text=label_text, width=12, anchor="w")
        lbl.pack(side=tk.LEFT)
        var = tk.StringVar(value="130")
        entry = tk.Entry(frame, textvariable=var, width=5)
        entry.pack(side=tk.LEFT)
        individual_speed_vars.append(var)
    # Inițial se folosește modul uniform, deci ascundem frame-ul pentru viteze individuale
    individual_speed_frame.pack_forget()

    # ==========================
    # Secțiunea de comenzi (direcții)
    # ==========================
    command_frame = tk.Frame(root)
    command_frame.pack(pady=20)

    # Noua mapare pentru direcții (doar indecși 0-10)
    directions = {
        0: "Stop",
        1: "Forward",
        2: "Backward",
        3: "Front Left",
        4: "Front Right",
        5: "Back Left",
        6: "Back Right",
        7: "Rotate Left",
        8: "Rotate Right",
        9: "Side Left",
        10: "Side Right"
    }

    # Crearea butoanelor în grilă (aranjate pe 4 coloane)
    for idx, (dir_val, label) in enumerate(directions.items()):
        row = idx // 4
        col = idx % 4
        # Butonul de Stop îl facem mai mare
        if dir_val == 0:
            btn = tk.Button(command_frame, text=label, width=10, height=4,
                            command=lambda d=dir_val: send_command(d))
        else:
            btn = tk.Button(command_frame, text=label, width=8, height=2,
                            command=lambda d=dir_val: send_command(d))
        btn.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

    # Configurarea grilei pentru redimensionare uniformă
    rows = (len(directions) + 3) // 4
    for i in range(rows):
        command_frame.grid_rowconfigure(i, weight=1)
    for i in range(4):
        command_frame.grid_columnconfigure(i, weight=1)

    root.mainloop()

if __name__ == "__main__":
    main()
