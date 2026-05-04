"""
SQLAlchemy ORM models for audio features.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Index
)

from app.core.database import Base


class AudioFeature(Base):
    """
    ORM model for audio feature data.
    Stores extracted audio features from bird sound recordings.
    Schema matches train_metadata_merged_features.csv structure exactly.
    """
    __tablename__ = "audio_features"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # File Information (matches CSV columns)
    filename = Column(String(255), nullable=False, unique=True, index=True)  # XC568398_seg18_m0.wav
    original_filename = Column(String(255), nullable=False, index=True)  # XC568398.ogg
    label = Column(String(50), nullable=False, index=True)  # abhori1, abethr1, etc (bird species code)

    # Audio Metadata
    duration = Column(Float, nullable=True)  # Duration in seconds
    sample_rate = Column(Integer, nullable=True)  # 32000

    # === 41 Audio Features (Extracted with librosa from extract_features.py) ===
    
    # Energy Features (2)
    energy_mean = Column(Float, nullable=True)
    energy_var = Column(Float, nullable=True)
    
    # Zero Crossing Rate (2)
    zcr_mean = Column(Float, nullable=True)
    zcr_var = Column(Float, nullable=True)
    
    # Silence Ratio (1)
    silence_ratio = Column(Float, nullable=True)
    
    # Spectral Centroid (2)
    centroid_mean = Column(Float, nullable=True)
    centroid_var = Column(Float, nullable=True)
    
    # Spectral Bandwidth (2)
    bandwidth_mean = Column(Float, nullable=True)
    bandwidth_var = Column(Float, nullable=True)
    
    # Spectral Rolloff (2)
    rolloff_mean = Column(Float, nullable=True)
    rolloff_var = Column(Float, nullable=True)
    
    # Harmonicity (HPSS) (2)
    harmonic_mean = Column(Float, nullable=True)
    harmonic_var = Column(Float, nullable=True)
    
    # Pitch/F0 (Piptrack) (2)
    pitch_mean = Column(Float, nullable=True)
    pitch_var = Column(Float, nullable=True)
    
    # MFCC Coefficients 1-13 (26: each with mean + var)
    mfcc1_mean = Column(Float, nullable=True)
    mfcc1_var = Column(Float, nullable=True)
    mfcc2_mean = Column(Float, nullable=True)
    mfcc2_var = Column(Float, nullable=True)
    mfcc3_mean = Column(Float, nullable=True)
    mfcc3_var = Column(Float, nullable=True)
    mfcc4_mean = Column(Float, nullable=True)
    mfcc4_var = Column(Float, nullable=True)
    mfcc5_mean = Column(Float, nullable=True)
    mfcc5_var = Column(Float, nullable=True)
    mfcc6_mean = Column(Float, nullable=True)
    mfcc6_var = Column(Float, nullable=True)
    mfcc7_mean = Column(Float, nullable=True)
    mfcc7_var = Column(Float, nullable=True)
    mfcc8_mean = Column(Float, nullable=True)
    mfcc8_var = Column(Float, nullable=True)
    mfcc9_mean = Column(Float, nullable=True)
    mfcc9_var = Column(Float, nullable=True)
    mfcc10_mean = Column(Float, nullable=True)
    mfcc10_var = Column(Float, nullable=True)
    mfcc11_mean = Column(Float, nullable=True)
    mfcc11_var = Column(Float, nullable=True)
    mfcc12_mean = Column(Float, nullable=True)
    mfcc12_var = Column(Float, nullable=True)
    mfcc13_mean = Column(Float, nullable=True)
    mfcc13_var = Column(Float, nullable=True)

    # # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Indexes for performance optimization
    __table_args__ = (
        Index('idx_filename', 'filename'),
        Index('idx_original_filename', 'original_filename'),
        Index('idx_label', 'label'),
        Index('idx_created_at', 'created_at'),
    )

    def __repr__(self) -> str:
        return (
            f"AudioFeature(id={self.id}, filename={self.filename}, "
            f"label={self.label})"
        )
