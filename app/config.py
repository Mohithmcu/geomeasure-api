"""Application configuration module."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings for the Geospatial File Measurement API."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "Geospatial File Measurement API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Base workspace directory
    BASE_DIR: Path = Path(__file__).resolve().parent.parent

    # File storage configuration
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    SAMPLES_DIR: Path = BASE_DIR / "samples"
    MAX_UPLOAD_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB

    # Allowed geospatial file formats
    ALLOWED_EXTENSIONS: set[str] = {".zip", ".kml", ".kmz"}

    # Default fallback CRS when not specified in source file
    DEFAULT_CRS: str = "EPSG:4326"

    # API Prefix
    API_PREFIX: str = "/api"


settings = Settings()

# Ensure uploads directory exists
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
