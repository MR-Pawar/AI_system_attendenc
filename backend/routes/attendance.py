"""
routes/attendance.py  –  Prompt 4
──────────────────────────────────────────────────────────
Real-time face recognition attendance system.

New in Prompt 4:
  /recognize         – core: detect → compare → mark (duplicate-safe)
  /session/start     – open a live session, cache encodings in memory
  /session/stop      – close session, return summary
  /session/status    – current session info
  /session/log       – all marks in this session
  /today             – today's full list
  /history           – filtered history
  /manual            – manual mark
  /export            – CSV export data
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from datetime import date, datetime, timedelta
import json, time

from models.schemas import FaceRecognitionResult
from services.auth_service import get_current_admin
from services.face_service import recognize_face, draw_face_box
from database import get_db

router = APIRouter()

# ── In-memory session state (per process) ─────────────
_session = {
    "active":    False,
    "id":        None,
    "started_at": None,
    "encodings": [],       # cached from DB at session start
    "log":       [],       # marks made this session
    "frames_processed": 0,
    "faces_detected": 0,
}


# ═══════════════════════════════════════════════════════
#  SESSION MANAGEMENT
# ═══════════════════════════════════════════════════════

def _load_encodings_from_db(db) -> list:
    """Pull all active student encodings from Supabase."""
    try:
        result = db.table("students").select(
            "id, name, roll_number, class, face_encoding"
        ).eq("is_active", True).execute()

        encodings = []
        for s in (result.data or []):
            raw = s.get("face_encoding")
            if raw:
                try:
                    encodings.append({
                        "student_id":  s["id"],
                        "roll_number": s["roll_number"],
                        "name":        s["name"],
                        "class":       s.get("class") or "",
                        "encoding":    json.loads(raw),
                    })
                except Exception:
                    pass
        return encodings
    except Exception as e:
        error_msg = str(e)
        if "getaddrinfo" in error_msg or "ConnectError" in error_msg:
            raise HTTPException(
                status_code=503,
                detail="Cannot connect to database. Check network and Supabase credentials."
            )
        raise HTTPException(status_code=500, detail=f"Database error: {error_msg}")


@router.post("/session/start")
async def start_session(admin: str = Depends(get_current_admin)):
    """
    Start a recognition session.
    Preloads all face encodings from Supabase into memory
    so every frame doesn't hit the database.
    """
    db = get_db()
    encodings = _load_encodings_from_db(db)

    if not encodings:
        raise HTTPException(
            status_code=400,
            detail="No registered students with face encodings found. "
                   "Please register students first."
        )

    sid = f"session_{int(time.time())}"
    _session.update({
        "active":    True,
        "id":        sid,
        "started_at": datetime.now().isoformat(),
        "encodings": encodings,
        "log":       [],
        "frames_processed": 0,
        "faces_detected":   0,
    })

    return {
        "success":          True,
        "session_id":       sid,
        "started_at":       _session["started_at"],
        "students_loaded":  len(encodings),
        "message":          f"Session started – {len(encodings)} student(s) loaded",
    }


@router.post("/session/stop")
async def stop_session(admin: str = Depends(get_current_admin)):
    if not _session["active"]:
        return {"message": "No active session"}

    summary = {
        "session_id":        _session["id"],
        "started_at":        _session["started_at"],
        "ended_at":          datetime.now().isoformat(),
        "frames_processed":  _session["frames_processed"],
        "faces_detected":    _session["faces_detected"],
        "students_marked":   len(_session["log"]),
        "log":               _session["log"],
    }
    _session.update({"active": False, "encodings": [], "log": [],
                     "frames_processed": 0, "faces_detected": 0})
    return summary


@router.get("/session/status")
async def session_status(admin: str = Depends(get_current_admin)):
    return {
        "active":           _session["active"],
        "session_id":       _session["id"],
        "started_at":       _session["started_at"],
        "students_loaded":  len(_session["encodings"]),
        "frames_processed": _session["frames_processed"],
        "faces_detected":   _session["faces_detected"],
        "marks_this_session": len(_session["log"]),
    }


@router.get("/session/log")
async def session_log(admin: str = Depends(get_current_admin)):
    return {"log": _session["log"], "total": len(_session["log"])}


# ═══════════════════════════════════════════════════════
#  CORE: RECOGNIZE + MARK  (called per frame from frontend)
# ═══════════════════════════════════════════════════════

@router.post("/recognize", response_model=FaceRecognitionResult)
async def recognize_and_mark(
    payload: dict,
    admin: str = Depends(get_current_admin),
):
    """
    Process one video frame:
      1. Run face_recognition against cached encodings
      2. If match found → check for duplicate on today's date
      3. If not duplicate  → INSERT attendance row to Supabase
      4. Return structured result for the UI
    """
    db = get_db()
    face_image = payload.get("face_image")
    if not face_image:
        raise HTTPException(status_code=400, detail="face_image is required")

    # Use session-cached encodings if session is active, else load fresh
    if _session["active"] and _session["encodings"]:
        known = _session["encodings"]
        _session["frames_processed"] += 1
    else:
        known = _load_encodings_from_db(db)

    if not known:
        return FaceRecognitionResult(
            success=False,
            message="No registered faces found – register students first"
        )

    # ── Face recognition ─────────────────────────────
    result = recognize_face(face_image, known)

    if _session["active"] and result.get("success"):
        _session["faces_detected"] += 1

    if not result["success"]:
        return FaceRecognitionResult(success=False, message=result["message"])

    student_uuid = result["student_id"]
    today        = str(date.today())
    now          = datetime.now()

    # ── Duplicate check (same student, same day) ─────
    dup = db.table("attendance").select("id, time").eq(
        "student_id", student_uuid
    ).eq("date", today).execute()

    if dup.data:
        marked_time = dup.data[0].get("time", "")
        return FaceRecognitionResult(
            success=True,
            student_id=student_uuid,
            roll_number=result.get("roll_number"),
            name=result["name"],
            confidence=result["confidence"],
            message=f"Already marked at {marked_time[:5]}",
            already_marked=True,
        )

    # ── Insert new attendance record ─────────────────
    db.table("attendance").insert({
        "student_id": student_uuid,
        "date":       today,
        "time":       now.strftime("%H:%M:%S"),
        "status":     "present",
        "confidence": result["confidence"],
    }).execute()

    # ── Update session log ───────────────────────────
    log_entry = {
        "student_id":  student_uuid,
        "roll_number": result.get("roll_number"),
        "name":        result["name"],
        "confidence":  result["confidence"],
        "time":        now.strftime("%H:%M:%S"),
        "class":       result.get("class", ""),
    }
    if _session["active"]:
        # Avoid duplicates in session log too
        existing_ids = [e["student_id"] for e in _session["log"]]
        if student_uuid not in existing_ids:
            _session["log"].append(log_entry)

    return FaceRecognitionResult(
        success=True,
        student_id=student_uuid,
        roll_number=result.get("roll_number"),
        name=result["name"],
        confidence=result["confidence"],
        message=f"✅ Attendance marked for {result['name']}",
        already_marked=False,
    )


# ═══════════════════════════════════════════════════════
#  LIVE PREVIEW  (face detection without marking)
# ═══════════════════════════════════════════════════════

@router.post("/detect-face")
async def detect_face_preview(
    payload: dict,
    admin: str = Depends(get_current_admin),
):
    """
    Detect & annotate faces without marking attendance.
    Used by the idle preview / scan animation.
    """
    face_image = payload.get("face_image")
    if not face_image:
        raise HTTPException(status_code=400, detail="face_image is required")
    return draw_face_box(face_image)


# ═══════════════════════════════════════════════════════
#  TODAY / HISTORY / MANUAL / EXPORT
# ═══════════════════════════════════════════════════════

@router.get("/today")
async def get_today_attendance(admin: str = Depends(get_current_admin)):
    db = get_db()
    try:
        res = db.table("attendance").select(
            "*, students(name, roll_number, class, email)"
        ).eq("date", str(date.today())).order("time", desc=True).execute()
        return res.data or []
    except Exception as e:
        error_msg = str(e)
        if "getaddrinfo" in error_msg or "ConnectError" in error_msg:
            raise HTTPException(
                status_code=503,
                detail="Cannot connect to database. Check your network and Supabase credentials."
            )
        raise HTTPException(status_code=500, detail=f"Error fetching attendance: {error_msg}")


@router.get("/history")
async def get_history(
    start_date:  Optional[str] = None,
    end_date:    Optional[str] = None,
    student_id:  Optional[str] = None,
    roll_number: Optional[str] = None,
    class_name:  Optional[str] = None,
    status:      Optional[str] = None,
    admin: str = Depends(get_current_admin),
):
    db    = get_db()
    query = db.table("attendance").select(
        "*, students(name, roll_number, class, email)"
    )
    if start_date:  query = query.gte("date", start_date)
    if end_date:    query = query.lte("date", end_date)
    if student_id:  query = query.eq("student_id", student_id)
    if status:      query = query.eq("status", status)

    result  = query.order("date", desc=True).order("time", desc=True).execute()
    records = result.data or []

    if roll_number:
        records = [r for r in records
                   if r.get("students", {}).get("roll_number") == roll_number]
    if class_name:
        records = [r for r in records
                   if (r.get("students", {}).get("class") or "").lower()
                      == class_name.lower()]
    return records


@router.post("/manual")
async def mark_manual(
    payload: dict,
    admin: str = Depends(get_current_admin),
):
    db         = get_db()
    identifier = payload.get("student_id") or payload.get("roll_number")
    if not identifier:
        raise HTTPException(
            status_code=400,
            detail="Provide student_id (UUID) or roll_number"
        )

    att_date = payload.get("date",   str(date.today()))
    att_time = payload.get("time",   datetime.now().strftime("%H:%M:%S"))
    status   = payload.get("status", "present")

    # Resolve to UUID
    if len(identifier) > 30 and "-" in identifier:
        student_uuid = identifier
    else:
        row = db.table("students").select("id").eq(
            "roll_number", identifier
        ).execute()
        if not row.data:
            raise HTTPException(status_code=404, detail="Student not found")
        student_uuid = row.data[0]["id"]

    dup = db.table("attendance").select("id").eq(
        "student_id", student_uuid
    ).eq("date", att_date).execute()

    if dup.data:
        db.table("attendance").update({"status": status}).eq(
            "student_id", student_uuid
        ).eq("date", att_date).execute()
        return {"message": "Attendance updated", "student_id": student_uuid}

    db.table("attendance").insert({
        "student_id": student_uuid,
        "date":       att_date,
        "time":       att_time,
        "status":     status,
    }).execute()
    return {"message": "Attendance marked", "student_id": student_uuid}


@router.get("/export")
async def export_attendance(
    start_date: Optional[str] = None,
    end_date:   Optional[str] = None,
    admin: str = Depends(get_current_admin),
):
    db    = get_db()
    query = db.table("attendance").select(
        "*, students(name, roll_number, class, email)"
    )
    if start_date: query = query.gte("date", start_date)
    if end_date:   query = query.lte("date", end_date)
    result = query.order("date", desc=True).execute()
    return {"data": result.data or [], "total": len(result.data or [])}


@router.get("/student/{student_id}")
async def get_student_attendance(
    student_id: str,
    start_date: Optional[str] = None,
    end_date:   Optional[str] = None,
    admin: str = Depends(get_current_admin),
):
    db    = get_db()
    query = db.table("attendance").select("*").eq("student_id", student_id)
    if start_date: query = query.gte("date", start_date)
    if end_date:   query = query.lte("date", end_date)
    result = query.order("date", desc=True).execute()
    return result.data or []
