# -*- coding: utf-8 -*-
"""
Created on Sat Mar 28 00:47:15 2026

@author: Villarreal Emiliano
"""

# -*- coding: utf-8 -*-
import cv2
import numpy as np
import math


# -------------------------------
# Cargar video o camara
# -------------------------------
# cap = cv2.VideoCapture(1)         # activa la camara

# cap = cv2.VideoCapture("video1.avi")     #  [            ]
# cap = cv2.VideoCapture("video2.avi")     #  [ video      ]
cap = cv2.VideoCapture("video3.avi")     #  [ pregrabado ]
 
     

if not cap.isOpened():
    print("Error al abrir el video o acceder a camara")
    exit()

# -------------------------------
# Parámetros generales
# -------------------------------
FRAME_W = 600
FRAME_H = 600

h, w = FRAME_H, FRAME_W
centro_imagen = w // 2


UMBRAL_PISADA = 40
UMBRAL_SALIDA = 10

# -------------------------------
# Memoria
# -------------------------------
x_izq_mem = None
x_der_mem = None

frames_sin_izq = 0
frames_sin_der = 0

UMBRAL_MEMORIA = 25
alpha = 0.8

# NUEVO: flag de ROI global
roi_full = True

# -------------------------------
# Función de ángulo
# -------------------------------
def angulo_linea(x1, y1, x2, y2):
    if x2 - x1 == 0:
        return 90
    return abs(math.degrees(math.atan2(y2 - y1, x2 - x1)))

# -------------------------------
# Loop principal
# -------------------------------
while True:

    ret, frame1 = cap.read()
    if not ret:
        break                                      # comentar si se usa camara
        # continue                                 # descomentar si se usa camara

    frame = cv2.resize(frame1, (FRAME_W, FRAME_H))
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # ===============================
    # ROI DINÁMICA + MODO GLOBAL
    # ===============================
    mask_roi = np.zeros((h, w), dtype=np.uint8)

    roi_top = int(h * 0.55)
    roi_bottom = h
    margen = 60

    if roi_full:
        # ROI COMPLETA
        roi_left = 0
        roi_right = w

    else:
        if x_izq_mem is not None and x_der_mem is not None:
            roi_left = max(0, x_izq_mem - margen)
            roi_right = min(w, x_der_mem + margen)

        elif x_izq_mem is not None:
            roi_left = max(0, x_izq_mem - margen)
            roi_right = w  # expandir para recuperar derecha

        elif x_der_mem is not None:
            roi_left = 0  # expandir para recuperar izquierda
            roi_right = min(w, x_der_mem + margen)

        else:
            roi_left = 0
            roi_right = w

    mask_roi[roi_top:roi_bottom, roi_left:roi_right] = 255
    hsv_roi = cv2.bitwise_and(hsv, hsv, mask=mask_roi)

    # ===============================
    # Segmentación
    # ===============================
    low_white  = np.array([0, 0, 180])
    high_white = np.array([180, 60, 255])

    low_yellow  = np.array([20, 100, 150])
    high_yellow = np.array([35, 255, 255])

    mask = cv2.bitwise_or(
        cv2.inRange(hsv_roi, low_white, high_white),
        cv2.inRange(hsv_roi, low_yellow, high_yellow)
    )

    kernel = np.ones((7,7), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    # ===============================
    # CANNY
    # ===============================
    edges = cv2.Canny(mask, 50, 150)

    # ===============================
    # HOUGH
    # ===============================
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi/180,
        threshold=30,
        minLineLength=60,
        maxLineGap=40
    )

    frame_out = frame.copy()
    x_izq, x_der = [], []

    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]

            ang = angulo_linea(x1, y1, x2, y2)
            if ang < 30 or ang > 150:
                continue

            pendiente = (y2 - y1) / (x2 - x1 + 1e-6)
            xb = x1 if y1 > y2 else x2

            # filtro de pendiente
            if xb < centro_imagen and pendiente > 0:
                continue
            if xb > centro_imagen and pendiente < 0:
                continue

            if xb < centro_imagen:
                x_izq.append(xb)
            else:
                x_der.append(xb)

            cv2.line(frame_out, (x1,y1), (x2,y2), (0,255,0), 2)

    # ===============================
    # PROMEDIO + SUAVIZADO
    # ===============================
    x_izq_m = None
    x_der_m = None

    if len(x_izq) > 0:
        x_izq_m = int(np.mean(x_izq))
        if x_izq_mem is not None:
            x_izq_m = int(alpha * x_izq_mem + (1 - alpha) * x_izq_m)
        x_izq_mem = x_izq_m
        frames_sin_izq = 0
    else:
        frames_sin_izq += 1
        x_izq_m = x_izq_mem

    if len(x_der) > 0:
        x_der_m = int(np.mean(x_der))
        if x_der_mem is not None:
            x_der_m = int(alpha * x_der_mem + (1 - alpha) * x_der_m)
        x_der_mem = x_der_m
        frames_sin_der = 0
    else:
        frames_sin_der += 1
        x_der_m = x_der_mem

    # ===============================
    # ANÁLISIS + CONTROL ROI
    # ===============================
    estado = "OK"
    color_izq = (0,255,0)
    color_der = (0,255,0)

    if (x_izq_m is None or x_der_m is None or
        frames_sin_izq > UMBRAL_MEMORIA or
        frames_sin_der > UMBRAL_MEMORIA):

        estado = "LINEAS NO DETECTADAS"
        roi_full = True   # ACTIVAR ROI COMPLETA

    else:
        roi_full = False  # VOLVER A ROI DINÁMICA

        dist_izq = centro_imagen - x_izq_m
        dist_der = x_der_m - centro_imagen

        if dist_izq < UMBRAL_PISADA:
            estado = "PISANDO IZQUIERDA"
            color_izq = (0,0,255)

        if dist_der < UMBRAL_PISADA:
            estado = "PISANDO DERECHA"
            color_der = (0,0,255)

        if centro_imagen < x_izq_m + UMBRAL_SALIDA:
            estado = "SALIDA IZQUIERDA"

        if centro_imagen > x_der_m - UMBRAL_SALIDA:
            estado = "SALIDA DERECHA"

        cv2.line(frame_out, (x_izq_m,h), (x_izq_m,int(h*0.6)), color_izq, 4)
        cv2.line(frame_out, (x_der_m,h), (x_der_m,int(h*0.6)), color_der, 4)
   
   
    # ===============================
    # DIBUJOS
    # ===============================
    cv2.line(frame_out, (centro_imagen,h), (centro_imagen,int(h*0.6)), (255,0,0), 2)

    cv2.putText(
        frame_out,
        estado,
        (50, 80),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (0,0,255) if "SALIDA" in estado else (0,255,255),
        3
    )

    # Visual ROI
    frame_roi_vis = frame.copy()
    cv2.rectangle(frame_roi_vis, (roi_left, roi_top), (roi_right, roi_bottom), (255,0,0), 3)

    cv2.imshow("LANE DETECTION", frame_out)
    cv2.imshow("ROI", frame_roi_vis)
    cv2.imshow("MASK", mask)
    cv2.imshow("EDGES", edges)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()