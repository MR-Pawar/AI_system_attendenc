"""
routes/students.py  — Fixed version
 • Better error messages
 • Works even if face_recognition not installed (OpenCV fallback)
 • /register endpoint accepts face_image (single) OR face_images (list)
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from models.schemas import StudentCreate, StudentResponse, StudentUpdate
from services.auth_service import get_current_admin
from services.face_service import (
    extract_face_encoding_multi,
    extract_face_encoding,
    validate_face_quality,
    save_face_image,
    draw_face_box,
    FACE_REC_AVAILABLE,
)
from database import get_db
import json

router = APIRouter()


def _row(row: dict) -> StudentResponse:
    return StudentResponse(
        id=row["id"],
        name=row["name"],
        roll_number=row["roll_number"],
        department=row.get("department"),
        year=row.get("year"),
        section=row.get("section"),
        class_=row.get("class"),
        email=row.get("email"),
        face_encoding=row.get("face_encoding"),
        is_active=row.get("is_active", True),
        created_at=row.get("created_at"),
    )


# ══════════════════════════════════════════════════════
#  REGISTER  (accepts single face_image OR list face_images)
# ══════════════════════════════════════════════════════
@router.post("/register")
async def register_student(payload: dict, admin: str = Depends(get_current_admin)):
    db = get_db()

    name        = (payload.get("name") or "").strip()
    roll_number = (payload.get("roll_number") or "").strip()
    class_name  = (payload.get("class_") or payload.get("class") or "").strip() or None
    email       = (payload.get("email") or "").strip() or None

    # Accept both single image and list
    face_images = payload.get("face_images") or []
    single_img  = payload.get("face_image")
    if single_img and not face_images:
        face_images = [single_img]
    if isinstance(face_images, str):
        face_images = [face_images]

    # Validate required fields
    if not name:
        raise HTTPException(status_code=422, detail="Student name is required")
    if not roll_number:
        raise HTTPException(status_code=422, detail="Roll number is required")

    # Duplicate check
    dup = db.table("students").select("id").eq("roll_number", roll_number).execute()
    if dup.data:
        raise HTTPException(status_code=400, detail=f"Roll number '{roll_number}' already registered")

    # Process face images if provided
    face_encoding_json = None
    enc_stats = {"frames_submitted": 0, "frames_used": 0, "frames_rejected": 0,
                 "encoding_length": 0, "mode": "none"}

    if face_images:
        encoding_list, enc_msg, stats = extract_face_encoding_multi(face_images)
        enc_stats.update({
            "frames_submitted": stats.get("total", len(face_images)),
            "frames_used":      stats.get("used", 0),
            "frames_rejected":  stats.get("rejected", 0),
            "mode":             stats.get("mode", "unknown"),
        })
        if encoding_list is None:
            raise HTTPException(
                status_code=400,
                detail=f"Face encoding failed: {enc_msg}. "
                       f"Frames used: {enc_stats['frames_used']}/{enc_stats['frames_submitted']}. "
                       f"Tip: make sure face is clearly visible in good lighting."
            )
        face_encoding_json = json.dumps(encoding_list)
        enc_stats["encoding_length"] = len(encoding_list)
        save_face_image(roll_number, face_images[0])

    # Insert to Supabase
    try:
        result = db.table("students").insert({
            "name":          name,
            "roll_number":   roll_number,
            "department":    payload.get("department") or None,
            "year":          payload.get("year")       or None,
            "section":       payload.get("section")    or None,
            "class":         class_name,
            "email":         email,
            "face_encoding": face_encoding_json,
        }).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    if not result.data:
        raise HTTPException(status_code=500, detail="Insert failed — no data returned from Supabase")

    return {
        "success":        True,
        "message":        f"'{name}' registered successfully!",
        "student":        _row(result.data[0]),
        "encoding_stats": enc_stats,
        "ai_mode":        "full_ai" if FACE_REC_AVAILABLE else "opencv_fallback",
    }


# ── Face quality check ─────────────────────────────────
@router.post("/check-face-quality")
async def check_quality(payload: dict, admin: str = Depends(get_current_admin)):
    img = payload.get("face_image")
    if not img:
        raise HTTPException(status_code=400, detail="face_image required")
    quality = validate_face_quality(img)
    preview = draw_face_box(img)
    return {
        "quality":        quality,
        "annotated":      preview.get("annotated"),
        "faces_detected": preview.get("faces", 0),
        "ready":          quality["ok"],
    }


# ── Update face ────────────────────────────────────────
@router.post("/{student_id}/update-face")
async def update_face(student_id: str, payload: dict, admin: str = Depends(get_current_admin)):
    db = get_db()
    imgs = payload.get("face_images") or []
    if isinstance(imgs, str): imgs = [imgs]
    if not imgs:
        raise HTTPException(status_code=422, detail="face_images required")
    row = db.table("students").select("roll_number,name").eq("id", student_id).execute()
    if not row.data:
        raise HTTPException(status_code=404, detail="Student not found")
    enc, msg, stats = extract_face_encoding_multi(imgs)
    if enc is None:
        raise HTTPException(status_code=400, detail=f"Encoding failed: {msg}")
    save_face_image(row.data[0]["roll_number"], imgs[0])
    db.table("students").update({"face_encoding": json.dumps(enc)}).eq("id", student_id).execute()
    return {"success": True, "message": "Face updated", "stats": stats}


# ── CRUD ───────────────────────────────────────────────
@router.get("/", response_model=List[StudentResponse])
async def get_all(search: Optional[str]=None, class_name: Optional[str]=None, admin: str=Depends(get_current_admin)):
    db = get_db()
    try:
        rows = db.table("students").select("*").eq("is_active", True).order("name").execute().data or []
        if search:
            s = search.lower()
            rows = [r for r in rows if s in r["name"].lower() or s in r["roll_number"].lower()]
        if class_name:
            rows = [r for r in rows if (r.get("class") or "").lower() == class_name.lower()]
        return [_row(r) for r in rows]
    except Exception as e:
        error_msg = str(e)
        if "getaddrinfo" in error_msg or "ConnectError" in error_msg:
            raise HTTPException(
                status_code=503,
                detail="Database connection error. Check your network and Supabase credentials."
            )
        raise HTTPException(status_code=500, detail=f"Error fetching students: {error_msg}")


@router.get("/{student_id}", response_model=StudentResponse)
async def get_one(student_id: str, admin: str = Depends(get_current_admin)):
    db = get_db()
    try:
        result = db.table("students").select("*").eq("id", student_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Student not found")
        return _row(result.data[0])
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "getaddrinfo" in error_msg or "ConnectError" in error_msg:
            raise HTTPException(status_code=503, detail="Database connection error")
        raise HTTPException(status_code=500, detail=f"Error: {error_msg}")


@router.put("/{student_id}", response_model=StudentResponse)
async def update(student_id: str, update: StudentUpdate, admin: str = Depends(get_current_admin)):
    db = get_db()
    data = {}
    if update.name        is not None: data["name"]        = update.name
    if update.roll_number is not None: data["roll_number"] = update.roll_number
    if update.department  is not None: data["department"]  = update.department
    if update.year        is not None: data["year"]        = update.year
    if update.section     is not None: data["section"]     = update.section
    if update.class_      is not None: data["class"]       = update.class_
    if update.email       is not None: data["email"]       = update.email
    if update.is_active   is not None: data["is_active"]   = update.is_active
    result = db.table("students").update(data).eq("id", student_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Not found")
    return _row(result.data[0])


@router.delete("/{student_id}")
async def delete(student_id: str, admin: str = Depends(get_current_admin)):
    get_db().table("students").update({"is_active": False}).eq("id", student_id).execute()
    return {"message": "Student deactivated"}
