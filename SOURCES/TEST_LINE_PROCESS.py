import threading, time
import tkinter as tk
import cv2
import numpy as np
from CAMERA.camera_session import init_camera, stop_camera, capture_raw_image
from LINE_PROCESS.get_line import detect_colored_boxes_multi, analyze_binary_mosaic_with_guidance, pretty_print_slices,confirm_analyzed_points,extract_dual_data,get_direction_from_confirmed_results
from LINE_PROCESS.get_line import  new_classify_direction

class CameraThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.frame = None
        init_camera()

    def run(self):
        while True:
            img = capture_raw_image()
            self.frame = img
            time.sleep(0.03)  # ~30fps

class App:
    def __init__(self):
        self.win = tk.Tk()
        self.win.title("Line Slice Monitor")

        self.canvas_size = 512
        self.num_slices = 8
        self.box_canvas = tk.Canvas(self.win, width=self.canvas_size, height=self.canvas_size, bg="white")
        self.box_canvas.grid(row=0, column=0, columnspan=3, padx=10, pady=10)

        self.comment = tk.Entry(self.win, width=50)
        self.comment.grid(row=1, column=0, columnspan=2, pady=5)
        self.save_btn = tk.Button(self.win, text="Save", command=self.save_data)
        self.save_btn.grid(row=1, column=2, padx=5)

        self.cam = CameraThread()
        self.cam.start()
        self.last_slices = []
        self.update_loop()

        self.win.protocol("WM_DELETE_WINDOW", self.on_close)

    def save_data(self):
        comment = self.comment.get()
        with open("slice_log.txt", "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {self.last_slices} | {comment}\n")
        print("Saved:", self.last_slices, "|", comment)
        self.comment.delete(0, tk.END)

    def update_loop(self):
        frame = self.cam.frame
        if frame is not None:
            data = extract_dual_data(frame.copy(), num_slices=self.num_slices)
            confirmed = confirm_analyzed_points(data)
            new_direction=new_classify_direction(confirmed)
            direction=get_direction_from_confirmed_results(confirmed)
            print(f"{direction} and new direction  {new_direction} ")
            self.last_slices = confirmed

            # Draw directly on a clone of the image
            display = frame.copy()
            self.draw_on_canvas(display, confirmed)
            #pretty_print_slices([(s, d, p) for s, d, p, _ in confirmed])

        self.win.after(30, self.update_loop)

    def draw_on_canvas(self, img, slices):
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (self.canvas_size, self.canvas_size))
        self.photo = tk.PhotoImage(width=self.canvas_size, height=self.canvas_size, data=cv2.imencode('.ppm', img)[1].tobytes())
        self.box_canvas.create_image(0, 0, anchor='nw', image=self.photo)

        cell_h = self.canvas_size // self.num_slices
        cx0 = self.canvas_size // 2

        for slice_idx, dist, pos, confirmed in slices:
            if pos is None:
                continue
            x, y = pos
            x_canvas = int(x * self.canvas_size / img.shape[1])
            y_canvas = int(y * self.canvas_size / img.shape[0])
            color = 'green' if confirmed else 'magenta'
            self.box_canvas.create_rectangle(x_canvas-3, y_canvas-3, x_canvas+3, y_canvas+3, fill=color, outline='')


    def on_close(self):
        stop_camera()
        self.win.destroy()

if __name__ == "__main__":
    App().win.mainloop()
