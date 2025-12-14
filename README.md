# Lane Detection using Hough Transform

Proyecto de detección de carriles para la materia DSP II.

## Descripción
El sistema detecta carriles viales en video utilizando:
- ROI trapezoidal
- Espacio de color HSV
- Transformada de Hough probabilística
- Análisis temporal para detección de pérdida de carril

Incluye un umbral adaptativo para diferenciar líneas discontinuas normales de desvíos reales.

## Tecnologías
- Python
- OpenCV
- NumPy

## Ejecución
```bash
python lane_detection_hough_trapezoidal_roi.py
