"""Vista local de camara, landmarks y retroalimentacion de pinza."""

from __future__ import annotations

import argparse
import sys
import time
import urllib.request
from collections import deque
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

from sensor.pinch import INDEX_TIP, THUMB_TIP, PinchTracker, palm_scale, pinch_ratio


MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)
MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "hand_landmarker.task"

CONNECTIONS = (
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20),
)

BG = (28, 28, 28)
WHITE = (245, 245, 245)
MUTED = (185, 185, 185)
YELLOW = (40, 220, 245)
GREEN = (80, 220, 100)
RED = (80, 80, 235)
WINDOW_NAME = "Guane - prueba del sensor"


def ensure_model(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".download")
    print("Descargando el modelo oficial de MediaPipe por unica vez...")
    try:
        urllib.request.urlretrieve(MODEL_URL, temporary)
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def open_camera(index: int, width: int, height: int) -> cv2.VideoCapture:
    backends = [cv2.CAP_ANY]
    if sys.platform == "win32":
        backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]

    for backend in backends:
        capture = cv2.VideoCapture(index, backend)
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        ok = False
        if capture.isOpened():
            for _ in range(3):
                ok, _ = capture.read()
                if ok:
                    break
        if ok:
            try:
                backend_name = capture.getBackendName()
            except cv2.error:
                backend_name = str(backend)
            print(f"Camara {index} abierta con backend {backend_name}.")
            return capture
        capture.release()

    raise RuntimeError(
        f"No se pudo abrir la camara {index}. Pruebe --camera 1 o revise "
        "Configuracion > Privacidad y seguridad > Camara."
    )


def to_pixels(landmarks: list, width: int, height: int) -> list[tuple[int, int]]:
    return [
        (
            int(np.clip(point.x, 0.0, 1.0) * (width - 1)),
            int(np.clip(point.y, 0.0, 1.0) * (height - 1)),
        )
        for point in landmarks
    ]


def draw_hand(frame: np.ndarray, landmarks: list, pinching: bool) -> None:
    height, width = frame.shape[:2]
    points = to_pixels(landmarks, width, height)
    for start, end in CONNECTIONS:
        cv2.line(frame, points[start], points[end], (220, 190, 90), 2, cv2.LINE_AA)
    for point in points:
        cv2.circle(frame, point, 4, WHITE, -1, cv2.LINE_AA)
    color = GREEN if pinching else YELLOW
    cv2.line(frame, points[THUMB_TIP], points[INDEX_TIP], color, 4, cv2.LINE_AA)
    cv2.circle(frame, points[THUMB_TIP], 7, color, -1, cv2.LINE_AA)
    cv2.circle(frame, points[INDEX_TIP], 7, color, -1, cv2.LINE_AA)


def put_text(
    frame: np.ndarray,
    text: str,
    position: tuple[int, int],
    scale: float = 0.65,
    color: tuple[int, int, int] = WHITE,
    thickness: int = 2,
) -> None:
    cv2.putText(
        frame, text, position, cv2.FONT_HERSHEY_SIMPLEX, scale, color,
        thickness, cv2.LINE_AA,
    )


def draw_panel(
    frame: np.ndarray,
    state: str,
    strength: float,
    ratio: float | None,
    handedness: str,
    handedness_score: float,
    fps: float,
    calibration_progress: float,
) -> None:
    height, width = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (width, 132), BG, -1)
    cv2.addWeighted(overlay, 0.78, frame, 0.22, 0, frame)

    state_color = GREEN if state == "PINZA DETECTADA" else YELLOW
    if state == "BUSCANDO MANO":
        state_color = RED
    put_text(frame, state, (22, 35), 0.82, state_color, 2)

    bar_x, bar_y = 22, 58
    bar_width = min(340, width - 44)
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + 20), MUTED, 1)
    fill = int(bar_width * (calibration_progress if state == "ESTABILIZANDO" else strength))
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill, bar_y + 20), state_color, -1)

    ratio_text = "--" if ratio is None else f"{ratio:.2f}"
    put_text(
        frame,
        f"Pinza: {strength * 100:3.0f}%   Ratio: {ratio_text}   "
        f"Lateralidad: {handedness} {handedness_score * 100:3.0f}%   FPS: {fps:4.1f}",
        (22, 106), 0.52, WHITE, 1,
    )
    put_text(frame, "C recalibrar   M espejo   Q salir", (22, height - 18), 0.5, WHITE, 1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prueba local del sensor de pinza")
    parser.add_argument("--camera", type=int, default=0, help="indice de camara")
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--height", type=int, default=540)
    parser.add_argument("--no-mirror", action="store_true")
    return parser.parse_args()


def run() -> int:
    args = parse_args()
    ensure_model(MODEL_PATH)
    capture = open_camera(args.camera, args.width, args.height)
    tracker = PinchTracker()
    fps_samples: deque[float] = deque(maxlen=30)
    mirror = not args.no_mirror
    calibration_started: float | None = None
    calibrated = False
    calibration_seconds = 1.5
    last_time = time.perf_counter()

    options = mp.tasks.vision.HandLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(MODEL_PATH)),
        running_mode=mp.tasks.vision.RunningMode.VIDEO,
        num_hands=1,
        min_hand_detection_confidence=0.55,
        min_hand_presence_confidence=0.55,
        min_tracking_confidence=0.55,
    )

    print("Sensor iniciado. Presione Q o Esc para salir.")
    try:
        with mp.tasks.vision.HandLandmarker.create_from_options(options) as detector:
            started = time.perf_counter()
            while True:
                ok, frame = capture.read()
                if not ok:
                    raise RuntimeError("La camara dejo de entregar imagenes")
                if mirror:
                    frame = cv2.flip(frame, 1)

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                timestamp_ms = int((time.perf_counter() - started) * 1000)
                result = detector.detect_for_video(image, timestamp_ms)

                now = time.perf_counter()
                elapsed = max(now - last_time, 1e-6)
                last_time = now
                fps_samples.append(1.0 / elapsed)
                fps = sum(fps_samples) / len(fps_samples)

                state = "BUSCANDO MANO"
                strength = 0.0
                ratio: float | None = None
                handedness = "--"
                handedness_score = 0.0
                progress = 0.0

                if result.hand_landmarks:
                    landmarks = result.hand_landmarks[0]
                    if result.handedness:
                        category = result.handedness[0][0]
                        handedness_score = category.score
                        handedness = {
                            "Left": "Izq.", "Right": "Der."
                        }.get(category.category_name, category.category_name or "--")
                    # Ignora detecciones demasiado pequenas para que el gesto sea estable.
                    hand_is_large_enough = palm_scale(landmarks) >= 0.055
                    if not hand_is_large_enough:
                        state = "ACERCA LA MANO"
                        calibration_started = None
                        tracker.reset()
                    elif not calibrated:
                        state = "ESTABILIZANDO"
                        if calibration_started is None:
                            calibration_started = now
                        progress = min(1.0, (now - calibration_started) / calibration_seconds)
                        if progress >= 1.0:
                            calibrated = True
                            tracker.reset()
                    else:
                        ratio = pinch_ratio(landmarks)
                        pinching, strength, ratio = tracker.update(ratio)
                        state = "PINZA DETECTADA" if pinching else "MANO ABIERTA"
                    valid_gesture = calibrated and hand_is_large_enough
                    draw_hand(frame, landmarks, tracker.active if valid_gesture else False)
                else:
                    calibration_started = None
                    tracker.reset()

                draw_panel(
                    frame, state, strength, ratio, handedness,
                    handedness_score, fps, progress,
                )
                cv2.imshow(WINDOW_NAME, frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), ord("Q"), 27):
                    break
                if key in (ord("c"), ord("C")):
                    calibrated = False
                    calibration_started = None
                    tracker.reset()
                if key in (ord("m"), ord("M")):
                    mirror = not mirror
                    calibrated = False
                    calibration_started = None
                    tracker.reset()
                try:
                    if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
                        break
                except cv2.error:
                    break
    finally:
        capture.release()
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)

