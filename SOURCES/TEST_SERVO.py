import tkinter as tk
from tkinter import ttk
from threading import Thread
import time
from USART_COM.serial_module import process_command


# ================== Funcții ==================
def read_response(timeout_sec=10):
    start = time.time()
    while time.time() - start < timeout_sec:
        data = process_command(3, 0, 0, [0])
        if data:
            print("STM32 response:", data)
            return data
        time.sleep(0.5)
    print("No response in time.")
    return None

def safe_process(servo_id, state, retry=False):
    while True:
        process_command(2, servo_id, state, [0])
        response = read_response()
        response_label.config(text=f"Răspuns STM32: {response}")
        if not retry or (response and 0 not in response):
            break
        print("Retrying...")
        time.sleep(1)


# ================== Acțiuni butoane ==================
def servo_action(servo_id, state):
    retry = retry_var.get()
    Thread(target=safe_process, args=(servo_id, state, retry)).start()

def ajustare_cutie():
    process_command(8, 8, 0, [0])
    response_label.config(text="Comandă ajustare cutie trimisă")

def calibrare_low_budget():
    def worker():
        process_command(2, 10, 0, [0])
        time.sleep(2)
        process_command(2, 10, 4, [0])
        time.sleep(2)
        process_command(2, 10, 0, [0])
        read_response()
        time.sleep(2)
        response_label.config(text="Calibrare LOW BUDGET finalizată")
    Thread(target=worker).start()

def calibrare_auto():
    process_command(2, 10, 2, [0])
    response_label.config(text="Comandă calibrare automată trimisă")

def buton_stop():
    stop_var.set(True)
    response_label.config(text="STOP apăsat – oprire comenzi")


# ================== UI ==================
root = tk.Tk()
root.title("Interfață Testare Servo")

main_frame = ttk.Frame(root, padding=20)
main_frame.grid(row=0, column=0)

response_label = ttk.Label(main_frame, text="Răspuns STM32: --", font=("Helvetica", 12))
response_label.grid(row=0, column=1, pady=10)

retry_var = tk.BooleanVar()
ttk.Checkbutton(main_frame, text="Retry până când reușește", variable=retry_var).grid(row=1, column=1, pady=5)

stop_var = tk.BooleanVar(value=False)

# Butoane servo
button_map = [
    ("Coboară Servo 9", lambda: servo_action(9, 1), 2, 0),
    ("Ridică Servo 9", lambda: servo_action(9, 0), 0, 0),
    ("Strânge Servo 10", lambda: servo_action(10, 1), 1, 1),
    ("Eliberează Servo 10", lambda: servo_action(10, 0), 1, 2)
]

for label, command, r, c in button_map:
    ttk.Button(main_frame, text=label, command=command).grid(row=r + 2, column=c, padx=10, pady=5)

# Linie de separație
sep = ttk.Separator(main_frame, orient='horizontal')
sep.grid(row=6, columnspan=3, sticky="ew", pady=10)

# Butoane calibrare
calibrare_frame = ttk.Frame(main_frame)
calibrare_frame.grid(row=7, columnspan=3)

calib_btn1 = ttk.Button(calibrare_frame, text="Calibrare LOW BUDGET", command=calibrare_low_budget)
calib_btn1.grid(row=0, column=0, padx=10)

calib_btn2 = ttk.Button(calibrare_frame, text="Calibrare Automată", command=calibrare_auto)
calib_btn2.grid(row=0, column=1, padx=10)

# Ajustare cutie + STOP
ttk.Button(main_frame, text="Ajustează Cutia", command=ajustare_cutie).grid(row=8, column=1, pady=5)
ttk.Button(main_frame, text="STOP", command=buton_stop).grid(row=9, column=1, pady=10, ipadx=10)

root.mainloop()
