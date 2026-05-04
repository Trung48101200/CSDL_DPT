"""
Pydantic schemas for audio-related API requests and responses.
"""
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class AudioFeatureBase(BaseModel):
    """Base schema for audio feature data."""
    filename: str = Field(..., description="Segmented filename (e.g., XC568398_seg18_m0.wav)")
    original_filename: str = Field(..., description="Original audio filename (e.g., XC568398.ogg)")
    label: str = Field(..., description="Bird species code (e.g., abhori1)")
    duration: Optional[float] = Field(None, description="Audio duration in seconds")
    sample_rate: Optional[int] = Field(None, description="Sample rate in Hz")


class AudioFeatureCreate(AudioFeatureBase):
    """Schema for creating new audio feature record."""
    pass


class AudioFeatureResponse(AudioFeatureBase):
    """Schema for audio feature API response."""
    id: int = Field(..., description="Audio feature ID")
    # All 41 features
    energy_mean: Optional[float] = None
    energy_var: Optional[float] = None
    zcr_mean: Optional[float] = None
    zcr_var: Optional[float] = None
    silence_ratio: Optional[float] = None
    centroid_mean: Optional[float] = None
    centroid_var: Optional[float] = None
    bandwidth_mean: Optional[float] = None
    bandwidth_var: Optional[float] = None
    rolloff_mean: Optional[float] = None
    rolloff_var: Optional[float] = None
    harmonic_mean: Optional[float] = None
    harmonic_var: Optional[float] = None
    pitch_mean: Optional[float] = None
    pitch_var: Optional[float] = None
    mfcc1_mean: Optional[float] = None
    mfcc1_var: Optional[float] = None
    mfcc2_mean: Optional[float] = None
    mfcc2_var: Optional[float] = None
    mfcc3_mean: Optional[float] = None
    mfcc3_var: Optional[float] = None
    mfcc4_mean: Optional[float] = None
    mfcc4_var: Optional[float] = None
    mfcc5_mean: Optional[float] = None
    mfcc5_var: Optional[float] = None
    mfcc6_mean: Optional[float] = None
    mfcc6_var: Optional[float] = None
    mfcc7_mean: Optional[float] = None
    mfcc7_var: Optional[float] = None
    mfcc8_mean: Optional[float] = None
    mfcc8_var: Optional[float] = None
    mfcc9_mean: Optional[float] = None
    mfcc9_var: Optional[float] = None
    mfcc10_mean: Optional[float] = None
    mfcc10_var: Optional[float] = None
    mfcc11_mean: Optional[float] = None
    mfcc11_var: Optional[float] = None
    mfcc12_mean: Optional[float] = None
    mfcc12_var: Optional[float] = None
    mfcc13_mean: Optional[float] = None
    mfcc13_var: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AudioListResponse(BaseModel):
    """Schema for paginated audio features list response."""
    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Items per page")
    total: int = Field(..., description="Total number of items")
    items: List[AudioFeatureResponse] = Field(default_factory=list)


class BirdWikiBase(BaseModel):
    """Base schema for bird wiki details."""
    scientific_name: str = Field(..., description="Scientific name")
    common_name: str = Field(..., description="Common/English name")
    primary_label: str = Field(..., description="Bird species code (e.g., abhori1)")


class BirdWikiResponse(BirdWikiBase):
    """Schema for bird wiki API response."""
    id: int
    summary: Optional[str] = Field(None, description="Wikipedia summary/description")
    order: Optional[str] = Field(None, description="Taxonomic order")
    family: Optional[str] = Field(None, description="Taxonomic family")
    genus: Optional[str] = Field(None, description="Taxonomic genus")
    local_image_path: Optional[str] = Field(None, description="Local path to bird image")
    conservation_status: Optional[str] = Field(None, description="Conservation status")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BirdInfo(BaseModel):
    """Nested bird metadata for search results."""
    common_name: Optional[str] = Field(None, description="Common bird name")
    scientific_name: Optional[str] = Field(None, description="Scientific bird name")
    summary: Optional[str] = Field(None, description="Bird description/summary")
    family: Optional[str] = Field(None, description="Taxonomic family")
    order: Optional[str] = Field(None, description="Taxonomic order")
    genus: Optional[str] = Field(None, description="Taxonomic genus")
    local_image_path: Optional[str] = Field(None, description="Path to bird image")
    conservation_status: Optional[str] = Field(None, description="Conservation status")


class SearchResultItem(BaseModel):
    """Schema for original-file level search result item."""
    rank: int = Field(..., description="Result rank (1-best)")
    original_filename: str = Field(..., description="Original audio filename")
    best_matching_segment: str = Field(..., description="Best-matching target segment filename")
    best_similarity: float = Field(..., description="Best segment similarity score")
    aggregate_score: float = Field(..., description="Aggregated file-level similarity score")
    matched_segments: int = Field(..., description="Number of matched target segments for this original file")
    label: str = Field(..., description="Bird species code")
    bird_info: BirdInfo = Field(..., description="Bird metadata for the matched species")


class SearchResponse(BaseModel):
    """Schema for search result response."""
    success: bool = Field(default=True, description="Operation success status")
    query_file: str = Field(..., description="Uploaded query file name")
    top_k: int = Field(..., description="Number of results returned")
    message: Optional[str] = Field(None, description="Optional informational message")
    processing_time_ms: Optional[float] = Field(
        None, description="Processing time in milliseconds"
    )
    results: List[SearchResultItem] = Field(
        default_factory=list, description="List of search results"
    )


class AudioImportResponse(BaseModel):
    """Schema for import audio response."""
    success: bool = Field(..., description="Operation success status")
    original_filename: str = Field(..., description="Original uploaded filename")
    label: str = Field(..., description="Bird species code")
    segments_created: int = Field(..., description="Number of segments created")
    features_inserted: int = Field(..., description="Number of feature records inserted")
    kdtree_rebuilt: bool = Field(..., description="Whether KDTree was rebuilt successfully")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    message: Optional[str] = Field(None, description="Informational message")


class OriginalAudioResponse(BaseModel):
    """Schema for original audio metadata response."""
    id: int = Field(..., description="Original audio record ID")
    original_filename: str = Field(..., description="Original uploaded filename")
    label: str = Field(..., description="Bird species code")
    file_path: str = Field(..., description="Relative file path to the original audio")
    duration: Optional[float] = Field(None, description="Duration in seconds")
    sample_rate: Optional[int] = Field(None, description="Sample rate in Hz")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OriginalAudioListResponse(BaseModel):
    """Schema for paginated original audio list response."""
    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Items per page")
    total: int = Field(..., description="Total number of items")
    items: List[OriginalAudioResponse] = Field(default_factory=list)


class AudioMetadataUpdateRequest(BaseModel):
    """Schema for audio metadata update request."""
    label: Optional[str] = Field(
        None,
        description="New bird species code to assign to the original file"
    )
    new_original_filename: Optional[str] = Field(
        None,
        description="New original filename to associate with the imported audio"
    )


class AudioUpdateResponse(BaseModel):
    """Schema for audio metadata update response."""
    success: bool = Field(..., description="Operation success status")
    original_filename: str = Field(..., description="Original filename before update")
    updated_records: int = Field(..., description="Number of records updated")
    updated_label: Optional[str] = Field(
        None,
        description="New label value if updated"
    )
    updated_original_filename: Optional[str] = Field(
        None,
        description="New original filename if updated"
    )
    message: Optional[str] = Field(None, description="Informational message")


class AudioDeleteResponse(BaseModel):
    """Schema for original file delete response."""
    success: bool = Field(..., description="Operation success status")
    original_filename: str = Field(..., description="Original filename deleted")
    deleted_audio_records: int = Field(..., description="Number of DB records deleted")
    deleted_original_files: int = Field(..., description="Number of original files deleted")
    deleted_segment_files: int = Field(..., description="Number of segment files deleted")
    kdtree_rebuilt: bool = Field(..., description="Whether KDTree rebuild succeeded")
    message: Optional[str] = Field(None, description="Informational message")


class ErrorResponse(BaseModel):
    """Schema for error responses."""
    success: bool = Field(default=False, description="Operation success status")
    message: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Additional error details")
    error_code: Optional[str] = Field(None, description="Error code for client handling")


class HealthResponse(BaseModel):
    """Schema for health check endpoint."""
    status: str = Field(default="healthy", description="Service status")
    version: str = Field(..., description="API version")
    database: str = Field(..., description="Database connection status")
    models_loaded: bool = Field(..., description="ML models loaded status")
