#Celda 1: Inicialización (Display comentado)
import os
import cv2
import numpy as np
from time import time
from PIL import Image, ImageDraw
from pynq_dpu import DpuOverlay
import matplotlib.pyplot as plt

# ── Display (COMENTADO PARA USO WIRELESS) ──────────────────────
# from pynq.lib.video import DisplayPort, VideoMode, PIXEL_RGB
# displayport = DisplayPort()
# displayport.configure(VideoMode(1024, 600, 24), PIXEL_RGB)
# print("Display inicializado: 1024x600")

# ── DPU overlay y modelo ───────────────────────────────────────
overlay = DpuOverlay("/usr/local/share/pynq-venv/lib/python3.10/site-packages/pynq_dpu/dpu.bit")
overlay.load_model("/home/xilinx/jupyter_notebooks/small_gray_classifierU96_b1600.xmodel")
print("Modelo cargado: small_gray_classifierU96_b1600.xmodel")

# ── Tensores y escalas de cuantización ────────────────────────
dpu = overlay.runner

inputTensors  = dpu.get_input_tensors()
outputTensors = dpu.get_output_tensors()

shapeIn    = tuple(inputTensors[0].dims)
shapeOut   = tuple(outputTensors[0].dims)
outputSize = int(outputTensors[0].get_data_size() / shapeIn[0])

input_fix_point  = inputTensors[0].get_attr("fix_point")
output_fix_point = outputTensors[0].get_attr("fix_point")
input_scale      = 2 ** input_fix_point
output_scale     = 2 ** (-output_fix_point)

print(f"shapeIn:          {shapeIn}")
print(f"input_fix_point:  {input_fix_point} -> input_scale  = {input_scale}")
print(f"output_fix_point: {output_fix_point} -> output_scale = {output_scale}")
assert shapeIn == (1, 15, 15, 1), f"shapeIn inesperado: {shapeIn}"

# ── Buffers INT8 ───────────────────────────────────────────────
input_data  = [np.empty(shapeIn,  dtype=np.int8, order="C")]
output_data = [np.empty(shapeOut, dtype=np.int8, order="C")]
image = input_data[0]

# ── Microscopio ────────────────────────────────────────────────
# Si no captura, cambiar: VideoCapture(1), (2), etc.
DEVICE = 0
os.environ['OPENCV_LOG_LEVEL'] = 'SILENT'

try:
    cap.release()
except:
    pass

import time as time_mod
time_mod.sleep(1)

cap = cv2.VideoCapture(DEVICE)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

if cap.isOpened():
    print(f"\nCámara abierta en /dev/video{DEVICE}")
    print("Todo listo. Ejecutá la Celda 2 para capturar, contar y enviar al celular.")
else:
    print(f"ERROR: No se pudo abrir /dev/video{DEVICE}. Probá con DEVICE = 1 o 2.")

THRESH = 0.74

#Celda 2: Captura, Inferencia y Transmisión a Flask
try:
    ret, frame_bgr = cap.read()

    if not ret:
        print("ERROR: No se pudo capturar. Verificar conexión del microscopio.")
    else:
        # ── Preparar imagen para el modelo ────────────────────
        frame_gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        x = frame_gray.astype(np.float32) / 255.0

        # ── Inferencia: 1344 parches de 15x15 ─────────────────
        resultados = []
        start = time()

        for j in range(480 // 15):
            for i in range(640 // 15):
                subimg = x[j*15 : j*15+15, i*15 : i*15+15].reshape([15, 15, 1])
                image[0, ...] = np.int8(subimg * input_scale)
                job_id = dpu.execute_async(input_data, output_data)
                dpu.wait(job_id)
                temp = [j_arr.reshape(1, outputSize) for j_arr in output_data]
                salida_float = temp[0][0].astype(np.float32) * output_scale
                res = 1 / (1 + np.exp(-salida_float))
                if res[0] > 0.3:
                    res[1] = 0
                resultados.append(res[1])

        stop = time()
        execution_time = stop - start
        huevos = sum(r > THRESH for r in resultados)

        # ── Dibujar rectángulos rojos sobre los huevos ────────
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        img_res   = Image.fromarray(frame_rgb)
        draw      = ImageDraw.Draw(img_res)
        ii, jj    = 0, 0
        for r in resultados:
            if r > THRESH:
                draw.rectangle(
                    (ii*15, jj*15, ii*15+15, jj*15+15),
                    outline=(255, 0, 0)
                )
            ii += 1
            if ii >= (640 // 15):
                ii = 0
                jj += 1

        # ── Mostrar en el display (COMENTADO) ─────────────────
        # frame_result  = np.array(img_res)
        # frame_bgr_out = cv2.cvtColor(frame_result, cv2.COLOR_RGB2BGR)
        # cv2.putText(...)
        # frame_resized = cv2.resize(...)
        # display_frame = displayport.newframe()
        # display_frame[:, :, :] = frame_resized
        # displayport.writeframe(display_frame)
        
        # ── ENVIAR A FLASK (Para ver en el celular) ───────────
        img_res.save('/tmp/resultado.png')
        with open('/tmp/conteo.txt', 'w') as f:
            f.write(str(huevos))
        # ──────────────────────────────────────────────────────

        print(f"Huevos detectados: {huevos}")
        print(f"Tiempo de inferencia: {execution_time:.4f}s")
        print("¡Imagen enviada! Revisá la pestaña del servidor Flask en tu celular.")
        
        # También lo dejamos en el notebook por si estás en la PC
        plt.figure(figsize=(10, 7))
        plt.imshow(img_res)
        plt.title(f'Resultado: {huevos} huevos detectados')
        plt.axis('off')
        plt.show()

finally:
    pass  # cap sigue abierta para la próxima captura

#Celda 3: Liberación de recursos
try:
    cap.release()
    print("Cámara liberada.")
except:
    print("Cámara ya estaba liberada.")

# try:
#     displayport.close()
#     print("Display cerrado.")
# except:
#     print("Display ya estaba cerrado.")

try:
    del overlay
    del dpu
    print("DPU liberado.")
except:
    print("DPU ya estaba liberado.")