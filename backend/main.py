from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import auth, students, attendance, dashboard, classes
import uvicorn

# ✅ Only ONE app instance
app = FastAPI(
    title="AI Face Recognition Attendance System",
    version="3.0.0",
    description="Supabase-connected attendance system with face recognition",
)

# ✅ CORS configuration for development and production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        # Local development (common ports)
        "http://localhost:3000",
        "http://localhost:5500",
        "http://localhost:5501",
        "http://localhost:8000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5500",
        "http://127.0.0.1:5501",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8080",
    ],
    allow_origin_regex="http://192\\.168\\..*:.*|http://10\\..*:.*|http://172\\..*:.*",  # Local network IP
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,       prefix="/api/auth",       tags=["Auth"])
app.include_router(students.router,   prefix="/api/students",   tags=["Students"])
app.include_router(attendance.router, prefix="/api/attendance", tags=["Attendance"])
app.include_router(dashboard.router,  prefix="/api/dashboard",  tags=["Dashboard"])
app.include_router(classes.router,    prefix="/api/classes",    tags=["Classes"])

@app.get("/")
def root():
    return {
        "status":  "online",
        "version": "3.0.0",
        "message": "AI Face Attendance API",
        "docs":    "/docs",
    }

@app.get("/api/health")
def health_check():
    """Health check endpoint for frontend to verify backend connectivity."""
    from database import get_db
    try:
        db = get_db()
        # Test connection to Supabase
        result = db.table("classes").select("count", count="exact").execute()
        return {
            "status": "healthy",
            "backend": "running",
            "database": "connected",
            "api_version": "3.0.0",
        }
    except Exception as e:
        return {
            "status": "warning",
            "backend": "running",
            "database": "error",
            "error": str(e),
            "api_version": "3.0.0",
        }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )