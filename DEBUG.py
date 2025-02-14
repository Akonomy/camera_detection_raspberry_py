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
        # Se folosește funcția process_command cu tipul 1 și parametrii corespunzători
        process_command(1, direction, tick, speed)
        print(f"Comandă trimisă: 1 {direction} {tick} {speed}")
    except Exception as e:
        print(f"Eroare la trimiterea comenzii: {e}")

def main():
    global tick_var, speed_var

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
    # Se creează butoanele radio pentru ticks de la 1 la 10
    for t in range(1, 11):
        rb = tk.Radiobutton(tick_frame, text=str(t), variable=tick_var, value=t)
        rb.pack(anchor=tk.W)

    # --- Speed ---
    speed_frame = tk.LabelFrame(top_frame, text="Speed")
    speed_frame.pack(side=tk.LEFT, padx=10)
    speed_var = tk.IntVar(value=130)  # valoare implicită 130
    # Valori posibile pentru viteză extinse: 70, 80, 90, 100, 110, 120, 130, 140, 150
    for s in [70, 80, 90, 100, 110, 120, 130, 140, 150]:
        rb = tk.Radiobutton(speed_frame, text=str(s), variable=speed_var, value=s)
        rb.pack(anchor=tk.W)

    # ==========================
    # Secțiunea de comenzi (direcții)
    # ==========================
    command_frame = tk.Frame(root)
    command_frame.pack(pady=20)

    # Dicționar cu poziționarea în grilă: (rând, coloană): (cod direcție, etichetă)
    # Conform specificației:
    #       [colț stânga sus]     [sus centru]    [colț dreapta sus]
    #       [mijloc stânga]       [centrul mare]  [mijloc dreapta]
    #       [colț stânga jos]     [jos centru]    [colț dreapta jos]
    commands = {
        (0, 0): (3, "Front-Left"),      # STANGA-FATA
        (0, 1): (1, "Forward"),         # INAINTE
        (0, 2): (4, "Front-Right"),     # DREAPTA-FATA
        (1, 0): (10, "Side Left"),      # LATERALA STÂNGA
        (1, 1): (0, "Stop"),            # STOP
        (1, 2): (9, "Side Right"),      # LATERALA DREAPTA
        (2, 0): (5, "Back-Left"),       # BACK-LEFT
        (2, 1): (2, "Backward"),        # INAPOI
        (2, 2): (6, "Back-Right")       # BACK-RIGHT
    }

    # Se creează butoanele în grilă
    for (row, col), (direction, label) in commands.items():
        # Dacă este butonul de STOP, îl facem mai mare
        if direction == 0:
            btn = tk.Button(command_frame, text=label, width=10, height=4,
                            command=lambda d=direction: send_command(d))
        else:
            btn = tk.Button(command_frame, text=label, width=8, height=2,
                            command=lambda d=direction: send_command(d))
        btn.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

    # Configurează celulele grilei pentru redimensionare uniformă (opțional)
    for i in range(3):
        command_frame.grid_rowconfigure(i, weight=1)
        command_frame.grid_columnconfigure(i, weight=1)

    # Pornește bucla principală a interfeței grafice
    root.mainloop()

if __name__ == "__main__":
    main()
