"""
ORM model for original audio uploads.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Index

from app.core.database import Base


class OriginalAudio(Base):
    """Stores metadata for uploaded original audio files."""
    __tablename__ = "original_audios"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    original_filename = Column(String(255), nullable=False, index=True)
    label = Column(String(50), nullable=False, index=True)
    file_path = Column(String(512), nullable=False)
    duration = Column(Float, nullable=True)
    sample_rate = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('idx_original_audio_label', 'original_filename', 'label'),
    )

    def __repr__(self) -> str:
        return (
            f"OriginalAudio(id={self.id}, original_filename={self.original_filename}, "
            f"label={self.label})"
        )
