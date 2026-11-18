import os
from typing import Dict, List


class FaceTrackerService:
    """
    Uses OpenCV Haar cascades to detect the speaker's face across sampled frames
    of a clip and compute a smoothed crop center (x_ratio, y_ratio) in [0, 1].
    """

    @staticmethod
    def is_available() -> bool:
        try:
            import cv2  # noqa: F401
            return True
        except Exception:
            return False

    @classmethod
    def track_speaker_center(
        cls,
        video_path: str,
        start_time: float,
        end_time: float,
        max_samples: int = 8,
    ) -> Dict:
        default_result = {
            "detected": False,
            "center_x_ratio": 0.5,
            "center_y_ratio": 0.42,
            "samples_checked": 0,
            "faces_found": 0,
        }

        if not os.path.exists(video_path):
            return default_result

        try:
            import cv2
        except Exception:
            return default_result

        cascade_path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
        alt_cascade_path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_alt2.xml")
        detector = cv2.CascadeClassifier(cascade_path)
        if detector.empty() and os.path.exists(alt_cascade_path):
            detector = cv2.CascadeClassifier(alt_cascade_path)
        if detector.empty():
            return default_result

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return default_result

        try:
            span = max(0.5, float(end_time) - float(start_time))
            sample_count = min(max_samples, max(3, int(span / 4) + 2))
            step_sec = span / max(1, sample_count)

            xs: List[float] = []
            ys: List[float] = []
            ws: List[float] = []
            hs: List[float] = []
            checked = 0

            for i in range(sample_count):
                t_sec = float(start_time) + (i + 0.5) * step_sec
                cap.set(cv2.CAP_PROP_POS_MSEC, t_sec * 1000.0)
                ok, frame = cap.read()
                if not ok or frame is None:
                    continue
                checked += 1

                h, w = frame.shape[:2]
                if w <= 0 or h <= 0:
                    continue

                # Downscale to 320px max side for fast Haar detection
                scale = 320.0 / max(w, h)
                if scale < 1.0:
                    small = cv2.resize(frame, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
                else:
                    small = frame

                gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
                faces = detector.detectMultiScale(
                    gray,
                    scaleFactor=1.2,
                    minNeighbors=4,
                    minSize=(24, 24),
                )
                if len(faces) > 0:
                    fx, fy, fw, fh = max(faces, key=lambda b: b[2] * b[3])
                    cx = (fx + fw / 2.0) / small.shape[1]
                    cy = (fy + fh / 2.0) / small.shape[0]
                    xs.append(float(cx))
                    ys.append(float(cy))
                    ws.append(float(fw / small.shape[1]))
                    hs.append(float(fh / small.shape[0]))

            if not xs:
                return {**default_result, "samples_checked": checked}

            xs_sorted = sorted(xs)
            ys_sorted = sorted(ys)
            ws_sorted = sorted(ws)
            hs_sorted = sorted(hs)
            mid = len(xs_sorted) // 2

            center_x = max(0.08, min(0.92, xs_sorted[mid]))
            center_y = max(0.08, min(0.92, ys_sorted[mid]))
            box_w = max(0.08, min(0.60, ws_sorted[mid]))
            box_h = max(0.08, min(0.60, hs_sorted[mid]))

            # Corner webcam check: face is located in a typical streamer corner box
            is_corner_cam = (
                (center_x < 0.38 or center_x > 0.62)
                and (center_y < 0.40 or center_y > 0.60)
            ) or (box_w < 0.32 and (center_x < 0.40 or center_x > 0.60))

            return {
                "detected": True,
                "center_x_ratio": round(center_x, 4),
                "center_y_ratio": round(center_y, 4),
                "box_w_ratio": round(box_w, 4),
                "box_h_ratio": round(box_h, 4),
                "is_corner_cam": bool(is_corner_cam),
                "samples_checked": checked,
                "faces_found": len(xs),
            }
        finally:
            cap.release()
