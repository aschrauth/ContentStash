from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    app_env: str = "development"
    port: int = 8000
    
    # Database
    mongodb_uri: str
    
    # JWT
    jwt_secret: str
    jwt_expires_in: int = 34560000  # 400 days in seconds
    
    # CORS
    cors_origins: str = "http://localhost:3000"
    
    # Google Gemini
    gemini_api_key: str | None = None
    
    # YouTube Data API v3
    youtube_api_key: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
