import cv2
import numpy as np

import time
from CAMERA.camera_session import init_camera, stop_camera, capture_raw_image



def preview_filters(image):
    """
    Primește o imagine BGR și returnează un dicționar de imagini procesate:
      - originală
      - grayscale
      - histogram equalized
      - Gaussian blur + threshold (global și adaptiv)
      - median blur + adaptive threshold
      - Canny edges
      - Mosaic + binary invers
    """
    out = {}
    img = image.copy()
    out['original'] = img

    # 1. Grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    out['grayscale'] = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    # 2. Histogram equalization (pentru luminanță)
    equalized = cv2.equalizeHist(gray)
    out['equalized'] = cv2.cvtColor(equalized, cv2.COLOR_GRAY2BGR)

    # 3. Gaussian blur + simple threshold
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    _, thr = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    out['blur+otsu'] = cv2.cvtColor(thr, cv2.COLOR_GRAY2BGR)

    # 4. Adaptive threshold
    adapt = cv2.adaptiveThreshold(gray, 255,
                                  cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                  cv2.THRESH_BINARY_INV,
                                  11, 2)
    out['adaptive'] = cv2.cvtColor(adapt, cv2.COLOR_GRAY2BGR)

    # 5. Median blur + adaptive threshold
    mblur = cv2.medianBlur(gray, 5)
    adapt2 = cv2.adaptiveThreshold(mblur, 255,
                                   cv2.ADAPTIVE_THRESH_MEAN_C,
                                   cv2.THRESH_BINARY_INV,
                                   11, 3)
    out['median+adapt'] = cv2.cvtColor(adapt2, cv2.COLOR_GRAY2BGR)

    # 6. Canny edges (poate elimina reflexii inutile)
    edges = cv2.Canny(gray, 50, 150)
    out['canny'] = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)

    # 7. Mosaic + binary invert
    small = cv2.resize(gray, (128,128), interpolation=cv2.INTER_LINEAR)
    mosaic = cv2.resize(small, (gray.shape[1], gray.shape[0]), interpolation=cv2.INTER_NEAREST)
    _, binm = cv2.threshold(mosaic, 90, 255, cv2.THRESH_BINARY_INV)
    out['mosaic_bin'] = cv2.cvtColor(binm, cv2.COLOR_GRAY2BGR)

    return out




def show_filter_grid(img_dict, tile_width=320):
    keys = list(img_dict.keys())
    images = list(img_dict.values())

    # Redimensionăm imaginile la dimensiuni egale
    resized = [cv2.resize(img, (tile_width, tile_width)) for img in images]

    # Stabilim gridul (3x3 maxim)
    cols = 3
    rows = (len(resized) + cols - 1) // cols

    # Umplem cu imagini negre dacă sunt mai puține decât gridul complet
    while len(resized) < rows * cols:
        resized.append(np.zeros_like(resized[0]))

    # Lipim imaginile într-un grid
    grid_rows = [np.hstack(resized[i*cols:(i+1)*cols]) for i in range(rows)]
    full_grid = np.vstack(grid_rows)

    # Adaugă titluri pe imagini
    for i, key in enumerate(keys):
        r = i // cols
        c = i % cols
        x = c * tile_width + 10
        y = r * tile_width + 30
        cv2.putText(full_grid, key, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    return full_grid

def loop_preview():
    init_camera()
    while True:
        frame = capture_raw_image()
        if frame is None:
            print("Camera nu a returnat nimic.")
            break

        filters = preview_filters(frame)
        grid = show_filter_grid(filters)
        cv2.imshow("Filtru Live", grid)

        key = cv2.waitKey(100)
        if key == 27:  # ESC
            break

    cv2.destroyAllWindows()


loop_preview()
