from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date, time, datetime

# ── Auth ──────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str

# ── Class ─────────────────────────────────────────
class ClassCreate(BaseModel):
    class_name: str
    subject: str

class ClassResponse(BaseModel):
    id: str
    class_name: str
    subject: str
    created_at: Optional[datetime] = None

# ── Student ───────────────────────────────────────
class StudentCreate(BaseModel):
    name:        str
    roll_number: str
    department:  Optional[str] = None   # BCA | B.com | BSc
    year:        Optional[str] = None   # 1st | 2nd | 3rd
    section:     Optional[str] = None   # A | B
    class_:      Optional[str] = None   # maps to "class" column
    email:       Optional[str] = None

    model_config = {"populate_by_name": True}

class StudentResponse(BaseModel):
    id:           str
    name:         str
    roll_number:  str
    department:   Optional[str] = None
    year:         Optional[str] = None
    section:      Optional[str] = None
    class_:       Optional[str] = None
    email:        Optional[str] = None
    face_encoding: Optional[str] = None
    is_active:    bool = True
    created_at:   Optional[datetime] = None

    model_config = {"populate_by_name": True}

class StudentUpdate(BaseModel):
    name:        Optional[str] = None
    roll_number: Optional[str] = None
    department:  Optional[str] = None
    year:        Optional[str] = None
    section:     Optional[str] = None
    class_:      Optional[str] = None
    email:       Optional[str] = None
    is_active:   Optional[bool] = None

# ── Attendance ────────────────────────────────────
class AttendanceCreate(BaseModel):
    student_id: str                       # UUID of the student
    date: Optional[str] = None           # YYYY-MM-DD  (defaults to today)
    time: Optional[str] = None           # HH:MM:SS    (defaults to now)
    status: Optional[str] = "present"
    confidence: Optional[float] = None

class AttendanceResponse(BaseModel):
    id: str
    student_id: str
    date: str
    time: str
    status: str
    confidence: Optional[float] = None
    created_at: Optional[datetime] = None

class FaceRecognitionResult(BaseModel):
    success: bool
    student_id: Optional[str] = None     # UUID
    roll_number: Optional[str] = None
    name: Optional[str] = None
    confidence: Optional[float] = None
    message: str
    already_marked: bool = False

# ── Dashboard ─────────────────────────────────────
class DashboardStats(BaseModel):
    total_students: int
    present_today: int
    absent_today: int
    attendance_rate: float
    recent_attendance: list
