"""
routes/dashboard.py  –  Prompt 5
─────────────────────────────────────────────────────
Full admin dashboard API:
  GET /stats            – KPI cards + weekly trend + class breakdown
  GET /students         – paginated student list with filters
  GET /attendance-today – today's attendance with class/status filter
  GET /attendance-history – date range + class + status filter
  GET /export           – CSV-ready export (date range, class, status)
  GET /monthly-report   – per-student monthly summary
"""

from fastapi import APIRouter, Depends, Query
from datetime import date, timedelta
from typing import Optional
from services.auth_service import get_current_admin
from database import get_db

router = APIRouter()


# ══════════════════════════════════════════════════════
#  KPI STATS
# ══════════════════════════════════════════════════════
@router.get("/stats")
async def get_stats(admin: str = Depends(get_current_admin)):
    db    = get_db()
    today = str(date.today())

    total_res   = db.table("students").select("id", count="exact").eq("is_active", True).execute()
    present_res = db.table("attendance").select("id", count="exact").eq("date", today).eq("status", "present").execute()
    late_res    = db.table("attendance").select("id", count="exact").eq("date", today).eq("status", "late").execute()
    absent_res  = db.table("attendance").select("id", count="exact").eq("date", today).eq("status", "absent").execute()
    classes_res = db.table("classes").select("id", count="exact").execute()

    total    = total_res.count    or 0
    present  = (present_res.count or 0) + (late_res.count or 0)
    absent   = max(0, total - present)
    rate     = round((present / total * 100) if total else 0, 1)

    # 7-day trend
    weekly = []
    for i in range(6, -1, -1):
        d   = date.today() - timedelta(days=i)
        cnt = db.table("attendance").select("id", count="exact").eq("date", str(d)).in_("status", ["present","late"]).execute()
        weekly.append({"date": str(d), "day": d.strftime("%a"), "count": cnt.count or 0})

    # Class breakdown
    stu_all = db.table("students").select("class").eq("is_active", True).execute()
    class_map: dict = {}
    for s in (stu_all.data or []):
        c = s.get("class") or "Unassigned"
        class_map[c] = class_map.get(c, 0) + 1

    # Recent attendance (today, last 8)
    recent = db.table("attendance").select(
        "*, students(name, roll_number, class)"
    ).eq("date", today).order("time", desc=True).limit(8).execute()

    return {
        "total_students":  total,
        "present_today":   present,
        "absent_today":    absent,
        "attendance_rate": rate,
        "total_classes":   classes_res.count or 0,
        "weekly_trend":    weekly,
        "class_breakdown": [{"class": k, "total": v} for k, v in sorted(class_map.items())],
        "recent_attendance": recent.data or [],
        "date": today,
    }


# ══════════════════════════════════════════════════════
#  STUDENT LIST  (with filters + pagination)
# ══════════════════════════════════════════════════════
@router.get("/students")
async def get_students(
    search:     Optional[str] = Query(None),
    class_name: Optional[str] = Query(None),
    has_face:   Optional[bool] = Query(None),
    page:       int = Query(1, ge=1),
    per_page:   int = Query(20, ge=1, le=100),
    admin: str = Depends(get_current_admin),
):
    db = get_db()
    result = db.table("students").select("*").eq("is_active", True).order("name").execute()
    students = result.data or []

    # Filters
    if search:
        s = search.lower()
        students = [st for st in students
                    if s in st["name"].lower() or s in st["roll_number"].lower()]
    if class_name:
        students = [st for st in students
                    if (st.get("class") or "").lower() == class_name.lower()]
    if has_face is not None:
        students = [st for st in students
                    if bool(st.get("face_encoding")) == has_face]

    total = len(students)
    start = (page - 1) * per_page
    paged = students[start: start + per_page]

    return {
        "students":   paged,
        "total":      total,
        "page":       page,
        "per_page":   per_page,
        "total_pages": -(-total // per_page),   # ceiling division
    }


# ══════════════════════════════════════════════════════
#  TODAY'S ATTENDANCE  (with class + status filter)
# ══════════════════════════════════════════════════════
@router.get("/attendance-today")
async def get_today(
    class_name: Optional[str] = Query(None),
    status:     Optional[str] = Query(None),
    admin: str = Depends(get_current_admin),
):
    db    = get_db()
    today = str(date.today())

    query = db.table("attendance").select(
        "*, students(name, roll_number, class, email)"
    ).eq("date", today).order("time", desc=True)

    if status:
        query = query.eq("status", status)

    result  = query.execute()
    records = result.data or []

    if class_name:
        records = [r for r in records
                   if (r.get("students") or {}).get("class", "").lower() == class_name.lower()]

    return {"records": records, "total": len(records), "date": today}


# ══════════════════════════════════════════════════════
#  ATTENDANCE HISTORY  (date range + class + status)
# ══════════════════════════════════════════════════════
@router.get("/attendance-history")
async def get_history(
    start_date:  Optional[str] = Query(None),
    end_date:    Optional[str] = Query(None),
    class_name:  Optional[str] = Query(None),
    roll_number: Optional[str] = Query(None),
    status:      Optional[str] = Query(None),
    page:        int = Query(1, ge=1),
    per_page:    int = Query(30, ge=1, le=200),
    admin: str = Depends(get_current_admin),
):
    db    = get_db()
    query = db.table("attendance").select(
        "*, students(name, roll_number, class, email)"
    )
    if start_date:  query = query.gte("date", start_date)
    if end_date:    query = query.lte("date", end_date)
    if status:      query = query.eq("status", status)

    result  = query.order("date", desc=True).order("time", desc=True).execute()
    records = result.data or []

    if class_name:
        records = [r for r in records
                   if (r.get("students") or {}).get("class","").lower() == class_name.lower()]
    if roll_number:
        records = [r for r in records
                   if (r.get("students") or {}).get("roll_number","") == roll_number]

    total = len(records)
    start = (page - 1) * per_page
    paged = records[start: start + per_page]

    return {
        "records":     paged,
        "total":       total,
        "page":        page,
        "per_page":    per_page,
        "total_pages": -(-total // per_page),
    }


# ══════════════════════════════════════════════════════
#  EXPORT  (CSV-ready full data)
# ══════════════════════════════════════════════════════
@router.get("/export")
async def export_report(
    start_date:  Optional[str] = Query(None),
    end_date:    Optional[str] = Query(None),
    class_name:  Optional[str] = Query(None),
    status:      Optional[str] = Query(None),
    admin: str = Depends(get_current_admin),
):
    db    = get_db()
    query = db.table("attendance").select(
        "*, students(name, roll_number, class, email)"
    )
    if start_date: query = query.gte("date", start_date)
    if end_date:   query = query.lte("date", end_date)
    if status:     query = query.eq("status", status)

    result  = query.order("date", desc=True).order("time", desc=True).execute()
    records = result.data or []

    if class_name:
        records = [r for r in records
                   if (r.get("students") or {}).get("class","").lower() == class_name.lower()]

    # Build flat rows for CSV
    rows = []
    for r in records:
        s = r.get("students") or {}
        rows.append({
            "date":        r.get("date",""),
            "time":        r.get("time",""),
            "name":        s.get("name",""),
            "roll_number": s.get("roll_number",""),
            "class":       s.get("class",""),
            "email":       s.get("email",""),
            "status":      r.get("status",""),
            "confidence":  r.get("confidence",""),
        })

    return {"data": rows, "total": len(rows),
            "start_date": start_date, "end_date": end_date}


# ══════════════════════════════════════════════════════
#  MONTHLY REPORT  (per student summary)
# ══════════════════════════════════════════════════════
@router.get("/monthly-report")
async def monthly_report(
    year:  Optional[int] = None,
    month: Optional[int] = None,
    class_name: Optional[str] = None,
    admin: str = Depends(get_current_admin),
):
    from calendar import monthrange
    today = date.today()
    y = year  or today.year
    m = month or today.month
    _, days = monthrange(y, m)
    start = f"{y}-{m:02d}-01"
    end   = f"{y}-{m:02d}-{days}"

    result = db.table("attendance").select(
        "*, students(name, roll_number, class)"
    ).gte("date", start).lte("date", end).execute() if False else \
    get_db().table("attendance").select(
        "*, students(name, roll_number, class)"
    ).gte("date", start).lte("date", end).execute()

    records = result.data or []
    if class_name:
        records = [r for r in records
                   if (r.get("students") or {}).get("class","").lower() == class_name.lower()]

    summary: dict = {}
    for rec in records:
        sid = rec["student_id"]
        s   = rec.get("students") or {}
        if sid not in summary:
            summary[sid] = {
                "student_id":  sid,
                "name":        s.get("name",""),
                "roll_number": s.get("roll_number",""),
                "class":       s.get("class",""),
                "present": 0, "absent": 0, "late": 0,
            }
        st = rec.get("status","present")
        summary[sid][st] = summary[sid].get(st, 0) + 1

    for sid in summary:
        total = summary[sid]["present"] + summary[sid]["absent"] + summary[sid]["late"]
        summary[sid]["percentage"] = round(
            (summary[sid]["present"] + summary[sid]["late"]) / total * 100
            if total else 0, 1
        )

    report = sorted(summary.values(), key=lambda x: x["percentage"], reverse=True)
    return {"year": y, "month": m, "working_days": days,
            "class_filter": class_name, "report": report}
