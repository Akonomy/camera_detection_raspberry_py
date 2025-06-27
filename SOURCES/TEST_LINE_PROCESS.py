import threading, time
import tkinter as tk
import cv2
import numpy as np
from CAMERA.camera_session import init_camera, stop_camera, capture_raw_image
from LINE_PROCESS.get_line import detect_colored_boxes_multi, analyze_binary_mosaic_with_guidance, pretty_print_slices

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
            frames = [frame.copy() for _ in range(3)]
            boxes = detect_colored_boxes_multi(frames)
            debug_img, slices = analyze_binary_mosaic_with_guidance(frame.copy(), boxes)
            self.last_slices = slices

            self.draw_on_canvas(debug_img, boxes, slices)
            pretty_print_slices(slices)

        self.win.after(30, self.update_loop)

    def draw_on_canvas(self, debug_img, boxes, slices):
        # Convert BGR to PhotoImage
        img = cv2.cvtColor(debug_img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (self.canvas_size, self.canvas_size))
        self.photo = tk.PhotoImage(width=self.canvas_size, height=self.canvas_size, data=cv2.imencode('.ppm', img)[1].tobytes())
        self.box_canvas.create_image(0,0, anchor='nw', image=self.photo)

        # Overlay the grid of magenta squares for slices
        cell_h = self.canvas_size // self.num_slices
        cx0 = self.canvas_size // 2
        for slice_idx, dist, valid in slices:
            if dist is not None and valid:
                x_canvas = cx0 + int(dist * self.canvas_size / debug_img.shape[1])
                y_canvas = slice_idx * cell_h + cell_h//2
                self.box_canvas.create_rectangle(x_canvas-3, y_canvas-3, x_canvas+3, y_canvas+3, fill='magenta', outline='')

    def on_close(self):
        stop_camera()
        self.win.destroy()

if __name__ == "__main__":
    App().win.mainloop()
