from typing import Optional

from pydantic import field_validator
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

    # Extraction / Playwright
    server_playwright_enabled: bool = True
    playwright_max_concurrency: int = 1
    playwright_metadata_fallback_enabled: bool = False
    playwright_block_heavy_resources: bool = True
    playwright_block_images: bool = False

    @field_validator(
        "server_playwright_enabled",
        "playwright_metadata_fallback_enabled",
        "playwright_block_heavy_resources",
        "playwright_block_images",
        mode="before",
    )
    @classmethod
    def parse_enabled_disabled_booleans(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"enabled", "enable"}:
                return True
            if normalized in {"disabled", "disable"}:
                return False
        return value
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
