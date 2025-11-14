"""
Configuration Management for Smart Billiards AI Referee System
Centralized settings using Pydantic BaseSettings
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # ========== Detection Settings ==========
    DETECTION_CONFIDENCE_THRESHOLD: float = 0.1
    DETECTION_MODEL_PATH: str = "models/yolov8n-ball-v.1.0.0.pt"

    # ========== Movement Detection ==========
    MOVEMENT_THRESHOLD: float = 2.0  # pixels
    STABLE_FRAMES_REQUIRED: int = 5  # consecutive frames below threshold
    MOVEMENT_HISTORY_SIZE: int = 10  # frames to track
    MOVEMENT_TIMEOUT: float = 3.0  # seconds before turn changes

    # ========== Pocket Detection ==========
    POCKET_DISAPPEARANCE_THRESHOLD: int = 10  # frames
    POCKET_STATIC_WINDOW: int = 5  # frames to check for static
    POCKET_STATIC_THRESH: float = 3.0  # max pixels movement

    # ========== Collision Detection ==========
    COLLISION_MOVE_THRESHOLD: float = 0.3  # minimum movement to detect
    COLLISION_CONTACT_MARGIN: float = 10.0  # pixels for contact detection
    COLLISION_CHECK_INTERVAL: int = 10  # frames between checks

    # ========== WebSocket Settings ==========
    WS_PING_INTERVAL: int = 30  # seconds
    WS_TIMEOUT: int = 60  # seconds
    WS_RECONNECT_MAX_ATTEMPTS: int = 10
    WS_RECONNECT_BASE_DELAY: float = 1.0  # seconds
    WS_RECONNECT_MAX_DELAY: float = 30.0  # seconds

    # ========== Video Processing ==========
    MAX_FRAME_BUFFER_SIZE: int = 100  # frames to keep in memory
    TARGET_FPS: int = 30
    DEFAULT_FRAME_SKIP: int = 0  # process every frame by default
    MJPEG_QUALITY: int = 80  # JPEG compression quality

    # ========== Game Logic ==========
    MAX_STATE_SNAPSHOTS: int = 5  # turn snapshots to keep

    # ========== Database Settings ==========
    DATABASE_URL: str = "sqlite:///./backend/data/billiards.db"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_ECHO: bool = False  # SQL logging

    # ========== API Settings ==========
    API_VERSION: str = "v1"
    API_RATE_LIMIT_PER_MINUTE: int = 60
    API_KEY_ENABLED: bool = False
    API_KEY: Optional[str] = None

    # ========== File Storage ==========
    UPLOAD_DIR: str = "uploads"
    OUTPUT_DIR: str = "outputs"
    MODEL_DIR: str = "models"
    MATCH_HISTORY_FILE: str = "backend/data/matches.json"

    # ========== Server Settings ==========
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8001
    BACKEND_GAME_PORT: int = 8001
    CORS_ORIGINS: list = ["*"]

    # ========== Logging Settings ==========
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = None
    LOG_FORMAT: str = "[%(levelname)s] %(message)s"

    # ========== Feature Flags ==========
    ENABLE_CAMERA: bool = True
    ENABLE_VIDEO_UPLOAD: bool = True
    ENABLE_MATCH_HISTORY: bool = True
    ENABLE_DEBUG_LOGGING: bool = False
    ENABLE_METRICS: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings


def update_settings(**kwargs):
    """
    Update settings dynamically

    Args:
        **kwargs: Settings to update
    """
    global settings
    for key, value in kwargs.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
        else:
            raise ValueError(f"Unknown setting: {key}")
