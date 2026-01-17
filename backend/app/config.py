from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    app_env: str = "development"
    port: int = 8000
    
    # Database
    mongodb_uri: str
    
    # JWT
    jwt_secret: str
    jwt_expires_in: int = 3600  # 1 hour in seconds
    
    # CORS
    cors_origins: str = "http://localhost:3000"
    
    # OpenAI
    openai_api_key: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()