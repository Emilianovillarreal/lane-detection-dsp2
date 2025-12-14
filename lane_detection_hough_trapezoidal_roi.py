# -*- coding: utf-8 -*-
import cv2
import numpy as np
import math

# -------------------------------
# Cargar video
# -------------------------------
cap = cv2.VideoCapture('ruta.mp4')

if not cap.isOpened():
    print("Error: No se pudo abrir el video.")
    exit()

# ------------------------------
# VARIABLES PARA UMBRAL AUTOMÁTICO
# ------------------------------
frames_sin_izq_actual = 0
max_sin_izq = 0
UMBRAL_DESVIO = None
frames_calibracion = 150   # ~5 segundos si el video es 30 fps
contador_frames = 0
alarma = False    

# Tamaño fijo
FRAME_W = 600
FRAME_H = 600

h, w = FRAME_H, FRAME_W

# -------------------------------
# ROI TRAPEZOIDAL
# -------------------------------
trap = np.array([[
    (int(w * 0.01), h),           # inferior izquierda
    (int(w * 0.39), int(h * 0.50)), # superior izquierda
    (int(w * 0.55), int(h * 0.50)), # superior derecha
    (int(w * 0.95), h)            # inferior derecha
]], dtype=np.int32)


# -------------------------------
# Función pendiente
# -------------------------------
def slope(x1, x2, y1, y2):
    if x2 - x1 == 0:
        return 0
    m = (y2 - y1) / (x2 - x1)
    return math.degrees(math.atan(m))

# ------------------------------
# Inicializar contadores
# ------------------------------
frames_con_linea = 0
frames_sin_linea = 0

# -------------------------------
# Loop principal
# -------------------------------
while True:

    ret, frame1 = cap.read()
    if not ret:
        print("Fin del video.")
        break

    frame = cv2.resize(frame1, (FRAME_W, FRAME_H))

    # ===============================
    # HSV
    # ===============================
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # ===============================
    # MÁSCARA ROI TRAPEZOIDAL
    # ===============================
    mask_roi = np.zeros((h, w), dtype=np.uint8)
    cv2.fillPoly(mask_roi, trap, 255)

    hsv_roi = cv2.bitwise_and(hsv, hsv, mask=mask_roi)

    # Debug ROI
    debug_roi = frame.copy()
    cv2.polylines(debug_roi, trap, True, (255, 0, 0), 2)
    cv2.imshow("ROI TRAPEZOIDAL", debug_roi)

    # ===============================
    # Rangos HSV
    # ===============================
    # Blanco
    low_white  = np.array([0, 0, 180])
    high_white = np.array([180, 60, 255])

    # Amarillo / naranja
    low_yellow  = np.array([15, 60, 120])
    high_yellow = np.array([40, 255, 255])

    mask_white  = cv2.inRange(hsv_roi, low_white, high_white)
    mask_yellow = cv2.inRange(hsv_roi, low_yellow, high_yellow)

    mask = cv2.bitwise_or(mask_white, mask_yellow)

    # ===============================
    # Limpieza
    # ===============================
    kernel = np.ones((9, 9), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.GaussianBlur(mask, (5, 5), 0)

    cv2.imshow("MASK WHITE", mask_white)
    cv2.imshow("MASK YELLOW", mask_yellow)
    cv2.imshow("MASK COMBINED", mask)

    # ===============================
    # HOUGH
    # ===============================
    linea_izquierda_detectada = False
    segmentos_izq = 0
    
    
    lines = cv2.HoughLinesP(
        mask,
        rho=1,
        theta=np.pi / 180,
        threshold=40,
        minLineLength=120,
        maxLineGap=50
    )

    frame_out = frame.copy()

    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]

            ang = slope(x1, x2, y1, y2)
            longitud = np.hypot(x2 - x1, y2 - y1)
            
            # Punto medio
            xm = (x1 + x2) // 2
            
            # CRITERIO DE LINEA (INCLINACIÓN + LONGITUD)
            if (-80 <= ang <= -30 or 30 <= ang <= 80) and longitud > 60:
                # DIBUJAR TODAS
                cv2.line(frame_out, (x1, y1), (x2, y2), (0, 255, 0), 3)

                # CONTAR SOLO IZQUIERDA
                if xm < w // 2:
                    segmentos_izq += 1

    
    # CRITERIO FINAL DE LINEA IZQUIERDA
    linea_detectada = segmentos_izq >= 3
    
    # ------------------------------
    # MEDICIÓN TEMPORAL (LINEA IZQUIERDA)
    # ------------------------------
    if linea_detectada:
        if frames_sin_izq_actual > 0:
            max_sin_izq = max(max_sin_izq, frames_sin_izq_actual)
        frames_sin_izq_actual = 0
    else:
        frames_sin_izq_actual += 1
    
    
    contador_frames += 1

    if contador_frames == frames_calibracion:
        UMBRAL_DESVIO = max_sin_izq * 2
        # UMBRAL_DESVIO=10
        print(f"[INFO] Umbral automático establecido en {UMBRAL_DESVIO} frames")

    if UMBRAL_DESVIO is not None:
        if frames_sin_izq_actual >= UMBRAL_DESVIO:
            alarma = True
        else:
            alarma = False
    
    if alarma:
        cv2.putText(
            frame_out,
            "ALERTA: POSIBLE DESVIO DE CARRIL",
            (80, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 0, 255),
            3
        )

    if alarma:
        print("⚠️ ALERTA: posible desvío del carril")

    
    if linea_detectada:
        frames_con_linea += 1
    else:
        frames_sin_linea += 1
    
    cv2.putText(
        frame_out,
        f"Con linea: {frames_con_linea}  Sin linea: {frames_sin_linea}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 255),
        2
    )
    
    cv2.imshow("DETECTING LINES", frame_out)




    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
