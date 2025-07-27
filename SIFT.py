import cv2
import time

# Ruta del stream MJPEG desde el celular
stream_url = "http://192.168.1.16:8080/video"
cap = cv2.VideoCapture(stream_url)

if not cap.isOpened():
    print("❌ Error: No se pudo abrir el stream del celular.")
    exit()

# Cargar los dos logos
logo1 = cv2.imread("Coca_Cola_Logo.jpg")
logo2 = cv2.imread("logo2.jpg")

if logo1 is None or logo2 is None:
    print("❌ Error: No se pudo cargar uno o ambos logos.")
    exit()

# Crear detector SIFT
sift = cv2.SIFT_create()

# Detectar keypoints y descriptores de ambos logos
kp1, desc1 = sift.detectAndCompute(logo1, None)
kp2, desc2 = sift.detectAndCompute(logo2, None)

# Matcher
matcher = cv2.BFMatcher()

frame_count = 0
fps_counter = 0
last_fps_time = time.time()

while True:
    ret, frame = cap.read()
    if not ret or frame is None:
        print("⚠️ Frame vacío.")
        break

    frame = cv2.resize(frame, (320, 240))
    frame_count += 1

    if frame_count % 5 == 0:
        # Detectar en el frame actual
        kp_frame, desc_frame = sift.detectAndCompute(frame, None)
        if desc_frame is None:
            continue

        ratio_thresh = 0.67

        # === Logo 1 ===
        matches1 = matcher.knnMatch(desc1, desc_frame, k=2)
        good1 = [m[0] for m in matches1 if len(m) == 2 and m[0].distance < ratio_thresh * m[1].distance]

        # === Logo 2 ===
        matches2 = matcher.knnMatch(desc2, desc_frame, k=2)
        good2 = [m[0] for m in matches2 if len(m) == 2 and m[0].distance < ratio_thresh * m[1].distance]

        print(f"Logo1: {len(good1)} matches | Logo2: {len(good2)} matches")

        if len(good1) > 50:
            img_matches1 = cv2.drawMatches(logo1, kp1, frame, kp_frame, good1, None,
                                           flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
            cv2.imshow("Matches1", img_matches1)

        if len(good2) > 50:
            img_matches2 = cv2.drawMatches(logo2, kp2, frame, kp_frame, good2, None,
                                           flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
            cv2.imshow("Matches2", img_matches2)

        frame_with_kp = cv2.drawKeypoints(frame, kp_frame, None)
        cv2.imshow("KeyPoints", frame_with_kp)

    cv2.imshow("Video", frame)

    # Mostrar FPS
    fps_counter += 1
    current_time = time.time()
    if current_time - last_fps_time >= 1.0:
        print(f"FPS: {fps_counter}")
        fps_counter = 0
        last_fps_time = current_time

    if cv2.waitKey(1) & 0xFF == 27:  # ESC
        break

cap.release()
cv2.destroyAllWindows()
