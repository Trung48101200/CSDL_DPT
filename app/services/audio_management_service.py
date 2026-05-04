from pathlib import Path
import shutil
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.repositories.audio_repository import AudioRepository, OriginalAudioRepository
from app.services.kdtree_manager import KDTreeManager
from app.utils.file_utils import FileManager


class AudioManagementService:
    """Service to manage metadata updates and original audio deletions."""

    @staticmethod
    def _original_audio_path(label: str, original_filename: str) -> str:
        return str(Path(settings.ORIGINAL_AUDIO_ROOT) / label / original_filename)

    @staticmethod
    def _segment_file_path(label: str, filename: str) -> str:
        return str(Path(settings.SEGMENT_SAVE_ROOT) / label / filename)

    @staticmethod
    def _normalize_original_filename(original_filename: str) -> str:
        return original_filename.strip().replace(" ", "_")

    @staticmethod
    def update_original_audio_metadata(
        db: Session,
        original_filename: str,
        new_original_filename: Optional[str] = None,
        new_label: Optional[str] = None,
        current_label: Optional[str] = None,
    ) -> Dict[str, object]:
        """Update original audio metadata and optionally move files on disk."""
        original_filename = AudioManagementService._normalize_original_filename(original_filename)
        originals = OriginalAudioRepository.get_by_filename_and_label(
            db,
            original_filename,
            current_label
        )
        if not originals:
            raise ValueError(f"Original filename '{original_filename}' not found")

        if not new_original_filename and not new_label:
            raise ValueError("At least one of new_original_filename or label must be provided")

        if new_original_filename:
            new_original_filename = AudioManagementService._normalize_original_filename(new_original_filename)

        updated_records = len(originals)
        updated_labels = set()

        # Move original audio files for each affected label
        for original in originals:
            source_path = AudioManagementService._original_audio_path(original.label, original.original_filename)
            target_label = new_label if new_label else original.label
            target_filename = new_original_filename if new_original_filename else original.original_filename
            dest_path = AudioManagementService._original_audio_path(target_label, target_filename)

            if Path(source_path).exists():
                FileManager.move_file(source_path, dest_path)

            update_data = {}
            if new_original_filename:
                update_data["original_filename"] = new_original_filename
            if new_label:
                update_data["label"] = new_label
                update_data["file_path"] = str(Path(new_label) / target_filename)
            elif new_original_filename:
                update_data["file_path"] = str(Path(original.label) / target_filename)

            if update_data:
                OriginalAudioRepository.update(db, original.id, update_data)

            updated_labels.add(target_label)

        if new_original_filename or new_label:
            AudioRepository.bulk_update_by_original_filename(
                db,
                original_filename,
                {k: v for k, v in {
                    "original_filename": new_original_filename,
                    "label": new_label
                }.items() if v is not None},
                current_label
            )

        return {
            "success": True,
            "original_filename": original_filename,
            "updated_records": updated_records,
            "updated_label": new_label,
            "updated_original_filename": new_original_filename,
            "message": "Audio metadata updated successfully"
        }

    @staticmethod
    def delete_original_audio_file(
        db: Session,
        original_filename: str,
        label: Optional[str] = None
    ) -> Dict[str, object]:
        """Delete original audio file and all related segment records, then rebuild KDTree."""
        original_filename = AudioManagementService._normalize_original_filename(original_filename)
        originals = OriginalAudioRepository.get_by_filename_and_label(db, original_filename, label)
        if not originals:
            raise ValueError(f"Original filename '{original_filename}' not found")

        deleted_original_paths = set()
        deleted_segment_count = 0

        for original in originals:
            original_path = AudioManagementService._original_audio_path(original.label, original.original_filename)
            if Path(original_path).exists():
                Path(original_path).unlink()
                deleted_original_paths.add(original_path)

            if label is None:
                related_rows = AudioRepository.get_by_original_filename(db, original_filename, original.label)
            else:
                related_rows = AudioRepository.get_by_original_filename(db, original_filename, label)

            for row in related_rows:
                segment_path = AudioManagementService._segment_file_path(row.label, row.filename)
                if Path(segment_path).exists():
                    Path(segment_path).unlink()
                    deleted_segment_count += 1

        deleted_count = AudioRepository.bulk_delete_by_original_filename(db, original_filename, label)

        for original in originals:
            OriginalAudioRepository.delete_by_id(db, original.id)

        kdtree_rebuilt = False
        try:
            KDTreeManager.rebuild_kdtree(db)
            kdtree_rebuilt = True
        except Exception:
            pass

        return {
            "success": True,
            "original_filename": original_filename,
            "deleted_audio_records": deleted_count,
            "deleted_original_files": len(deleted_original_paths),
            "deleted_segment_files": deleted_segment_count,
            "kdtree_rebuilt": kdtree_rebuilt,
            "message": "Original audio and its segments deleted successfully"
        }
