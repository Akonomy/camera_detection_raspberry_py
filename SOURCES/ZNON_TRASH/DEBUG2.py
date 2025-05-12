import tkinter as tk
from tkinter import ttk
import time
# Importă funcția de comunicare
from USART_COM.serial_module import process_command

# Variabile globale pentru parametrii selectați
tick_var = None
speed_var = None

def send_command(direction):
    """
    Preia valorile curente pentru ticks și speed și trimite comanda corespunzătoare.
    """
    tick = tick_var.get()
    speed = speed_var.get()
    try:
        process_command(1, direction, tick, speed)
        print(f"Command sent: {direction} | Ticks: {tick} | Speed: {speed}")
    except Exception as e:
        print(f"Error sending command: {e}")

def main():
    global tick_var, speed_var

    root = tk.Tk()
    root.title("Command Tester")

    # =========================
    # Section: Ticks & Speed
    # =========================
    control_frame = tk.Frame(root)
    control_frame.pack(pady=10, fill=tk.X)

    # --- Ticks (10 buttons, horizontal) ---
    ticks_frame = tk.LabelFrame(control_frame, text="Ticks")
    ticks_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
    tick_var = tk.IntVar(value=1)  # Valoare implicită
    for t in range(1, 11):
        rb = tk.Radiobutton(ticks_frame, text=str(t), variable=tick_var, value=t)
        rb.pack(side=tk.LEFT, padx=2, pady=2)

    # --- Speed (9 buttons, horizontal) ---
    speed_frame = tk.LabelFrame(control_frame, text="Speed")
    speed_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
    speed_var = tk.IntVar(value=70)  # Valoare implicită
    speeds = [70, 80, 90, 100, 110, 120, 130, 140, 150]
    for s in speeds:
        rb = tk.Radiobutton(speed_frame, text=str(s), variable=speed_var, value=s)
        rb.pack(side=tk.LEFT, padx=2, pady=2)

    # =========================
    # Section: Command Buttons
    # (Buttons for each case: 0..18)
    # =========================
    # Definirea comenzilor cu codul și descrierea
    commands = {
        0:  "STOP",
        1:  "Forward",
        2:  "Backward",
        3:  "Front-Right",
        4:  "Front-Left",
        5:  "Back-Right",
        6:  "Back-Left",
        7:  "Rotate Right",
        8:  "Rotate Left",
        9:  "Side-Right",
        10: "Side-Left",
        11: "Hard Right Turn",
        12: "Hard Left Turn",
        13: "Hard Left Back",
        14: "Hard Right Back",
        15: "Diagonal Front-Left",
        16: "Diagonal Back-Right",
        17: "Diagonal Front-Right",
        18: "Diagonal Back-Left"
    }

    commands_frame = tk.LabelFrame(root, text="Commands")
    commands_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    # Vom afișa butoanele într-o grilă de 4 rânduri x 5 coloane.
    # (Ultima celulă va rămâne goală, deoarece avem 19 comenzi.)
    num_columns = 5
    for index, cmd in enumerate(range(0, 19)):
        row = index // num_columns
        col = index % num_columns
        btn_text = f"{cmd}: {commands[cmd]}"
        btn = tk.Button(commands_frame, text=btn_text, width=18, height=2,
                        command=lambda d=cmd: send_command(d))
        btn.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")

    # Configurare uniformă a coloanelor din grid
    for i in range(num_columns):
        commands_frame.grid_columnconfigure(i, weight=1)

    root.mainloop()

if __name__ == "__main__":
    main()
