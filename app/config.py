from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # App settings
    app_name: str = "Ask_API"
    debug: bool = False

    # OpenAI settings
    openai_model: str = "gpt-3.5-turbo"
    temperature: float = 0.0

    # API base URL configuration
    api_scheme: str = "http"
    api_host: str = "qa30scl-rws-001:8080/rws"

    # RWS API Basic Auth
    rws_username: Optional[str] = "ma5adm1n"
    rws_password: Optional[str] = "jasper2006"

    # Redis settings
    redis_url: str = "redis://localhost:6379"
    cache_ttl: int = 3600

    # API settings
    assets_path: str = "app/assets"
    api_timeout: int = 30
    max_retries: int = 3

    # CORS
    cors_origins: list = ["*"]

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()