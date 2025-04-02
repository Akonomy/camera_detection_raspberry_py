#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from USART_COM.serial_module import process_command  # presupune că modulul este în calea PYTHONPATH

# Funcții helper pentru conversii
def to_int(value, default=0):
    try:
        return int(value)
    except ValueError:
        return default

def normalize_vector(vec, required_length=4):
    """
    Completează vectorul cu 0 până când are required_length elemente.
    Dacă vectorul are mai mult de required_length elemente, se trunchiază.
    """
    if len(vec) < required_length:
        return vec + [0]*(required_length - len(vec))
    else:
        return vec[:required_length]

# ----------------------
# Tab pentru cmd_type 2: Control Servo
# ----------------------
class ControlServoFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        # Label și input pentru ID servo
        ttk.Label(self, text="Servo ID:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.servo_id_entry = ttk.Entry(self, width=20)
        self.servo_id_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # Label și input pentru unghi
        ttk.Label(self, text="Angle:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.angle_entry = ttk.Entry(self, width=20)
        self.angle_entry.grid(row=1, column=1, padx=5, pady=5)
        
        # Buton pentru trimitere
        self.send_button = ttk.Button(self, text="Send", command=self.send_command)
        self.send_button.grid(row=2, column=0, columnspan=2, pady=10)
        
    def send_command(self):
        servo_id = to_int(self.servo_id_entry.get())
        angle = to_int(self.angle_entry.get())
        # Pentru cmd_type 2, vectorul default este completat la 4 elemente
        vec = normalize_vector([])
        try:
            process_command(2, servo_id, angle, vec)
            messagebox.showinfo("Control Servo", "Command sent successfully.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

# ----------------------
# Tab pentru cmd_type 3: Request Data
# ----------------------
class RequestDataFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        # Buton pentru Request Data
        self.request_button = ttk.Button(self, text="Request Data", command=self.request_data)
        self.request_button.grid(row=0, column=0, padx=5, pady=5)
        # Zonă text pentru afișarea răspunsului
        self.response_text = scrolledtext.ScrolledText(self, width=50, height=10)
        self.response_text.grid(row=1, column=0, padx=5, pady=5)
        
    def request_data(self):
        try:
            # Pentru cmd_type 3, vectorul default este completat la 4 elemente
            response = process_command(3, 0, 0, normalize_vector([]))
            # Afișăm răspunsul primit
            self.response_text.delete(1.0, tk.END)
            self.response_text.insert(tk.END, "Response:\n" + str(response))
        except Exception as e:
            messagebox.showerror("Error", str(e))

# ----------------------
# Tab pentru cmd_type 4: Save Next Cross Direction
# ----------------------
class SaveCrossDirectionFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        # Pentru cmd_type 4, avem un input pentru data1 (ex: direcția sau altă valoare)
        ttk.Label(self, text="Data1 (Direction Value):").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.data1_entry = ttk.Entry(self, width=20)
        self.data1_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # Buton de trimitere
        self.send_button = ttk.Button(self, text="Send", command=self.send_command)
        self.send_button.grid(row=1, column=0, columnspan=2, pady=10)
        
    def send_command(self):
        data1 = to_int(self.data1_entry.get())
        try:
            # Pentru cmd_type 4, vectorul default este completat la 4 elemente
            process_command(4, data1, 0, normalize_vector([]))
            messagebox.showinfo("Save Cross Direction", "Command sent successfully.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

# ----------------------
# Tab pentru cmd_type 5: Set Mode
# ----------------------
class SetModeFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        # Un input pentru a specifica modul (vector, conform cerinței)
        ttk.Label(self, text="Mode Value:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.mode_entry = ttk.Entry(self, width=20)
        self.mode_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # Buton de trimitere
        self.send_button = ttk.Button(self, text="Send", command=self.send_command)
        self.send_button.grid(row=1, column=0, columnspan=2, pady=10)
        
    def send_command(self):
        mode_val = to_int(self.mode_entry.get())
        try:
            # Pentru cmd_type 5, vectorul default este completat la 4 elemente
            process_command(5, mode_val, 0, normalize_vector([]))
            messagebox.showinfo("Set Mode", "Command sent successfully.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

# ----------------------
# Tab pentru cmd_type 6: Decode and Save Directions
# ----------------------
class DecodeSaveDirectionsFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        # Vom crea două opțiuni implicite: IDLE (mode 0) și LINE FOLLOWER (mode 1)
        self.mode_var = tk.IntVar(value=0)
        self.radio_idle = ttk.Radiobutton(self, text="IDLE (0)", variable=self.mode_var, value=0, command=self.disable_custom)
        self.radio_line = ttk.Radiobutton(self, text="LINE FOLLOWER (1)", variable=self.mode_var, value=1, command=self.disable_custom)
        self.radio_custom = ttk.Radiobutton(self, text="Custom:", variable=self.mode_var, value=-1, command=self.enable_custom)
        self.radio_idle.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.radio_line.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.radio_custom.grid(row=0, column=2, padx=5, pady=5, sticky="w")
        
        # Input pentru modul custom
        self.custom_entry = ttk.Entry(self, width=10, state="disabled")
        self.custom_entry.grid(row=0, column=3, padx=5, pady=5)
        
        # Afișăm 4 inputuri pentru vector (cele 4 octeți)
        ttk.Label(self, text="Vector (4 bytes):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.vector_entries = []
        for i in range(4):
            entry = ttk.Entry(self, width=5)
            entry.grid(row=1, column=1+i, padx=5, pady=5)
            self.vector_entries.append(entry)
        # Buton de trimitere
        self.send_button = ttk.Button(self, text="Send", command=self.send_command)
        self.send_button.grid(row=2, column=0, columnspan=4, pady=10)
        
    def disable_custom(self):
        self.custom_entry.config(state="disabled")
        
    def enable_custom(self):
        self.custom_entry.config(state="normal")
        
    def send_command(self):
        # Determinăm modul selectat
        mode = self.mode_var.get()
        if mode == -1:
            # Custom mode
            try:
                mode = int(self.custom_entry.get())
            except ValueError:
                messagebox.showerror("Error", "Invalid custom mode value!")
                return
        # Citim cele 4 valori pentru vector
        vector = []
        for entry in self.vector_entries:
            try:
                vector.append(int(entry.get()))
            except ValueError:
                messagebox.showerror("Error", "Vector bytes must be integers!")
                return
        # Normalizează vectorul la 4 elemente
        vector = normalize_vector(vector, 4)
        try:
            # Pentru cmd_type 6, folosim mode ca data1, 0 ca data2 și vectorul citit
            process_command(6, mode, 0, vector)
            messagebox.showinfo("Decode & Save Directions", "Command sent successfully.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

# ----------------------
# Main Application Window
# ----------------------
class TestInterface(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("STM32 Test Interface")
        self.geometry("600x400")
        
        notebook = ttk.Notebook(self)
        notebook.pack(expand=True, fill='both')
        
        # Creăm tab-uri pentru fiecare cmd_type (2,3,4,5,6)
        tab2 = ControlServoFrame(notebook)
        tab3 = RequestDataFrame(notebook)
        tab4 = SaveCrossDirectionFrame(notebook)
        tab5 = SetModeFrame(notebook)
        tab6 = DecodeSaveDirectionsFrame(notebook)
        
        notebook.add(tab2, text="Control Servo (2)")
        notebook.add(tab3, text="Request Data (3)")
        notebook.add(tab4, text="Save Cross Direction (4)")
        notebook.add(tab5, text="Set Mode (5)")
        notebook.add(tab6, text="Decode & Save Directions (6)")
        
if __name__ == '__main__':
    app = TestInterface()
    app.mainloop()
