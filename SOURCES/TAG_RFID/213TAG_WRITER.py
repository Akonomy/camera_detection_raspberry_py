import tkinter as tk
from tkinter import ttk
from NFC213 import write_text_tag213
from TAG_PN532 import read_pn532_data, extract_text_from_raw
import threading
import time

TAG_LIST = [
    f"Z[{i}]" for i in range(1, 9)
] + [
    f"C[{i}][{j}]" for i, j in [
        (1,2), (1,3), (1,4),
        (2,1), (2,2), (2,3),
        (3,1), (3,2), (3,4),
        (4,1), (4,4),
        (5,1), (5,2), (5,3), (5,4),
        (6,1), (6,3), (6,4),
        (7,3), (7,4),
        (8,1), (8,2), (8,3), (8,4),
        (9,1), (9,2), (9,3),
        (10,1), (10,2), (10,3)
    ]
]

class NFCWriterUI:
    def __init__(self, root):
        self.root = root
        self.root.title("NFC Tag Writer")
        self.current_index = 0
        self.auto_mode = tk.BooleanVar()
        self.running = False

        self.label = tk.Label(root, text="", font=("Arial", 48))
        self.label.pack(pady=20)

        self.status_frame = tk.Frame(root)
        self.status_frame.pack(pady=10)
        self.status_ok = tk.Label(self.status_frame, width=10, height=5, bg="gray")
        self.status_ok.grid(row=0, column=0, padx=20)
        self.status_fail = tk.Label(self.status_frame, width=10, height=5, bg="gray")
        self.status_fail.grid(row=0, column=1, padx=20)

        self.read_text = tk.Label(root, text="", font=("Arial", 16))
        self.read_text.pack(pady=5)
        self.intent_text = tk.Label(root, text="", font=("Arial", 14), fg="blue")
        self.intent_text.pack(pady=5)

        self.control_frame = tk.Frame(root)
        self.control_frame.pack(pady=10)

        self.auto_check = tk.Checkbutton(self.control_frame, text="AUTO", variable=self.auto_mode, command=self.toggle_auto)
        self.auto_check.grid(row=0, column=0, padx=5)

        self.prev_button = tk.Button(self.control_frame, text="Previous", command=self.prev_tag)
        self.prev_button.grid(row=0, column=1, padx=5)

        self.next_button = tk.Button(self.control_frame, text="Next", command=self.next_tag)
        self.next_button.grid(row=0, column=2, padx=5)

        self.write_button = tk.Button(self.control_frame, text="Write Anyway", command=self.force_write)
        self.write_button.grid(row=0, column=3, padx=5)

        self.read_button = tk.Button(self.control_frame, text="Read Tag", command=self.read_tag)
        self.read_button.grid(row=0, column=4, padx=5)

        self.update_display()

    def update_display(self):
        if self.current_index < len(TAG_LIST):
            tag = TAG_LIST[self.current_index]
            self.label.config(text=tag)
            self.intent_text.config(text=f"Next write: {tag}")
        else:
            self.label.config(text="DONE")
            self.intent_text.config(text="")

    def toggle_auto(self):
        if self.auto_mode.get():
            self.running = True
            threading.Thread(target=self.auto_loop, daemon=True).start()
        else:
            self.running = False

    def auto_loop(self):
        while self.running and self.current_index < len(TAG_LIST):
            self.try_write_tag(TAG_LIST[self.current_index], force=False)
            time.sleep(1)

    def next_tag(self):
        if self.current_index < len(TAG_LIST) - 1:
            self.current_index += 1
            self.update_display()

    def prev_tag(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.update_display()

    def force_write(self):
        if self.current_index < len(TAG_LIST):
            self.try_write_tag(TAG_LIST[self.current_index], force=True)

    def read_tag(self):
        uid, raw = read_pn532_data()
        if uid is None:
            self.set_status("gray", "gray", "No tag detected.")
            return
        text = extract_text_from_raw(raw)
        self.set_status("gray", "gray", f"Read tag: {text}")

    def try_write_tag(self, tag_text, force=False):
        uid, raw = read_pn532_data()
        if uid is None:
            self.set_status("gray", "gray", "No tag detected.")
            return

        existing = extract_text_from_raw(raw)
        if existing and not force:
            self.set_status("gray", "orange", f"Already written: {existing}")
            return

        success = write_text_tag213(tag_text)
        if not success:
            self.set_status("gray", "red", "❌ Write failed.")
            return

        uid2, raw2 = read_pn532_data()
        new_value = extract_text_from_raw(raw2)
        if new_value == tag_text:
            self.set_status("green", "gray", f"✅ Written: {new_value}")
            self.current_index += 1
            self.update_display()
        else:
            self.set_status("gray", "red", f"❌ Verification failed: {new_value}")

    def set_status(self, ok_color, fail_color, text):
        self.status_ok.config(bg=ok_color)
        self.status_fail.config(bg=fail_color)
        self.read_text.config(text=text)


if __name__ == "__main__":
    root = tk.Tk()
    app = NFCWriterUI(root)
    root.mainloop()
