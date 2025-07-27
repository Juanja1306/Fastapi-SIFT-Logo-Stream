# FastAPI SIFT Logo Stream Detector

Un sistema de detección de logos en tiempo real usando **SIFT (Scale-Invariant Feature Transform)** con FastAPI que procesa streams MJPEG y detecta coincidencias de logos pre-cargados.

## 🚀 Características

- **Detección SIFT en tiempo real**: Procesa streams MJPEG y detecta logos usando algoritmos SIFT
- **Stream MJPEG**: Visualización en tiempo real con keypoints y matches superpuestos
- **Múltiples logos**: Soporte para detectar múltiples logos simultáneamente
- **API REST**: Endpoints para estadísticas, recarga de logos y control del sistema
- **Interfaz web**: Frontend moderno con auto-refresh de estadísticas
- **Recarga en caliente**: Cambio de logos sin reiniciar la aplicación
- **Monitoreo**: Estadísticas de FPS, matches y uso de memoria

## 📋 Requisitos

- Python 3.11
- OpenCV con contribuciones (SIFT)
- FastAPI + Uvicorn
- Numpy
- Psutil (opcional, para monitoreo de memoria)

## 🛠️ Instalación

1. **Clonar el repositorio**:
```bash
git clone <repository-url>
cd fastapi-sift-logo-stream
```

2. **Instalar dependencias**:
```bash
pip install -r requirements.txt
```

**Nota importante**: SIFT requiere `opencv-contrib-python`. Si usas `opencv-python` no tendrás acceso a SIFT.

## ⚙️ Configuración

### 1. Configurar el stream de video

Edita `main.py` y modifica la variable `STREAM_URL`:

```python
STREAM_URL = "http://192.168.1.16:8080/video"   # Cambia a tu IP / puerto
```

### 2. Configurar logos

Coloca tus archivos de logo en el directorio raíz:
- `Coca_Cola_Logo.jpg` (logo 1)
- `logo2.jpg` (logo 2)

O modifica las rutas en `main.py`:

```python
LOGO1_PATH = Path("Coca_Cola_Logo.jpg")
LOGO2_PATH = Path("logo2.jpg")
```

### 3. Ajustar parámetros SIFT

```python
RATIO_THRESH = 0.67              # Umbral de ratio para matches
GOOD_MATCH_THRESH = 20            # Mínimo de matches "buenos"
FRAME_SIZE = (320, 240)           # Tamaño de frame
JPEG_QUALITY = 90                 # Calidad del stream MJPEG
PROCESS_EVERY = 1                 # Procesar cada N frames
```

## 🚀 Ejecución

### Desarrollo
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Producción
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 📡 API Endpoints

### `GET /`
- **Descripción**: Redirige al frontend web
- **Respuesta**: HTML con interfaz de usuario

### `GET /stream`
- **Descripción**: Stream MJPEG en tiempo real
- **Tipo**: `multipart/x-mixed-replace`
- **Contenido**: Video con keypoints y matches superpuestos

### `GET /stats`
- **Descripción**: Estadísticas en tiempo real
- **Respuesta**: JSON
```json
{
  "fps": 15.2,
  "logo1_matches": 12,
  "logo2_matches": 0,
  "last_update": 1640995200.0,
  "mem_mb": 45.6
}
```

### `GET /stats_html`
- **Descripción**: Estadísticas en HTML auto-refrescante
- **Respuesta**: HTML con meta refresh cada 1 segundo

### `POST /reload-logos`
- **Descripción**: Recarga logos sin reiniciar la aplicación
- **Parámetros**:
  - `logo1_file`: Archivo de imagen (opcional)
  - `logo2_file`: Archivo de imagen (opcional)
  - `logo1_path`: Ruta en disco (opcional)
  - `logo2_path`: Ruta en disco (opcional)
- **Respuesta**: `{"status": "ok"}`

## 🎯 Uso

### 1. Configurar stream de video

**Opción A: IP Webcam (Android)**
1. Instala "IP Webcam" desde Google Play
2. Configura la IP y puerto en la app
3. Actualiza `STREAM_URL` en `main.py`

**Opción B: Webcam local**
```python
STREAM_URL = 0  # Usar webcam local
```

### 2. Ejecutar la aplicación
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Acceder a la interfaz
- Abre `http://127.0.0.1:8000` en tu navegador
- El stream se mostrará automáticamente
- Las estadísticas se actualizan cada segundo

### 4. Monitorear detecciones
- **Logo 1**: Se muestra en el panel izquierdo
- **Logo 2**: Se muestra en el panel derecho
- **Matches**: Número de coincidencias detectadas
- **FPS**: Rendimiento del procesamiento

## 🔧 Archivos del Proyecto

```
fastapi-sift-logo-stream/
├── main.py              # Aplicación FastAPI principal
├── SIFT.py              # Script standalone de prueba SIFT
├── requirements.txt      # Dependencias Python
├── static/
│   └── index.html       # Frontend web
├── Coca_Cola_Logo.jpg   # Logo 1 (ejemplo)
├── logo2.jpg           # Logo 2 (ejemplo)
└── README.md           # Este archivo
```

## 🧠 Algoritmo SIFT

### ¿Qué es SIFT?
SIFT (Scale-Invariant Feature Transform) es un algoritmo de detección de características que:
- Es **invariante a escala**: Detecta logos sin importar su tamaño
- Es **invariante a rotación**: Funciona con logos rotados
- Es **robusto a cambios de iluminación**: Funciona en diferentes condiciones de luz

### Proceso de detección:
1. **Extracción de keypoints**: Puntos característicos en el logo
2. **Cálculo de descriptores**: Vectores que describen cada keypoint
3. **Matching**: Comparación de descriptores entre logo y frame
4. **Filtrado**: Aplicación de ratio test para eliminar falsos positivos
5. **Visualización**: Dibujo de matches y keypoints

## 📊 Monitoreo y Estadísticas

### Métricas disponibles:
- **FPS**: Frames por segundo procesados
- **Logo1_matches**: Número de matches para el primer logo
- **Logo2_matches**: Número de matches para el segundo logo
- **Mem_mb**: Uso de memoria en MB
- **Last_update**: Timestamp de la última actualización

### Visualización:
- **Panel izquierdo**: Matches del Logo 1
- **Panel derecho**: Matches del Logo 2
- **Overlay de texto**: Contador de matches en tiempo real

## 🔄 Recarga en Caliente

### Cambiar logos sin reiniciar:
```bash
# Usando curl
curl -X POST "http://localhost:8000/reload-logos" \
  -F "logo1_file=@nuevo_logo1.jpg" \
  -F "logo2_file=@nuevo_logo2.jpg"
```

### O usando paths:
```bash
curl -X POST "http://localhost:8000/reload-logos" \
  -F "logo1_path=/ruta/a/nuevo_logo1.jpg" \
  -F "logo2_path=/ruta/a/nuevo_logo2.jpg"
```

## 🐛 Solución de Problemas

### Error: "No se pudo abrir el stream"
- Verifica que la IP y puerto sean correctos
- Confirma que el stream esté activo
- Prueba con `STREAM_URL = 0` para webcam local

### Error: "No se pudo cargar logos"
- Verifica que los archivos de logo existan
- Confirma que sean imágenes válidas (JPG, PNG)
- Revisa las rutas en `LOGO1_PATH` y `LOGO2_PATH`

### Bajo FPS:
- Reduce `FRAME_SIZE`
- Aumenta `PROCESS_EVERY`
- Reduce `JPEG_QUALITY`

### SIFT no disponible:
```bash
pip uninstall opencv-python
pip install opencv-contrib-python
```

## 🚀 Optimizaciones

### Para mejor rendimiento:
1. **Reducir resolución**: `FRAME_SIZE = (160, 120)`
2. **Procesar menos frames**: `PROCESS_EVERY = 2`
3. **Ajustar calidad**: `JPEG_QUALITY = 70`
4. **Optimizar logos**: Usar imágenes más pequeñas

### Para mejor detección:
1. **Ajustar ratio**: `RATIO_THRESH = 0.75`
2. **Usar logos de alta calidad**
3. **Evitar logos muy similares**

