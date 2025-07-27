"""
FastAPI app that:
  • Lee un stream MJPEG (IP Webcam Android, etc.)
  • Detecta coincidencias SIFT contra dos logos (pre-cargados)
  • Superpone keypoints y matches en el frame
  • Expone:
      GET /stream        -> MJPEG en tiempo real (multipart/x-mixed-replace)
      GET /stats         -> JSON con FPS, matches y memoria
      GET /stats_html    -> HTML auto-refrescante (cada 1 s) con las stats
      POST /reload-logos -> Recarga logos sin reiniciar

Requisitos:
    pip install fastapi uvicorn opencv-contrib-python numpy psutil

Ejecutar:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000

Notas:
  - SIFT está en opencv-contrib-python. Si usas "opencv-python" no tendrás SIFT.
  - Usa un hilo para capturar/procesar sin bloquear el event loop.
  - Ajusta STREAM_URL y rutas a tus logos.
  - Frontend simple en /static/index.html (montado abajo).
"""

import os
import json
import time
import threading
from pathlib import Path
from typing import Optional, Dict

import cv2
import numpy as np

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import (
    RedirectResponse,
    StreamingResponse,
    JSONResponse,
    HTMLResponse,
)
from fastapi.staticfiles import StaticFiles

# psutil para medir memoria (opcional)
try:
    import psutil
    PROCESS = psutil.Process(os.getpid())
except ImportError:  # fallback si no está instalado
    psutil = None
    PROCESS = None

# ===================== CONFIG =====================
STREAM_URL = "http://192.168.1.16:8080/video"   # Cambia a tu IP / puerto
LOGO1_PATH = Path("Coca_Cola_Logo.jpg")
LOGO2_PATH = Path("logo2.jpg")
RATIO_THRESH = 0.67
GOOD_MATCH_THRESH = 20            # Matches "buenos" para dibujar líneas
FRAME_SIZE = (320, 240)           # (width, height) por vista individual
JPEG_QUALITY = 90                 # Calidad del stream MJPEG
PROCESS_EVERY = 1                 # Procesar cada N frames (1 = todos)

# ===================== GLOBAL STATE =====================
app = FastAPI(title="SIFT Matcher Stream API")

# Monta carpeta estática para servir el frontend
app.mount("/static", StaticFiles(directory="static", html=True), name="static")

cap: Optional[cv2.VideoCapture] = None
sift: Optional[cv2.SIFT] = None
matcher: Optional[cv2.BFMatcher] = None

# Logos y features
logo1_img: Optional[np.ndarray] = None
logo2_img: Optional[np.ndarray] = None
kp1 = desc1 = None
kp2 = desc2 = None

# Estadísticas compartidas
stats_lock = threading.Lock()
shared_stats: Dict[str, float] = {
    "fps": 0.0,
    "logo1_matches": 0,
    "logo2_matches": 0,
    "last_update": 0.0,
    "mem_mb": 0.0,
}

# Último frame procesado (para el stream)
frame_lock = threading.Lock()
last_frame: Optional[np.ndarray] = None

stop_event = threading.Event()

# ===================== HELPER FUNCTIONS =====================

def load_logos(path1: Path, path2: Path) -> None:
    """Carga logos y calcula sus keypoints/desc."""
    global logo1_img, logo2_img, kp1, kp2, desc1, desc2
    img1 = cv2.imread(str(path1))
    img2 = cv2.imread(str(path2))
    if img1 is None or img2 is None:
        raise FileNotFoundError("No se pudo cargar uno o ambos logos.")
    logo1_img, logo2_img = img1, img2
    kp1, desc1 = sift.detectAndCompute(logo1_img, None)
    kp2, desc2 = sift.detectAndCompute(logo2_img, None)


def update_mem_stat():
    if psutil and PROCESS:
        return PROCESS.memory_info().rss / (1024 * 1024)
    return 0.0


def processing_loop():
    global cap, last_frame
    fps_counter = 0
    last_fps_time = time.time()

    while not stop_event.is_set():
        if cap is None or not cap.isOpened():
            time.sleep(0.1)
            continue

        ret, frame = cap.read()
        if not ret or frame is None:
            time.sleep(0.02)
            continue

        frame = cv2.resize(frame, FRAME_SIZE)

        # --- SIFT en cada frame ---
        kp_frame, desc_frame = sift.detectAndCompute(frame, None)
        if desc_frame is not None:
            # Logo 1
            matches1 = matcher.knnMatch(desc1, desc_frame, k=2)
            good1 = [m[0] for m in matches1 if len(m) == 2 and m[0].distance < RATIO_THRESH * m[1].distance]
            # Logo 2
            matches2 = matcher.knnMatch(desc2, desc_frame, k=2)
            good2 = [m[0] for m in matches2 if len(m) == 2 and m[0].distance < RATIO_THRESH * m[1].distance]

            # Dibujar matches de ambos logos
            img_matches1 = cv2.drawMatches(
                logo1_img, kp1, frame, kp_frame, good1, None,
                flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS,
            )
            img_matches2 = cv2.drawMatches(
                logo2_img, kp2, frame, kp_frame, good2, None,
                flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS,
            )

            view_w, view_h = FRAME_SIZE
            img_matches1 = cv2.resize(img_matches1, (view_w, view_h))
            img_matches2 = cv2.resize(img_matches2, (view_w, view_h))
            out_frame = np.hstack([img_matches1, img_matches2])

            # Texto overlay
            cv2.putText(out_frame, f"L1: {len(good1)}", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.putText(out_frame, f"L2: {len(good2)}", (view_w + 10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            with stats_lock:
                shared_stats["logo1_matches"] = len(good1)
                shared_stats["logo2_matches"] = len(good2)
                shared_stats["last_update"] = time.time()
                shared_stats["mem_mb"] = update_mem_stat()

            with frame_lock:
                last_frame = out_frame
        # Si no hay descriptores, no sobreescribimos para evitar parpadeo

        # FPS
        fps_counter += 1
        now = time.time()
        if now - last_fps_time >= 1.0:
            with stats_lock:
                shared_stats["fps"] = fps_counter / (now - last_fps_time)
            fps_counter = 0
            last_fps_time = now

    if cap is not None:
        cap.release()


def mjpeg_generator():
    boundary = "frame"
    encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]
    while not stop_event.is_set():
        with frame_lock:
            frame = None if last_frame is None else last_frame.copy()
        if frame is None:
            time.sleep(0.02)
            continue
        ret, buffer = cv2.imencode(".jpg", frame, encode_params)
        if not ret:
            continue
        jpg_bytes = buffer.tobytes()
        yield (b"--" + boundary.encode() + b"\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + jpg_bytes + b"\r\n")


# ===================== FASTAPI EVENTS =====================

@app.on_event("startup")
def startup_event():
    global cap, sift, matcher
    sift = cv2.SIFT_create()
    matcher = cv2.BFMatcher()

    load_logos(LOGO1_PATH, LOGO2_PATH)

    cap = cv2.VideoCapture(STREAM_URL)
    if not cap.isOpened():
        raise RuntimeError("No se pudo abrir el stream del celular.")

    stop_event.clear()
    t = threading.Thread(target=processing_loop, daemon=True)
    t.start()


@app.on_event("shutdown")
def shutdown_event():
    stop_event.set()


# ===================== ENDPOINTS =====================

@app.get("/stream")
def stream_video():
    return StreamingResponse(mjpeg_generator(), media_type="multipart/x-mixed-replace; boundary=frame")


@app.get("/stats")
def get_stats():
    with stats_lock:
        return JSONResponse(shared_stats.copy())


@app.get("/stats_html", response_class=HTMLResponse)
def stats_html():
    with stats_lock:
        data = shared_stats.copy()
    pretty = json.dumps(data, indent=2)
    return f"""<!DOCTYPE html>
<html><head>
<meta charset='utf-8'>
<meta http-equiv='refresh' content='1'>
<style>
body {{ margin:0; background:#111; color:#eee; font-family: monospace; font-size:14px; }}
pre  {{ padding:8px; }}
</style>
</head><body>
<pre>{pretty}</pre>
</body></html>"""


@app.post("/reload-logos")
async def reload_logos(
    logo1_file: Optional[UploadFile] = File(None),
    logo2_file: Optional[UploadFile] = File(None),
    logo1_path: Optional[str] = Form(None),
    logo2_path: Optional[str] = Form(None),
):
    """Recarga logos desde archivos o paths en disco."""
    global logo1_img, logo2_img, kp1, kp2, desc1, desc2

    new_logo1 = None
    new_logo2 = None

    if logo1_file is not None:
        data = await logo1_file.read()
        file_array = np.frombuffer(data, np.uint8)
        new_logo1 = cv2.imdecode(file_array, cv2.IMREAD_COLOR)
    elif logo1_path:
        new_logo1 = cv2.imread(logo1_path)

    if logo2_file is not None:
        data = await logo2_file.read()
        file_array = np.frombuffer(data, np.uint8)
        new_logo2 = cv2.imdecode(file_array, cv2.IMREAD_COLOR)
    elif logo2_path:
        new_logo2 = cv2.imread(logo2_path)

    if new_logo1 is None and new_logo2 is None:
        raise HTTPException(status_code=400, detail="No se envió ningún logo válido")

    if new_logo1 is not None:
        logo1_img = new_logo1
        kp1, desc1 = sift.detectAndCompute(logo1_img, None)
    if new_logo2 is not None:
        logo2_img = new_logo2
        kp2, desc2 = sift.detectAndCompute(logo2_img, None)

    return {"status": "ok"}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")
