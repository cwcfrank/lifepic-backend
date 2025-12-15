"""
Application configuration using pydantic-settings.
Loads environment variables for database and API credentials.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = ""
    
    # TDX API
    tdx_client_id: str = ""
    tdx_client_secret: str = ""
    tdx_auth_url: str = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
    tdx_api_base_url: str = "https://tdx.transportdata.tw/api/basic"
    
    # Sync API
    sync_api_key: str = ""
    
    # App settings
    app_name: str = "ParkRadar Backend API"
    debug: bool = False
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
