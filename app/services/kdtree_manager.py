"""
KDTree manager for rebuilding the search index after import.
"""
import logging
import time
from pathlib import Path
from typing import List

import joblib
import numpy as np
from scipy.spatial import cKDTree
from sqlalchemy.orm import Session

from app.core.config import settings
from app.repositories.audio_repository import AudioRepository
from app.services.kdtree_service import KDTreeService

logger = logging.getLogger(__name__)


class KDTreeManager:
    """Manager for rebuilding and persisting KDTree indexes."""

    @staticmethod
    def rebuild_kdtree(
        db: Session,
        kdtree_path: str,
        scaler_path: str
    ) -> bool:
        start_time = time.time()

        if not KDTreeService.is_ready():
            KDTreeService.load_models(kdtree_path, scaler_path)

        if KDTreeService._scaler is None:
            raise RuntimeError("Scaler is not loaded. Cannot rebuild KDTree without scaler.")

        feature_vectors, audio_ids = AudioRepository.get_all_features_as_vectors(db)
        if not feature_vectors:
            raise RuntimeError("No audio feature vectors found in database to build KDTree.")

        features_array = np.asarray(feature_vectors, dtype=np.float32)
        normalized_features = KDTreeService._scaler.transform(features_array)
        kdtree = cKDTree(normalized_features)

        output_path = Path(kdtree_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"kdtree": kdtree, "audio_ids": audio_ids}, str(output_path))

        KDTreeService.set_tree(kdtree, audio_ids)

        elapsed_ms = (time.time() - start_time) * 1000
        logger.info("Rebuilt KDTree with %d vectors in %.1fms", len(audio_ids), elapsed_ms)
        return True
