"""
Core configuration module.
Load environment variables and provide centralized config.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)


class Settings:
    """Application settings from environment variables."""

    # === Database Configuration ===
    MYSQL_USER: str = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_HOST: str = os.getenv("MYSQL_HOST", "127.0.0.1")
    MYSQL_PORT: int = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "audio_db")

    # Database URL for SQLAlchemy
    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@"
            f"{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
        )

    # === File Upload Configuration ===
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "app/static/uploads")
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "20"))
    MAX_UPLOAD_SIZE_BYTES: int = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    ALLOWED_AUDIO_EXTENSIONS: list = [".wav", ".mp3", ".ogg"]

    # === Search Configuration ===
    TOP_K_RESULTS: int = int(os.getenv("TOP_K_RESULTS", "5"))

    # === Model & Feature Configuration ===
    KDTREE_MODEL_PATH: str = os.getenv(
        "KDTREE_MODEL_PATH", "audio_kdtree.pkl"
    )
    SCALER_MODEL_PATH: str = os.getenv(
        "SCALER_MODEL_PATH", "audio_scaler.pkl"
    )
    NUM_FEATURES: int = 41  # 41 audio features
    SEGMENT_SAVE_ROOT: str = os.getenv("SEGMENT_SAVE_ROOT", "bird_sounds_only")
    ORIGINAL_AUDIO_ROOT: str = os.getenv("ORIGINAL_AUDIO_ROOT", "train_audio")

    # === Audio Processing Configuration ===
    TARGET_SAMPLE_RATE: int = int(os.getenv("TARGET_SAMPLE_RATE", "32000"))
    TOP_DB: float = float(os.getenv("TOP_DB", "30"))
    SEGMENT_WINDOW_SECONDS: float = float(os.getenv("SEGMENT_WINDOW_SECONDS", "2.0"))
    SEGMENT_HOP_SECONDS: float = float(os.getenv("SEGMENT_HOP_SECONDS", "1.0"))
    MIN_SEGMENT_DURATION_SECONDS: float = float(os.getenv("MIN_SEGMENT_DURATION_SECONDS", "1.5"))
    MAX_QUERY_SEGMENTS: int = int(os.getenv("MAX_QUERY_SEGMENTS", "15"))
    MAX_NEIGHBORS_PER_SEGMENT: int = int(os.getenv("MAX_NEIGHBORS_PER_SEGMENT", "20"))
    SEARCH_TOP_N_AGGREGATION: int = int(os.getenv("SEARCH_TOP_N_AGGREGATION", "3"))

    # === API Configuration ===
    API_TITLE: str = "Bird Sound CBIR API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = (
        "REST API for Content-Based Image/Audio Retrieval of bird sounds"
    )

    # === CORS Configuration ===
    CORS_ORIGINS: list = os.getenv(
        "CORS_ORIGINS", "http://localhost:3000,http://localhost:8000"
    ).split(",")

    # === Logging Configuration ===
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    CLEANUP_UPLOADS: bool = os.getenv(
        "CLEANUP_UPLOADS",
        "False"
    ).lower() == "true"


# Global settings instance
settings = Settings()
