# -*- coding: utf-8 -*-
"""
Created on Sat Mar 28 00:47:15 2026

@author: Villarreal Emiliano
revisar:

1_ Latencia del Pipeline completo en fps. (En RASPY) - Metricas.

2_ Tiene que estar por debajo del segundo aprox. 

3_ Investigar sistemas ADAS

4_ 
"""

# -*- coding: utf-8 -*-
import cv2
import numpy as np
import math
import time

# -------------------------------
# Cargar video o camara
# -------------------------------
# cap = cv2.VideoCapture(1)         # activa la camara

# cap = cv2.VideoCapture("video1.avi")     #  [            ]
# cap = cv2.VideoCapture("video2.avi")     #  [ videos     ]
# cap = cv2.VideoCapture("video3.avi")     #  [ pregrabado ]

cap = cv2.VideoCapture("VideoProject1.mp4")
# cap = cv2.VideoCapture("VideoProject2.mp4")

 
if not cap.isOpened():
    print("Error al abrir el video o acceder a camara")
    exit()

# --- Métricas ---
total_frames = 0
frames_ok = 0        # Ambos carriles detectados
frames_memoria = 0   # Usando la memoria (inercia)
lista_fps = []

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

# Almacenan la última posición 'X' válida detectada (promediada y suavizada).
# Se inicializan en None para indicar que al comenzar no hay historial.
x_izq_mem = None
x_der_mem = None

# Contadores de frames consecutivos en los que NO se detectó una línea.
# Sirven para decidir cuándo dejar de confiar en la memoria y reiniciar la búsqueda.
frames_sin_izq = 0
frames_sin_der = 0

# Tolerancia máxima (en cuadros) para mantener la línea en pantalla si se pierde.
# Si pasan más de 25 frames sin detectar nada, el sistema asume pérdida total.
UMBRAL_MEMORIA = 25

# Factor de suavizado para el Filtro de Promedio Exponencial (EMA).
# 0.8 significa que el 80% de la posición actual depende del pasado (estabilidad)
# y el 20% del nuevo dato detectado (reacción).
alpha = 0.5

# Control de estado de la Región de Interés (ROI).
# True: El sistema busca en toda la imagen (útil al iniciar o tras perder el carril).
# False: El sistema usa una ventana reducida cerca de la memoria para ahorrar CPU.
roi_full = True


#--------------- ESTO LO AGREGUE 22/4/26 -----------------------------------------

# --- Métricas Avanzadas ---
tp = 0 # Verdadero Positivo
fn = 0 # Falso Negativo
# ... agregar fp y tn si los necesitas ..

# Abrir el log
archivo_log = open("metricas_analisis.csv", "w")
archivo_log.write("frame,fps,x_izq,x_der,estado\n")

#----------------FIN DE LO QUE AGRGUE. ---------------------------------------

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
    
    t_inicio = time.time() # Captura el tiempo actual
    ret, frame1 = cap.read()
    if not ret:
        break                                      # comentar si se usa camara
        # continue                                 # descomentar si se usa camara

    # Redimensiona el frame a un tamaño estándar (600x600).
    frame = cv2.resize(frame1, (FRAME_W, FRAME_H))
    
    # Convierte el espacio de color de BGR (estándar de OpenCV) a HSV.
    # HSV es superior para detectar colores bajo sombras o cambios de luz (brillo vs crominancia).
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # ===============================
    # ROI DINÁMICA + MODO GLOBAL
    # ===============================
    
    # Crea una máscara negra del tamaño de la imagen (ceros).
    mask_roi = np.zeros((h, w), dtype=np.uint8)

    # Define los límites verticales: solo miramos del 55% hacia abajo (asfalto).
    roi_top = int(h * 0.55)
    roi_bottom = h
    margen = 60     # Margen de búsqueda lateral alrededor de la línea recordada.

    if roi_full:
        # MODO GLOBAL: Si no hay historial, busca en todo el ancho de la imagen.
        roi_left = 0
        roi_right = w

    else:
        # MODO ADAPTATIVO:
        if x_izq_mem is not None and x_der_mem is not None:
            # Si tiene ambas líneas, crea un "pasillo" de búsqueda entre ellas.
            roi_left = max(0, x_izq_mem - margen)
            roi_right = min(w, x_der_mem + margen)

        elif x_izq_mem is not None:
            # Si solo tiene la izquierda, asegura esa zona y abre la derecha para 'recuperar'.
            roi_left = max(0, x_izq_mem - margen)
            roi_right = w  # expandir para recuperar derecha

        elif x_der_mem is not None:
            # Si solo tiene la derecha, abre la izquierda para intentar relocalizarla.
            roi_left = 0  # expandir para recuperar izquierda
            roi_right = min(w, x_der_mem + margen)

        else:
            # Caso de seguridad: si la memoria falla, vuelve a buscar en todo el ancho.
            roi_left = 0
            roi_right = w
    
    # Dibuja el rectángulo blanco en la máscara para definir el área de interés.
    mask_roi[roi_top:roi_bottom, roi_left:roi_right] = 255
    
    # Aplica la máscara: solo los píxeles dentro de la ROI conservan su color HSV, el resto muere.
    # Esto reduce drásticamente el ruido de objetos fuera de la carretera.
    hsv_roi = cv2.bitwise_and(hsv, hsv, mask=mask_roi)

    # ===============================
    # Segmentación
    # ===============================
    
    # Definición de rangos en HSV para filtrar carriles (Blanco y Amarillo)
    low_white  = np.array([0, 0, 180])
    high_white = np.array([180, 60, 255])

    low_yellow  = np.array([20, 100, 150])
    high_yellow = np.array([35, 255, 255])
    
    # Generación de máscara binaria combinando ambos colores dentro de la ROI
    mask = cv2.bitwise_or(
        cv2.inRange(hsv_roi, low_white, high_white),
        cv2.inRange(hsv_roi, low_yellow, high_yellow)
    )
    
    #mask_sin_morfologia = mask.copy()

    # Operación morfológica de clausura para rellenar huecos y eliminar ruido pequeño
    kernel = np.ones((21,21), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    
    #cv2.imshow("Antes Morfologia", mask_sin_morfologia)
    #cv2.imshow("Despues Morfologia", mask)

    # ===============================
    # CANNY: Detector de bordes de Canny para obtener los contornos de la máscara
    # ===============================
    edges = cv2.Canny(mask, 50, 150)

    # ===============================
    # HOUGH : Transformada de Hough Probabilística para detectar segmentos de recta
    # ===============================
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi/180,
        threshold=30,
        minLineLength=60,
        maxLineGap=40
    )
    
    

    frame_out = frame.copy()    # Imagen de salida para visualización
    x_izq, x_der = [], []       # Listas para clasificar coordenadas X de base

    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            
            # Filtro Angular: Elimina líneas horizontales que no pertenecen al carril
            ang = angulo_linea(x1, y1, x2, y2)
            if ang < 30 or ang > 150:
                continue
            
            # Cálculo de pendiente y punto base inferior (punto más cercano al auto)
            pendiente = (y2 - y1) / (x2 - x1 + 1e-6)
            xb = x1 if y1 > y2 else x2

            # filtro de pendiente: Valida la orientación lógica según el cuadrante (Izquierda/Derecha)
            if xb < centro_imagen and pendiente > 0:
                continue
            if xb > centro_imagen and pendiente < 0:
                continue

            # Clasificación espacial de los segmentos detectados
            if xb < centro_imagen:
                x_izq.append(xb)
            else:
                x_der.append(xb)
            
            # Dibujo de segmentos crudos aprobados (Verde fino)
            cv2.line(frame_out, (x1,y1), (x2,y2), (0,255,0), 2)
            #cv2.imshow("HOUGH", frame_out)

    # ===============================
    # PROMEDIO + SUAVIZADO
    # ===============================
    x_izq_m = None
    x_der_m = None
    
    # Procesamiento Lado Izquierdo
    if len(x_izq) > 0:
        x_izq_m = int(np.mean(x_izq))
        if x_izq_mem is not None:
            # Filtro EMA: 80% peso histórico, 20% detección nueva para evitar parpadeo
            x_izq_m = int(alpha * x_izq_mem + (1 - alpha) * x_izq_m)
        x_izq_mem = x_izq_m
        frames_sin_izq = 0      # Reset de contador de pérdida
    else:
        frames_sin_izq += 1
        x_izq_m = x_izq_mem     # Uso de inercia/memoria ante oclusión

    # Procesamiento Lado Derecho (Idem anterior)
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
    
    # Verificación de integridad del sistema (Failsafe)
    if (x_izq_m is None or x_der_m is None or
        frames_sin_izq > UMBRAL_MEMORIA or
        frames_sin_der > UMBRAL_MEMORIA):

        estado = "LINEAS NO DETECTADAS"
        roi_full = True   # Regresa a Modo Búsqueda Global

    else:
        roi_full = False  # Mantiene Modo Seguimiento Eficiente (ROI Adaptativa)

        # Análisis de proximidad al carril (Seguridad Vial)
        dist_izq = centro_imagen - x_izq_m
        dist_der = x_der_m - centro_imagen

        if dist_izq < UMBRAL_PISADA:
            estado = "PISANDO IZQUIERDA"
            color_izq = (0,0,255)

        if dist_der < UMBRAL_PISADA:
            estado = "PISANDO DERECHA"
            color_der = (0,0,255)

        # Detección de invasión crítica de carril opuesto/banquina
        if centro_imagen < x_izq_m + UMBRAL_SALIDA:
            estado = "SALIDA IZQUIERDA"

        if centro_imagen > x_der_m - UMBRAL_SALIDA:
            estado = "SALIDA DERECHA"

        # Dibujo de las líneas maestras promediadas (Grosor 4)
        cv2.line(frame_out, (x_izq_m,h), (x_izq_m,int(h*0.6)), color_izq, 4)
        cv2.line(frame_out, (x_der_m,h), (x_der_m,int(h*0.6)), color_der, 4)
   
   
    # ===============================
    # DIBUJOS
    # ===============================
    
    # Eje central del vehículo (Referencia azul)
    cv2.line(frame_out, (centro_imagen,h), (centro_imagen,int(h*0.6)), (255,0,0), 2)

    # Renderizado de alertas de estado en pantalla
    cv2.putText(
        frame_out,
        estado,
        (50, 80),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (0,0,255) if "SALIDA" in estado else (0,255,255),
        3
    )
    
    # ---------------Esto lo agregue el 22/4/2026
    
    # ... después de las otras llamadas a cv2.putText ...
    
    # Dibujar el NÚMERO DE FRAME actual
    cv2.putText(
        frame_out, 
        f"Frame: {total_frames}", 
        (50, 150), 
        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2
    )
    
    # ---------------Aca termina ------------------

    # Generación de ventana con máscara de ROI visible para depuración
    frame_roi_vis = frame.copy()
    cv2.rectangle(frame_roi_vis, (roi_left, roi_top), (roi_right, roi_bottom), (255,0,0), 3)

    t_final = time.time()
    duracion = t_final - t_inicio  # Tiempo en segundos
    fps_reales = 1 / duracion if duracion > 0 else 0
    
    # 2. ANOTA LAS MÉTRICAS (Ahora la variable fps_reales YA EXISTE)
    total_frames += 1
    # Guardar en archivo para graficar después
    with open("metricas_detalle.csv", "a") as f:
        f.write(f"{fps_reales},{x_izq_m},{x_der_m}\n")
    lista_fps.append(fps_reales)

    if estado == "OK":
        frames_ok += 1
        if (len(x_izq) == 0 or len(x_der) == 0):
            frames_memoria += 1
            
    #--------------------------- ESTO LO AGREGUE EL 22/4/26
    # Determinar si el sistema detectó algo y si la detección es "correcta"
    # (Necesitarías comparar con un valor de referencia, por ejemplo, el frame anterior o un ground truth)
    es_deteccion_real = (len(x_izq) > 0 or len(x_der) > 0)
     
    if es_deteccion_real and estado == "OK":
        tp += 1
    elif not es_deteccion_real and estado == "OK":
        # Aquí ocurrió un Falso Negativo: el sistema dijo OK (usó memoria) pero no detectó nada real
        fn += 1
     
     # Escribir en el log para la matriz de confusión posterior
    archivo_log.write(f"{total_frames},{fps_reales:.2f},{x_izq_m},{x_der_m},{estado}\n") 

     # -------------------------------------------------------------------

    
    # Dibujar en el frame para ver en tiempo real
    cv2.putText(frame_out, f"FPS: {int(fps_reales)} | Latencia: {duracion:.4f}s", 
                (50, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
    
    cv2.imshow("LANE DETECTION", frame_out)
    cv2.imshow("ROI", frame_roi_vis)
    cv2.imshow("MASK", mask)
    cv2.imshow("EDGES", edges)
    
    
    

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
archivo_log.close()
cap.release()
cv2.destroyAllWindows()

# --- INFORME DE DESEMPEÑO TÉCNICO ---
print("\n" + "="*30)
print("  REPORTE DE MÉTRICAS (UNSL)")
print("="*30)
if total_frames > 0:
    disponibilidad = (frames_ok / total_frames) * 100
    confianza_memoria = (frames_memoria / total_frames) * 100
    fps_promedio = np.mean(lista_fps)

    print(f"Frames Procesados:    {total_frames}")
    print(f"FPS Promedio:         {fps_promedio:.2f}")
    print(f"Latencia Promedio:    {1/fps_promedio:.4f}s")
    print("-" * 30)
    print(f"Disponibilidad (OK):  {disponibilidad:.2f}%")
    print(f"Uso de Memoria:       {confianza_memoria:.2f}%")
    print(f"Detección Pura:       {(disponibilidad - confianza_memoria):.2f}%")
    
    if disponibilidad > 90:
        print("Estado del Sistema:   EXCELENTE / ROBUSTO")
    elif disponibilidad > 70:
        print("Estado del Sistema:   ACEPTABLE / ESTABLE")
    else:
        print("Estado del Sistema:   CRÍTICO / REVISAR SEGMENTACIÓN")
print("="*30 + "\n")
