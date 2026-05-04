"""
Repository for audio feature database operations.
Handles all database queries for audio features.
"""
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, desc, outerjoin, func

from app.models.audio_feature import AudioFeature
from app.models.bird_wiki import BirdWikiDetail
from app.models.original_audio import OriginalAudio
from app.schemas.audio import AudioFeatureCreate


class AudioRepository:
    """Repository class for audio feature database operations."""

    @staticmethod
    def create(
        db: Session, audio_data: AudioFeatureCreate, features_dict: dict
    ) -> AudioFeature:
        """
        Create new audio feature record in database.
        
        Args:
            db: Database session
            audio_data: Audio metadata
            features_dict: Dictionary of 41 audio features
            
        Returns:
            Created AudioFeature instance
        """
        # Merge audio data with features
        db_audio = AudioFeature(
            **audio_data.dict(),
            **features_dict
        )
        db.add(db_audio)
        db.commit()
        db.refresh(db_audio)
        return db_audio

    @staticmethod
    def get_feature_column_names() -> List[str]:
        return [
            'energy_mean', 'energy_var',
            'zcr_mean', 'zcr_var',
            'centroid_mean', 'centroid_var',
            'rolloff_mean', 'rolloff_var',
            'bandwidth_mean', 'bandwidth_var',
            'harmonic_mean', 'harmonic_var',
            'pitch_mean', 'pitch_var',
            'silence_ratio',
            'mfcc1_mean', 'mfcc1_var',
            'mfcc2_mean', 'mfcc2_var',
            'mfcc3_mean', 'mfcc3_var',
            'mfcc4_mean', 'mfcc4_var',
            'mfcc5_mean', 'mfcc5_var',
            'mfcc6_mean', 'mfcc6_var',
            'mfcc7_mean', 'mfcc7_var',
            'mfcc8_mean', 'mfcc8_var',
            'mfcc9_mean', 'mfcc9_var',
            'mfcc10_mean', 'mfcc10_var',
            'mfcc11_mean', 'mfcc11_var',
            'mfcc12_mean', 'mfcc12_var',
            'mfcc13_mean', 'mfcc13_var',
        ]

    @staticmethod
    def filter_feature_dict(features_dict: dict) -> dict:
        columns = AudioRepository.get_feature_column_names()
        return {key: float(features_dict[key]) for key in columns if key in features_dict and features_dict[key] is not None}

    @staticmethod
    def create_many(
        db: Session,
        audio_records: List[tuple]
    ) -> List[AudioFeature]:
        if not audio_records:
            return []

        objects = []
        for audio_data, features_dict in audio_records:
            clean_features = AudioRepository.filter_feature_dict(features_dict)
            obj = AudioFeature(
                **audio_data.dict(),
                **clean_features
            )
            objects.append(obj)

        db.add_all(objects)
        db.commit()
        for obj in objects:
            db.refresh(obj)

        return objects

    @staticmethod
    def get_by_id(db: Session, audio_id: int) -> Optional[AudioFeature]:
        """Get audio feature by ID."""
        return db.query(AudioFeature).filter(
            AudioFeature.id == audio_id
        ).first()

    @staticmethod
    def get_by_file_path(db: Session, filename: str) -> Optional[AudioFeature]:
        """Get audio feature by filename."""
        return db.query(AudioFeature).filter(
            AudioFeature.filename == filename
        ).first()

    @staticmethod
    def get_by_original_filename(
        db: Session,
        original_filename: str,
        label: Optional[str] = None
    ) -> List[AudioFeature]:
        """Get all audio features matching an original filename."""
        query = db.query(AudioFeature).filter(
            AudioFeature.original_filename == original_filename
        )
        if label:
            query = query.filter(AudioFeature.label == label)
        return query.all()

    @staticmethod
    def bulk_update_by_original_filename(
        db: Session,
        original_filename: str,
        update_data: dict,
        label: Optional[str] = None
    ) -> int:
        """Update metadata for audio records by original filename."""
        query = db.query(AudioFeature).filter(
            AudioFeature.original_filename == original_filename
        )
        if label:
            query = query.filter(AudioFeature.label == label)

        updated_count = query.update(update_data, synchronize_session=False)
        db.commit()
        return updated_count

    @staticmethod
    def bulk_delete_by_original_filename(
        db: Session,
        original_filename: str,
        label: Optional[str] = None
    ) -> int:
        """Delete audio records by original filename."""
        query = db.query(AudioFeature).filter(
            AudioFeature.original_filename == original_filename
        )
        if label:
            query = query.filter(AudioFeature.label == label)

        deleted_count = query.delete(synchronize_session=False)
        db.commit()
        return deleted_count

    @staticmethod
    def list_paginated(
        db: Session,
        page: int = 1,
        limit: int = 10,
        label: Optional[str] = None,
        filename: Optional[str] = None,
        original_filename: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        search_keyword: Optional[str] = None
    ) -> Tuple[List[AudioFeature], int]:
        """
        Get paginated list of audio features with filtering and sorting.
        
        Args:
            db: Database session
            page: Page number (1-indexed)
            limit: Items per page
            label: Filter by bird species code (e.g., abhori1)
            filename: Filter by segmented filename
            original_filename: Filter by original filename
            sort_by: Field to sort by
            sort_order: "asc" or "desc"
            search_keyword: Search in filename, original_filename, label
            
        Returns:
            Tuple of (audio_features list, total count)
        """
        # Build query
        query = db.query(AudioFeature)

        # Apply filters
        filters = []
        if label:
            filters.append(AudioFeature.label.ilike(f"%{label}%"))
        if filename:
            filters.append(AudioFeature.filename.ilike(f"%{filename}%"))
        if original_filename:
            filters.append(AudioFeature.original_filename.ilike(f"%{original_filename}%"))
        if search_keyword:
            filters.append(
                (AudioFeature.filename.ilike(f"%{search_keyword}%")) |
                (AudioFeature.original_filename.ilike(f"%{search_keyword}%")) |
                (AudioFeature.label.ilike(f"%{search_keyword}%"))
            )

        if filters:
            query = query.filter(and_(*filters))

        # Get total count before pagination
        total = query.count()

        # Apply sorting
        if sort_by == "created_at":
            sort_column = AudioFeature.created_at
        elif sort_by == "label":
            sort_column = AudioFeature.label
        elif sort_by == "filename":
            sort_column = AudioFeature.filename
        else:
            sort_column = AudioFeature.created_at

        if sort_order.lower() == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)

        # Apply pagination
        offset = (page - 1) * limit
        items = query.offset(offset).limit(limit).all()

        return items, total

    @staticmethod
    def get_audio_by_ids(db: Session, audio_ids: List[int]) -> List[AudioFeature]:
        """Get multiple audio features by IDs."""
        return db.query(AudioFeature).filter(
            AudioFeature.id.in_(audio_ids)
        ).all()

    @staticmethod
    def get_audio_with_bird_info_by_ids(db: Session, audio_ids: List[int]) -> List[tuple]:
        """Get multiple audio features by IDs with bird metadata loaded as tuples."""
        audio_records = db.query(AudioFeature).filter(
            AudioFeature.id.in_(audio_ids)
        ).all()
        
        # Batch load bird metadata separately to avoid N+1 queries
        bird_dict = {}
        if audio_records:
            labels = [audio.label for audio in audio_records]
            bird_details = db.query(BirdWikiDetail).filter(
                BirdWikiDetail.primary_label.in_(labels)
            ).all()
            bird_dict = {bird.primary_label: bird for bird in bird_details}
        
        # Return tuples of (audio, bird_info) so client can unpack them
        return [(audio, bird_dict.get(audio.label)) for audio in audio_records]

    @staticmethod
    def get_all_features_as_vectors(db: Session) -> Tuple[List[List[float]], List[int]]:
        """
        Get all audio features as feature vectors for KDTree indexing.
        Uses exact 41 features in the correct order used by extract_features.py
        
        Feature order:
        1. energy_mean, energy_var (2)
        2. zcr_mean, zcr_var (2)
        3. centroid_mean, centroid_var (2)
        4. rolloff_mean, rolloff_var (2)
        5. bandwidth_mean, bandwidth_var (2)
        6. harmonic_mean, harmonic_var (2)
        7. pitch_mean, pitch_var (2)
        8. silence_ratio (1)
        9. mfcc1_mean, mfcc1_var through mfcc13_mean, mfcc13_var (26)
        
        Returns:
            Tuple of (feature_vectors list, audio_ids list)
        """
        # Get all audio records
        audios = db.query(AudioFeature).all()

        if not audios:
            return [], []

        # Feature column names (41 features) - EXACT order from extract_features.py
        feature_columns = [
            'energy_mean', 'energy_var',
            'zcr_mean', 'zcr_var',
            'centroid_mean', 'centroid_var',
            'rolloff_mean', 'rolloff_var',
            'bandwidth_mean', 'bandwidth_var',
            'harmonic_mean', 'harmonic_var',
            'pitch_mean', 'pitch_var',
            'silence_ratio',
            'mfcc1_mean', 'mfcc1_var',
            'mfcc2_mean', 'mfcc2_var',
            'mfcc3_mean', 'mfcc3_var',
            'mfcc4_mean', 'mfcc4_var',
            'mfcc5_mean', 'mfcc5_var',
            'mfcc6_mean', 'mfcc6_var',
            'mfcc7_mean', 'mfcc7_var',
            'mfcc8_mean', 'mfcc8_var',
            'mfcc9_mean', 'mfcc9_var',
            'mfcc10_mean', 'mfcc10_var',
            'mfcc11_mean', 'mfcc11_var',
            'mfcc12_mean', 'mfcc12_var',
            'mfcc13_mean', 'mfcc13_var',
        ]

        # Extract feature vectors
        vectors = []
        ids = []
        for audio in audios:
            vector = [getattr(audio, col, None) for col in feature_columns]
            # Only include complete vectors (no None values)
            if all(v is not None for v in vector):
                vectors.append(vector)
                ids.append(audio.id)

        return vectors, ids

    @staticmethod
    def update(db: Session, audio_id: int, update_data: dict) -> Optional[AudioFeature]:
        """Update audio feature record."""
        db_audio = AudioRepository.get_by_id(db, audio_id)
        if not db_audio:
            return None

        for key, value in update_data.items():
            setattr(db_audio, key, value)

        db.commit()
        db.refresh(db_audio)
        return db_audio

    @staticmethod
    def delete(db: Session, audio_id: int) -> bool:
        """Delete audio feature record."""
        db_audio = AudioRepository.get_by_id(db, audio_id)
        if not db_audio:
            return False

        db.delete(db_audio)
        db.commit()
        return True


class OriginalAudioRepository:
    """Repository for original audio metadata records."""

    @staticmethod
    def create(db: Session, original_audio_data: dict) -> OriginalAudio:
        original_audio = OriginalAudio(**original_audio_data)
        db.add(original_audio)
        db.commit()
        db.refresh(original_audio)
        return original_audio

    @staticmethod
    def get_by_id(db: Session, original_id: int) -> Optional[OriginalAudio]:
        return db.query(OriginalAudio).filter(
            OriginalAudio.id == original_id
        ).first()

    @staticmethod
    def get_by_filename_and_label(
        db: Session,
        original_filename: str,
        label: Optional[str] = None
    ) -> List[OriginalAudio]:
        query = db.query(OriginalAudio).filter(
            OriginalAudio.original_filename == original_filename
        )
        if label:
            query = query.filter(OriginalAudio.label == label)
        return query.all()

    @staticmethod
    def update(db: Session, original_id: int, update_data: dict) -> Optional[OriginalAudio]:
        original_audio = OriginalAudioRepository.get_by_id(db, original_id)
        if not original_audio:
            return None

        for key, value in update_data.items():
            setattr(original_audio, key, value)

        db.commit()
        db.refresh(original_audio)
        return original_audio

    @staticmethod
    def delete_by_id(db: Session, original_id: int) -> bool:
        original_audio = OriginalAudioRepository.get_by_id(db, original_id)
        if not original_audio:
            return False

        db.delete(original_audio)
        db.commit()
        return True

    @staticmethod
    def list_paginated(
        db: Session,
        page: int = 1,
        limit: int = 10,
        label: Optional[str] = None,
        original_filename: Optional[str] = None,
        search_keyword: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Tuple[List[OriginalAudio], int]:
        query = db.query(OriginalAudio)

        filters = []
        if label:
            filters.append(OriginalAudio.label.ilike(f"%{label}%"))
        if original_filename:
            filters.append(OriginalAudio.original_filename.ilike(f"%{original_filename}%"))
        if search_keyword:
            filters.append(
                (OriginalAudio.original_filename.ilike(f"%{search_keyword}%")) |
                (OriginalAudio.label.ilike(f"%{search_keyword}%"))
            )
        if filters:
            query = query.filter(and_(*filters))

        total = query.count()

        sort_column = OriginalAudio.created_at
        if sort_by == "label":
            sort_column = OriginalAudio.label
        elif sort_by == "original_filename":
            sort_column = OriginalAudio.original_filename

        if sort_order.lower() == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)

        offset = (page - 1) * limit
        items = query.offset(offset).limit(limit).all()
        return items, total

    @staticmethod
    def count_audio_segments(db: Session, original_filename: str, label: str) -> int:
        return db.query(func.count(AudioFeature.id)).filter(
            AudioFeature.original_filename == original_filename,
            AudioFeature.label == label
        ).scalar() or 0


class BirdWikiRepository:
    """Repository class for bird wiki database operations."""

    @staticmethod
    def get_by_id(db: Session, bird_id: int) -> Optional[BirdWikiDetail]:
        """Get bird wiki record by ID."""
        return db.query(BirdWikiDetail).filter(
            BirdWikiDetail.id == bird_id
        ).first()

    @staticmethod
    def get_by_primary_label(db: Session, primary_label: str) -> Optional[BirdWikiDetail]:
        """Get bird wiki record by primary_label (bird species code)."""
        return db.query(BirdWikiDetail).filter(
            BirdWikiDetail.primary_label == primary_label
        ).first()

    @staticmethod
    def get_by_scientific_name(db: Session, scientific_name: str) -> Optional[BirdWikiDetail]:
        """Get bird wiki record by scientific name."""
        return db.query(BirdWikiDetail).filter(
            BirdWikiDetail.scientific_name == scientific_name
        ).first()

    @staticmethod
    def get_by_primary_labels(
        db: Session,
        primary_labels: List[str]
    ) -> List[BirdWikiDetail]:
        """Get multiple bird wiki records by primary_labels."""
        return db.query(BirdWikiDetail).filter(
            BirdWikiDetail.primary_label.in_(primary_labels)
        ).all()

    @staticmethod
    def search_by_keyword(
        db: Session,
        keyword: str,
        limit: int = 10
    ) -> List[BirdWikiDetail]:
        """Search bird wiki records by keyword in common_name, scientific_name, order, family."""
        return db.query(BirdWikiDetail).filter(
            (BirdWikiDetail.common_name.ilike(f"%{keyword}%")) |
            (BirdWikiDetail.scientific_name.ilike(f"%{keyword}%")) |
            (BirdWikiDetail.order.ilike(f"%{keyword}%")) |
            (BirdWikiDetail.family.ilike(f"%{keyword}%"))
        ).limit(limit).all()

    @staticmethod
    def get_by_family(
        db: Session,
        family: str,
        limit: int = 10
    ) -> List[BirdWikiDetail]:
        """Get bird wiki records by taxonomic family."""
        return db.query(BirdWikiDetail).filter(
            BirdWikiDetail.family == family
        ).limit(limit).all()
