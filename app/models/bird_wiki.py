"""
SQLAlchemy ORM models for bird wiki details.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, Index, Text
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class BirdWikiDetail(Base):
    """
    ORM model for bird encyclopedia/wiki information.
    Stores taxonomic and descriptive information about bird species.
    Schema matches bird_wikipedia_info_final.csv structure exactly.
    """
    __tablename__ = "bird_wiki_details"

    # Primary Key
    # id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Bird Identification & Link to AudioFeature
    scientific_name = Column(String(255), nullable=False, unique=True, index=True)
    common_name = Column(String(255), nullable=False, index=True)
    primary_label = Column(String(50), primary_key=True, nullable=False, unique=True, index=True)  # Link to audio_features.label

    # Description
    summary = Column(Text, nullable=True)  # Wikipedia summary/description

    # Taxonomic Information
    order = Column(String(100), nullable=True, index=True)
    family = Column(String(100), nullable=True, index=True)
    genus = Column(String(100), nullable=True, index=True)

    # Media & References
    local_image_path = Column(String(500), nullable=True)  # bird_images\afbfly1.jpg
    conservation_status = Column(String(50), nullable=True)  # Least Concern, Near Threatened, etc.

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Indexes for performance
    __table_args__ = (
        Index('idx_scientific_name', 'scientific_name'),
        Index('idx_common_name', 'common_name'),
        Index('idx_primary_label', 'primary_label'),
        Index('idx_family', 'family'),
        Index('idx_created_at', 'created_at'),
    )

    def __repr__(self) -> str:
        return (
            f"BirdWikiDetail(primary_label={self.primary_label}, common_name={self.common_name}, "
            f"scientific_name={self.scientific_name})"
        )
