from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    SUPABASE_URL: str = "https://xuduzaibuefetuvbzgpb.supabase.co"
    SUPABASE_KEY: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh1ZHV6YWlidWVmZXR1dmJ6Z3BiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM4MTM5NTUsImV4cCI6MjA4OTM4OTk1NX0.t_vKegFQy60r6_K2H4z_cDDc3L7Zk68ktJFRActPj_Y"
    SECRET_KEY: str = "your_jwt_secret_key_here_change_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"
    FACE_ENCODINGS_DIR: str = "face_data"
    TOLERANCE: float = 0.5

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
