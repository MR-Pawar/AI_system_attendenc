from fastapi import APIRouter, HTTPException, status
from models.schemas import LoginRequest, TokenResponse
from services.auth_service import create_access_token, get_password_hash, verify_password
from config import settings
from database import get_db

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Admin login endpoint."""
    db = get_db()

    # Check hardcoded admin or from DB
    is_valid = False

    if request.username == settings.ADMIN_USERNAME and request.password == settings.ADMIN_PASSWORD:
        is_valid = True
    else:
        try:
            result = db.table("admins").select("*").eq("username", request.username).execute()
            if result.data:
                admin = result.data[0]
                is_valid = verify_password(request.password, admin["password_hash"])
        except Exception:
            pass

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token = create_access_token(data={"sub": request.username})
    return TokenResponse(access_token=token, username=request.username)


@router.post("/create-admin")
async def create_admin(request: LoginRequest):
    """Create a new admin account (first-time setup)."""
    db = get_db()
    hashed = get_password_hash(request.password)
    try:
        result = db.table("admins").insert({
            "username": request.username,
            "password_hash": hashed
        }).execute()
        return {"message": "Admin created successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/verify")
async def verify_token_endpoint(token: str):
    """Verify if a token is valid."""
    from services.auth_service import verify_token
    username = verify_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return {"valid": True, "username": username}
