# 🚗 Lane Detection System v2 - ROI Adaptativa

Este repositorio contiene un sistema de detección de carriles optimizado para visión artificial en tiempo real, diseñado específicamente para funcionar en dispositivos de recursos limitados como la **Raspberry Pi**.

---

## 🚀 Características principales

- **ROI Dinámica y Adaptativa**  
  El sistema ajusta el área de interés (*Region of Interest*) basándose en la última posición conocida de las líneas, optimizando el uso de CPU.

- **Memoria de Carril**  
  Implementa un contador de frames para mantener la trayectoria incluso si las líneas desaparecen brevemente (hasta 25 frames).

- **Segmentación de Color**  
  Filtros HSV configurados para detectar líneas blancas y amarillas en diversas condiciones de iluminación.

- **Alertas en Tiempo Real**  
  Detecta estados de *"Pisando línea"* o *"Salida de carril"*.

---

## 🛠 Instalación y Uso

### 1. Clonar el repositorio
```bash
git clone https://github.com/tu-usuario/tu-repo.git
