"""
File utilities for handling audio file uploads and validation.
"""
import os
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class FileValidator:
    """Utility class for validating uploaded files."""

    @classmethod
    def is_valid_extension(cls, filename: str) -> bool:
        """Check if file extension is allowed."""
        ext = Path(filename).suffix.lower()
        return ext in {ext.lower() for ext in settings.ALLOWED_AUDIO_EXTENSIONS}

    @classmethod
    def is_valid_size(cls, size_bytes: int) -> bool:
        """Check if file size is within limit."""
        return size_bytes <= settings.MAX_UPLOAD_SIZE_BYTES

    @classmethod
    def validate_file(
        cls, filename: str, file_size: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate uploaded file.
        Returns: (is_valid, error_message)
        """
        if not filename:
            return False, "Filename cannot be empty"

        if not cls.is_valid_extension(filename):
            return False, (
                f"Invalid file extension. Allowed: {', '.join(cls.ALLOWED_EXTENSIONS)}"
            )

        if not cls.is_valid_size(file_size):
            max_mb = cls.MAX_SIZE_BYTES / (1024 * 1024)
            return False, f"File size exceeds {max_mb:.0f}MB limit"

        return True, None


class FileManager:
    """Utility class for managing file operations."""

    @staticmethod
    def ensure_upload_dir(upload_dir: str) -> Path:
        """Ensure upload directory exists."""
        upload_path = Path(upload_dir)
        upload_path.mkdir(parents=True, exist_ok=True)
        return upload_path

    @staticmethod
    def generate_unique_filename(original_filename: str) -> str:
        """
        Generate unique filename to avoid conflicts.
        Format: timestamp_original_filename
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        name_without_ext = Path(original_filename).stem
        ext = Path(original_filename).suffix
        return f"{timestamp}_{name_without_ext}{ext}"

    @staticmethod
    def save_upload_file(
        file_content: bytes,
        filename: str,
        upload_dir: str
    ) -> str:
        """
        Save uploaded file to disk.
        Returns: relative file path
        """
        FileManager.ensure_upload_dir(upload_dir)
        unique_filename = FileManager.generate_unique_filename(filename)
        file_path = Path(upload_dir) / unique_filename

        with open(file_path, "wb") as f:
            f.write(file_content)

        logger.info(f"File saved: {file_path}")
        return str(file_path)

    @staticmethod
    def save_file_bytes(
        file_content: bytes,
        filename: str,
        directory: str
    ) -> str:
        """Save file bytes to a target directory with a unique filename."""
        FileManager.ensure_upload_dir(directory)
        unique_filename = FileManager.generate_unique_filename(filename)
        file_path = Path(directory) / unique_filename

        with open(file_path, "wb") as f:
            f.write(file_content)

        logger.info(f"File saved: {file_path}")
        return str(file_path)

    @staticmethod
    def make_unique_path(path: Path) -> Path:
        """Generate a unique filename path when the target already exists."""
        if not path.exists():
            return path

        parent = path.parent
        stem = path.stem
        suffix = path.suffix
        counter = 1

        candidate = parent / f"{stem}_{counter}{suffix}"
        while candidate.exists():
            counter += 1
            candidate = parent / f"{stem}_{counter}{suffix}"

        return candidate

    @staticmethod
    def move_file(source: str, destination: str) -> str:
        """Move a file to a destination path, ensuring the target directory exists."""
        src_path = Path(source)
        dest_path = Path(destination)
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        if dest_path.exists():
            dest_path = FileManager.make_unique_path(dest_path)

        try:
            src_path.replace(dest_path)
        except Exception:
            import shutil
            dest_path = Path(FileManager.make_unique_path(dest_path))
            shutil.move(str(src_path), str(dest_path))

        logger.info(f"Moved file from {source} to {dest_path}")
        return str(dest_path)

    @staticmethod
    def file_exists(file_path: str) -> bool:
        """Check if file exists."""
        return Path(file_path).exists()

    @staticmethod
    def get_file_size(file_path: str) -> int:
        """Get file size in bytes."""
        return Path(file_path).stat().st_size

    @staticmethod
    def delete_file(file_path: str) -> bool:
        """Delete file if it exists."""
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                logger.info(f"File deleted: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {str(e)}")
            return False
