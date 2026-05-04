"""
Audio import service.
Handles upload validation, segmentation, feature extraction, database insertion, and KDTree rebuild.
"""
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.repositories.audio_repository import AudioRepository, OriginalAudioRepository
from app.schemas.audio import AudioFeatureCreate
from app.services.feature_extractor_service import FeatureExtractorService
from app.services.kdtree_manager import KDTreeManager
from app.services.segment_service import SegmentService
from app.utils.file_utils import FileManager

logger = logging.getLogger(__name__)


class AudioImportService:
    """Service for importing new audio files into the CBIR system."""

    @staticmethod
    def _normalize_original_filename(
        original_filename: str,
        upload_filename: str
    ) -> str:
        if not original_filename:
            return upload_filename

        original_filename = original_filename.strip()
        if not original_filename:
            return upload_filename

        if Path(original_filename).suffix:
            return original_filename

        return f"{original_filename}{Path(upload_filename).suffix}"

    @staticmethod
    def import_audio_file(
        file_content: bytes,
        upload_filename: str,
        label: str,
        original_filename: str,
        db: Session
    ) -> Dict[str, Any]:
        start_time = time.time()
        temp_file_path = None
        saved_original_path = None
        saved_segments: List[Dict[str, Any]] = []

        try:
            temp_file_path = FileManager.save_upload_file(
                file_content,
                upload_filename,
                settings.UPLOAD_DIR
            )
            logger.info("Saved uploaded file for import: %s", temp_file_path)

            normalized_original_filename = AudioImportService._normalize_original_filename(
                original_filename,
                upload_filename
            )
            original_save_path = FileManager.save_file_bytes(
                file_content,
                normalized_original_filename,
                str(Path(settings.ORIGINAL_AUDIO_ROOT) / label)
            )
            saved_original_path = original_save_path
            logger.info("Saved original audio to train_audio label folder: %s", original_save_path)

            y_full, sr_full = SegmentService.load_audio(temp_file_path)
            full_duration = len(y_full) / sr_full

            segments = SegmentService.segment_audio(temp_file_path)
            if not segments:
                y, sr = SegmentService.load_audio(temp_file_path)
                duration = len(y) / sr
                if duration >= settings.MIN_SEGMENT_DURATION_SECONDS:
                    segments = [{
                        "segment_index": 1,
                        "start_time": 0.0,
                        "end_time": duration,
                        "audio": y,
                        "sr": sr,
                        "duration": duration
                    }]
                else:
                    raise ValueError(
                        "Uploaded audio could not be segmented into valid segments. "
                        "Please provide a longer or clearer audio file."
                    )

            saved_segments = SegmentService.save_segments(
                segments,
                label,
                normalized_original_filename
            )
            logger.info("Saved %d audio segments for import", len(saved_segments))

            audio_records = []
            for segment in saved_segments:
                try:
                    features = FeatureExtractorService.extract_features_from_array(
                        segment["audio"],
                        segment["sr"]
                    )
                    filtered_features = AudioRepository.filter_feature_dict(features)
                    audio_data = AudioFeatureCreate(
                        filename=segment["filename"],
                        original_filename=normalized_original_filename,
                        label=label,
                        duration=segment["duration"],
                        sample_rate=segment["sample_rate"]
                    )
                    audio_records.append((audio_data, filtered_features))
                except Exception as exc:
                    logger.warning(
                        "Feature extraction failed for segment %s: %s",
                        segment["filename"],
                        str(exc)
                    )

            if not audio_records:
                raise ValueError("Feature extraction failed for every imported segment.")

            inserted_objects = AudioRepository.create_many(db, audio_records)
            features_inserted = len(inserted_objects)
            logger.info("Inserted %d audio feature records into database", features_inserted)

            OriginalAudioRepository.create(db, {
                "original_filename": normalized_original_filename,
                "label": label,
                "file_path": str(Path(label) / normalized_original_filename),
                "duration": full_duration,
                "sample_rate": sr_full,
            })
            logger.info("Created original audio metadata record for %s", normalized_original_filename)

            kdtree_rebuilt = KDTreeManager.rebuild_kdtree(
                db,
                settings.KDTREE_MODEL_PATH,
                settings.SCALER_MODEL_PATH
            )

            processing_time_ms = (time.time() - start_time) * 1000
            return {
                "success": True,
                "original_filename": normalized_original_filename,
                "label": label,
                "segments_created": len(saved_segments),
                "features_inserted": features_inserted,
                "kdtree_rebuilt": kdtree_rebuilt,
                "processing_time_ms": processing_time_ms,
                "message": "Imported audio successfully."
            }

        except Exception as exc:
            db.rollback()
            logger.error("Audio import failed: %s", str(exc))
            for segment in saved_segments:
                try:
                    FileManager.delete_file(segment.get("filepath"))
                except Exception:
                    logger.warning("Failed to delete imported segment file after failure: %s", segment.get("filepath"))
            if saved_original_path:
                try:
                    FileManager.delete_file(saved_original_path)
                except Exception:
                    logger.warning("Failed to delete original audio file after failure: %s", saved_original_path)
            raise

        finally:
            if temp_file_path and getattr(settings, "CLEANUP_UPLOADS", False):
                FileManager.delete_file(temp_file_path)
