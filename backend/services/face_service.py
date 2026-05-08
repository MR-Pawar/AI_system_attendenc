"""
face_service.py  — Windows-safe version
────────────────────────────────────────
Gracefully handles missing face_recognition / dlib on Windows.
Falls back to OpenCV-only mode if face_recognition not installed.
"""

import cv2
import numpy as np
import base64
import json
from datetime import datetime
from pathlib import Path
from config import settings

# ── Try importing face_recognition (needs dlib / cmake on Windows) ──────────
try:
    import face_recognition
    FACE_REC_AVAILABLE = True
except ImportError:
    FACE_REC_AVAILABLE = False
    print("⚠️  face_recognition not installed — using OpenCV-only fallback mode")
    print("   To enable full AI recognition, run:")
    print("   pip install cmake dlib face-recognition")

ENCODINGS_DIR = Path(settings.FACE_ENCODINGS_DIR)
ENCODINGS_DIR.mkdir(exist_ok=True)


# ── Image helpers ────────────────────────────────────────────────────────────

def _b64_to_bgr(b64: str) -> np.ndarray | None:
    if "," in b64:
        b64 = b64.split(",")[1]
    try:
        buf = base64.b64decode(b64)
        arr = np.frombuffer(buf, dtype=np.uint8)
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)
    except Exception:
        return None


def _bgr_to_b64(img: np.ndarray, quality: int = 85) -> str:
    _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return base64.b64encode(buf).decode("utf-8")


# ── OpenCV-only face detector (Haar cascade fallback) ───────────────────────

def _cv2_detect_faces(img_bgr: np.ndarray) -> list:
    """Detect face rectangles using OpenCV Haar cascade (no dlib needed)."""
    gray     = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    cascade  = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces    = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
    return faces.tolist() if len(faces) > 0 else []


def _cv2_simple_encoding(img_bgr: np.ndarray, face_rect) -> list:
    """
    Lightweight 128-value pseudo-encoding using pixel histograms.
    NOT suitable for real recognition — used only when face_recognition
    library is unavailable (Windows fallback).
    """
    x, y, w, h = face_rect
    face_crop   = img_bgr[y:y+h, x:x+w]
    face_resized = cv2.resize(face_crop, (64, 64))
    gray         = cv2.cvtColor(face_resized, cv2.COLOR_BGR2GRAY)

    # 128-bin histogram as pseudo-encoding
    hist = cv2.calcHist([gray], [0], None, [128], [0, 256])
    cv2.normalize(hist, hist)
    return hist.flatten().tolist()


# ── Quality validation ────────────────────────────────────────────────────────

def validate_face_quality(b64: str) -> dict:
    img = _b64_to_bgr(b64)
    if img is None:
        return {"ok": False, "issues": ["Could not decode image"], "faces": 0}

    h, w  = img.shape[:2]
    gray  = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    brightness = float(np.mean(gray))
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    issues = []

    if brightness < 40:  issues.append("Too dark — improve lighting")
    elif brightness > 220: issues.append("Too bright / overexposed")
    if blur_score < 60:  issues.append("Too blurry — hold camera steady")

    # Detect faces (use whichever library is available)
    if FACE_REC_AVAILABLE:
        rgb  = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        locs = face_recognition.face_locations(rgb, model="hog")
        faces = len(locs)
        face_ratio = 0
        if locs:
            top, right, bottom, left = locs[0]
            face_ratio = round(((right-left)*(bottom-top)) / (w*h) * 100, 1)
    else:
        rects = _cv2_detect_faces(img)
        faces = len(rects)
        face_ratio = 0
        if rects:
            x, y, fw, fh = rects[0]
            face_ratio = round((fw * fh) / (w * h) * 100, 1)

    if faces == 0:   issues.append("No face detected — position face in oval")
    elif faces > 1:  issues.append("Multiple faces — only one person please")
    elif face_ratio < 5:  issues.append("Face too small — move closer")
    elif face_ratio > 85: issues.append("Face too close — move back")

    return {
        "ok":         len(issues) == 0,
        "issues":     issues,
        "brightness": round(brightness, 1),
        "blur":       round(blur_score, 1),
        "faces":      faces,
        "face_ratio": face_ratio,
        "mode":       "full_ai" if FACE_REC_AVAILABLE else "opencv_fallback",
    }


# ── Single encoding ───────────────────────────────────────────────────────────

def extract_face_encoding(b64: str) -> tuple:
    img = _b64_to_bgr(b64)
    if img is None:
        return None, "Could not decode image"

    if FACE_REC_AVAILABLE:
        rgb  = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        locs = face_recognition.face_locations(rgb, model="hog")
        if not locs:   return None, "No face detected"
        if len(locs) > 1: return None, "Multiple faces — capture one face only"
        encs = face_recognition.face_encodings(rgb, locs)
        if not encs:   return None, "Could not generate encoding"
        return encs[0].tolist(), "Success"
    else:
        rects = _cv2_detect_faces(img)
        if not rects:      return None, "No face detected (OpenCV mode)"
        if len(rects) > 1: return None, "Multiple faces detected"
        enc = _cv2_simple_encoding(img, rects[0])
        return enc, "Success (OpenCV fallback mode)"


# ── Multi-sample averaged encoding ───────────────────────────────────────────

def extract_face_encoding_multi(images: list) -> tuple:
    if not images:
        return None, "No images provided", {}

    good, rejected = [], 0

    for b64 in images:
        img = _b64_to_bgr(b64)
        if img is None:
            rejected += 1
            continue

        if FACE_REC_AVAILABLE:
            rgb  = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            locs = face_recognition.face_locations(rgb, model="hog")
            if len(locs) != 1:
                rejected += 1
                continue
            encs = face_recognition.face_encodings(rgb, locs)
            if not encs:
                rejected += 1
                continue
            good.append(np.array(encs[0]))
        else:
            rects = _cv2_detect_faces(img)
            if len(rects) != 1:
                rejected += 1
                continue
            enc = _cv2_simple_encoding(img, rects[0])
            good.append(np.array(enc))

    if not good:
        return None, "No valid face found in any frame", {
            "total": len(images), "used": 0, "rejected": rejected
        }

    avg = np.mean(good, axis=0)
    stats = {
        "total":    len(images),
        "used":     len(good),
        "rejected": rejected,
        "consistency": 0.0,
        "mode": "full_ai" if FACE_REC_AVAILABLE else "opencv_fallback",
    }
    return avg.tolist(), "Success", stats


# ── Save face image to disk ───────────────────────────────────────────────────

def save_face_image(roll: str, b64: str) -> str:
    d = ENCODINGS_DIR / roll
    d.mkdir(parents=True, exist_ok=True)
    img = _b64_to_bgr(b64)
    if img is None:
        return ""
    path = d / f"face_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    cv2.imwrite(str(path), img)
    return str(path)


# ── Draw face boxes (live preview) ────────────────────────────────────────────

def draw_face_box(b64: str) -> dict:
    img = _b64_to_bgr(b64)
    if img is None:
        return {"faces": 0, "annotated": None, "ready": False}

    out = img.copy()

    if FACE_REC_AVAILABLE:
        rgb  = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        locs = face_recognition.face_locations(rgb, model="hog")
        ready = len(locs) == 1
        for top, right, bottom, left in locs:
            color = (0, 200, 80) if ready else (0, 120, 255)
            cv2.rectangle(out, (left, top), (right, bottom), color, 2)
            cv2.putText(out, "Ready" if ready else "Adjust", (left, top-8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
        faces = len(locs)
    else:
        rects = _cv2_detect_faces(img)
        ready = len(rects) == 1
        for (x, y, w, h) in rects:
            color = (0, 200, 80) if ready else (0, 120, 255)
            cv2.rectangle(out, (x, y), (x+w, y+h), color, 2)
            cv2.putText(out, "Ready" if ready else "Adjust", (x, y-8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
        faces = len(rects)

    return {
        "faces":     faces,
        "annotated": _bgr_to_b64(out),
        "ready":     ready,
    }


# ── Attendance face recognition ───────────────────────────────────────────────

def recognize_face(b64: str, known_encodings: list) -> dict:
    img = _b64_to_bgr(b64)
    if img is None:
        return {"success": False, "message": "Could not decode image"}

    if FACE_REC_AVAILABLE:
        rgb  = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        locs = face_recognition.face_locations(rgb, model="hog")
        if not locs:
            return {"success": False, "message": "No face detected"}
        encs = face_recognition.face_encodings(rgb, locs)
        if not encs:
            return {"success": False, "message": "Could not encode face"}
        unknown = encs[0]
    else:
        rects = _cv2_detect_faces(img)
        if not rects:
            return {"success": False, "message": "No face detected"}
        unknown = np.array(_cv2_simple_encoding(img, rects[0]))

    best, best_dist = None, 1.0
    for k in known_encodings:
        known_vec = np.array(k["encoding"])
        if FACE_REC_AVAILABLE:
            dist = face_recognition.face_distance([known_vec], unknown)[0]
        else:
            # Cosine distance fallback
            norm_u = np.linalg.norm(unknown)
            norm_k = np.linalg.norm(known_vec)
            if norm_u > 0 and norm_k > 0:
                dist = 1.0 - float(np.dot(unknown, known_vec) / (norm_u * norm_k))
            else:
                dist = 1.0

        if dist < best_dist:
            best_dist = dist
            best = k

    tol = settings.TOLERANCE
    if best and best_dist <= tol:
        confidence = round((1 - best_dist) * 100, 2)
        return {
            "success":     True,
            "student_id":  best["student_id"],
            "roll_number": best.get("roll_number", ""),
            "name":        best["name"],
            "confidence":  confidence,
            "message":     f"Recognized with {confidence}% confidence",
        }
    return {"success": False, "message": "Face not recognized — please register first"}


def detect_faces_in_frame(b64: str) -> dict:
    return draw_face_box(b64)
