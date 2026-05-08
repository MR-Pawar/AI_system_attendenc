from fastapi import APIRouter, HTTPException, Depends
from typing import List
from models.schemas import ClassCreate, ClassResponse
from services.auth_service import get_current_admin
from database import get_db

router = APIRouter()


# ── INSERT ─────────────────────────────────────────
@router.post("/", response_model=ClassResponse)
async def create_class(payload: ClassCreate, admin: str = Depends(get_current_admin)):
    """Create a new class."""
    db = get_db()
    try:
        result = db.table("classes").insert({
            "class_name": payload.class_name,
            "subject":    payload.subject,
        }).execute()
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create class")
        return ClassResponse(**result.data[0])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── FETCH ALL ──────────────────────────────────────
@router.get("/", response_model=List[ClassResponse])
async def get_all_classes(admin: str = Depends(get_current_admin)):
    """Fetch all classes."""
    db = get_db()
    try:
        result = db.table("classes").select("*").order("class_name").execute()
        return [ClassResponse(**c) for c in (result.data or [])]
    except Exception as e:
        error_msg = str(e)
        if "getaddrinfo" in error_msg or "ConnectError" in error_msg:
            raise HTTPException(
                status_code=503,
                detail="Cannot connect to database. Check your network and Supabase credentials."
            )
        raise HTTPException(status_code=500, detail=f"Error fetching classes: {error_msg}")


# ── FETCH ONE ──────────────────────────────────────
@router.get("/{class_id}", response_model=ClassResponse)
async def get_class(class_id: str, admin: str = Depends(get_current_admin)):
    db = get_db()
    result = db.table("classes").select("*").eq("id", class_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Class not found")
    return ClassResponse(**result.data[0])


# ── UPDATE ─────────────────────────────────────────
@router.put("/{class_id}", response_model=ClassResponse)
async def update_class(class_id: str, payload: ClassCreate, admin: str = Depends(get_current_admin)):
    db = get_db()
    result = db.table("classes").update({
        "class_name": payload.class_name,
        "subject":    payload.subject,
    }).eq("id", class_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Class not found")
    return ClassResponse(**result.data[0])


# ── DELETE ─────────────────────────────────────────
@router.delete("/{class_id}")
async def delete_class(class_id: str, admin: str = Depends(get_current_admin)):
    db = get_db()
    db.table("classes").delete().eq("id", class_id).execute()
    return {"message": "Class deleted successfully"}


# ── STUDENTS IN CLASS ──────────────────────────────
@router.get("/{class_name}/students")
async def get_students_by_class(class_name: str, admin: str = Depends(get_current_admin)):
    """Fetch all active students in a given class."""
    db = get_db()
    result = db.table("students").select("*").eq("class", class_name).eq("is_active", True).execute()
    return result.data or []
