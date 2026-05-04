"""
API routers for audio and search endpoints.
"""
import logging
import time
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Query, Form, HTTPException, status
import aiofiles
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.schemas.audio import (
    AudioListResponse,
    AudioFeatureResponse,
    SearchResponse,
    ErrorResponse,
    AudioImportResponse,
    OriginalAudioListResponse,
    OriginalAudioResponse,
    AudioMetadataUpdateRequest,
    AudioUpdateResponse,
    AudioDeleteResponse
)
from app.repositories.audio_repository import AudioRepository, BirdWikiRepository, OriginalAudioRepository
from app.services.search_service import SearchService
from app.services.audio_import_service import AudioImportService
from app.services.audio_management_service import AudioManagementService
from app.utils.file_utils import FileValidator, FileManager

logger = logging.getLogger(__name__)

# Create routers
audio_router = APIRouter(prefix="/api/audio", tags=["Audio"])
search_router = APIRouter(prefix="/api/search", tags=["Search"])
import_router = APIRouter(prefix="/api", tags=["Import"])


# ============================================================================
# AUDIO ENDPOINTS
# ============================================================================

@audio_router.get(
    "",
    response_model=AudioListResponse,
    summary="List audio features",
    description="Get paginated list of audio features with filtering and sorting"
)
async def list_audio(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    label: Optional[str] = Query(None, description="Filter by bird species code (e.g., abhori1)"),
    filename: Optional[str] = Query(None, description="Filter by segmented filename"),
    original_filename: Optional[str] = Query(None, description="Filter by original filename"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    search: Optional[str] = Query(None, description="Search keyword"),
    db: Session = Depends(get_db)
):
    """
    Get paginated list of audio features.
    
    Parameters:
    - **page**: Page number (default: 1)
    - **limit**: Items per page (default: 10, max: 100)
    - **label**: Filter by bird species code (e.g., abhori1)
    - **filename**: Filter by segmented filename
    - **original_filename**: Filter by original filename
    - **sort_by**: Sort field (created_at, label, filename)
    - **sort_order**: Sort direction (asc or desc)
    - **search**: Search keyword in filename, original_filename, label
    """
    try:
        items, total = AudioRepository.list_paginated(
            db=db,
            page=page,
            limit=limit,
            label=label,
            filename=filename,
            original_filename=original_filename,
            sort_by=sort_by,
            sort_order=sort_order,
            search_keyword=search
        )

        return AudioListResponse(
            page=page,
            limit=limit,
            total=total,
            items=[AudioFeatureResponse.from_orm(item) for item in items]
        )

    except Exception as e:
        logger.error(f"Error listing audio: {str(e)}")
        raise


@audio_router.get(
    "/originals",
    response_model=OriginalAudioListResponse,
    summary="List original audio records",
    description="Get paginated list of stored original audio files"
)
async def list_original_audio(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    label: Optional[str] = Query(None, description="Filter by bird species code"),
    original_filename: Optional[str] = Query(None, description="Filter by original filename"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    search: Optional[str] = Query(None, description="Search keyword"),
    db: Session = Depends(get_db)
):
    try:
        items, total = OriginalAudioRepository.list_paginated(
            db=db,
            page=page,
            limit=limit,
            label=label,
            original_filename=original_filename,
            sort_by=sort_by,
            sort_order=sort_order,
            search_keyword=search
        )
        return OriginalAudioListResponse(
            page=page,
            limit=limit,
            total=total,
            items=[OriginalAudioResponse.from_orm(item) for item in items]
        )

    except Exception as e:
        logger.error(f"Error listing original audio: {str(e)}")
        raise


@audio_router.get(
    "/originals/{original_id}",
    response_model=OriginalAudioResponse,
    summary="Get original audio by ID",
    description="Get stored original audio metadata by original audio record ID"
)
async def get_original_audio(original_id: int, db: Session = Depends(get_db)):
    try:
        original = OriginalAudioRepository.get_by_id(db, original_id)
        if not original:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "message": f"Original audio with ID {original_id} not found",
                    "error_code": "ORIGINAL_AUDIO_NOT_FOUND"
                }
            )
        return OriginalAudioResponse.from_orm(original)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving original audio {original_id}: {str(e)}")
        raise


@audio_router.get(
    "/{audio_id}",
    response_model=AudioFeatureResponse,
    summary="Get audio feature by ID",
    description="Get detailed audio feature information by ID"
)
async def get_audio(audio_id: int, db: Session = Depends(get_db)):
    """Get audio feature record by ID."""
    try:
        audio = AudioRepository.get_by_id(db, audio_id)
        if not audio:
            return {
                "success": False,
                "message": f"Audio with ID {audio_id} not found",
                "detail": None,
                "error_code": "AUDIO_NOT_FOUND"
            }

        return AudioFeatureResponse.from_orm(audio)

    except Exception as e:
        logger.error(f"Error retrieving audio {audio_id}: {str(e)}")
        raise


@import_router.post(
    "/import",
    response_model=AudioImportResponse,
    summary="Import a new bird audio file",
    description=(
        "Upload an audio file to segment, extract features, insert into the database, "
        "and rebuild the KDTree so new audio is searchable immediately."
    )
)
async def import_audio(
    file: UploadFile = File(
        ..., 
        description="Audio file (.wav, .mp3, or .ogg)",
        media_type="audio/wav,audio/mpeg,audio/ogg"
    ),
    label: str = Form(..., description="Bird species code for the uploaded audio"),
    original_filename: Optional[str] = Form(None, description="Original filename provided by the user"),
    db: Session = Depends(get_db)
):
    """Import a new audio file into the CBIR database."""
    start_time = time.time()

    try:
        file_content = await file.read()
        file_size = len(file_content)

        is_valid, error_msg = FileValidator.validate_file(file.filename, file_size)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "success": False,
                    "message": error_msg,
                    "error_code": "INVALID_FILE"
                }
            )

        if not original_filename:
            original_filename = file.filename

        result = AudioImportService.import_audio_file(
            file_content,
            file.filename,
            label,
            original_filename,
            db
        )

        result["processing_time_ms"] = (time.time() - start_time) * 1000
        return result

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Import error: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "message": "Audio import failed",
                "detail": str(exc),
                "error_code": "IMPORT_FAILED"
            }
        )


@audio_router.patch(
    "/original/{original_filename}",
    response_model=AudioUpdateResponse,
    responses={404: {"model": ErrorResponse}}
)
async def update_original_audio_metadata(
    original_filename: str,
    request: AudioMetadataUpdateRequest,
    current_label: Optional[str] = Query(
        None,
        description=(
            "Current bird species label for the original audio if the filename is ambiguous"
        )
    ),
    db: Session = Depends(get_db)
):
    """Update original audio metadata without changing audio feature vectors."""
    try:
        result = AudioManagementService.update_original_audio_metadata(
            db=db,
            original_filename=original_filename,
            new_original_filename=request.new_original_filename,
            new_label=request.label,
            current_label=current_label
        )
        return result

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "message": str(exc),
                "error_code": "AUDIO_NOT_FOUND"
            }
        )
    except Exception as exc:
        logger.error("Metadata update error: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "message": "Metadata update failed",
                "detail": str(exc),
                "error_code": "METADATA_UPDATE_FAILED"
            }
        )


@audio_router.delete(
    "/original/{original_filename}",
    response_model=AudioDeleteResponse,
    responses={404: {"model": ErrorResponse}}
)
async def delete_original_audio_file(
    original_filename: str,
    label: Optional[str] = Query(
        None,
        description="Filter deletion by bird species label if needed"
    ),
    db: Session = Depends(get_db)
):
    """Delete an original audio file and all its related segment records from the system."""
    try:
        result = AudioManagementService.delete_original_audio_file(
            db=db,
            original_filename=original_filename,
            label=label
        )
        return result

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "message": str(exc),
                "error_code": "AUDIO_NOT_FOUND"
            }
        )
    except Exception as exc:
        logger.error("Audio delete error: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "message": "Audio delete failed",
                "detail": str(exc),
                "error_code": "DELETE_FAILED"
            }
        )


# ============================================================================
# SEARCH ENDPOINTS
# ============================================================================

@search_router.post(
    "",
    response_model=SearchResponse,
    summary="Search similar bird sounds",
    description="Upload audio file and find similar bird sounds in database"
)
async def search_similar_sounds(
    file: UploadFile = File(
        ...,
        description="Audio file (.wav, .mp3, or .ogg)",
        media_type="audio/wav,audio/mpeg,audio/ogg"
    ),
    top_k: int = Query(
        settings.TOP_K_RESULTS,
        ge=1,
        le=20,
        description="Number of results to return"
    ),
    db: Session = Depends(get_db)
):
    """
    Upload audio file and search for similar bird sounds.
    
    Workflow:
    1. Validate file (type, size)
    2. Save uploaded file
    3. Segment uploaded audio into query segments
    4. Extract features from each segment
    5. Search KDTree per query segment
    6. Aggregate neighbors by original file
    7. Return ranked original-file results
    
    Returns:
    - rank: Result position (1 best)
    - original_filename: Matched original audio file
    - best_matching_segment: Best matched segment filename
    - best_similarity: Similarity score for the best segment
    - aggregate_score: File-level aggregated score
    - label: Bird species code
    - bird_info: Nested bird metadata
    """
    temp_file_path = None

    try:
        # Step 1: Read file content
        file_content = await file.read()
        file_size = len(file_content)

        # Step 2: Validate file
        is_valid, error_msg = FileValidator.validate_file(
            file.filename,
            file_size
        )

        if not is_valid:
            logger.warning(f"File validation failed: {error_msg}")
            return {
                "success": False,
                "message": error_msg,
                "query_file": file.filename,
                "top_k": 0,
                "results": []
            }

        # Step 3: Save uploaded file
        temp_file_path = FileManager.save_upload_file(
            file_content,
            file.filename,
            settings.UPLOAD_DIR
        )
        logger.info(f"File saved: {temp_file_path}")

        # Step 3-7: Perform search
        search_result = SearchService.search_by_audio_file(
            temp_file_path,
            db,
            top_k=top_k
        )

        return SearchResponse(**search_result)

    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return {
            "success": False,
            "message": "Search failed",
            "detail": str(e),
            "query_file": file.filename,
            "top_k": 0,
            "results": []
        }

    finally:
        # Cleanup: delete temp file if needed
        if temp_file_path and getattr(settings, "CLEANUP_UPLOADS", False):
            FileManager.delete_file(temp_file_path)


# ============================================================================
# HEALTH CHECK ENDPOINT
# ============================================================================

@search_router.get(
    "/health",
    summary="Health check",
    description="Check API and models health status"
)
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint.
    Verifies:
    - API is running
    - Database connection is working
    - ML models (KDTree, Scaler) are loaded
    """
    try:
        # Check database
        db.execute("SELECT 1")

        # Check models
        health_status = SearchService.check_health()

        return {
            "status": "healthy" if health_status["models_loaded"] else "degraded",
            "version": settings.API_VERSION,
            "database": "connected",
            "models_loaded": health_status["models_loaded"]
        }

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "version": settings.API_VERSION,
            "database": "disconnected",
            "models_loaded": False
        }
