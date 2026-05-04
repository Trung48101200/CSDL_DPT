"""
KDTree service for nearest neighbor search.
Handles loading and querying pre-built KDTree and scaler models.
"""
import logging
from typing import List, Tuple, Optional
import numpy as np
from pathlib import Path
import joblib
from scipy.spatial import cKDTree

logger = logging.getLogger(__name__)


class KDTreeService:
    """Service for KDTree-based similarity search."""

    # Class-level attributes to store loaded models (singleton pattern)
    _kdtree: Optional[cKDTree] = None
    _scaler = None
    _audio_ids: Optional[List[int]] = None

    @classmethod
    def load_models(
        cls,
        kdtree_path: str,
        scaler_path: str,
        force_reload: bool = False
    ) -> bool:
        """
        Load KDTree and StandardScaler models from disk.
        Models are cached in class attributes to avoid reloading.
        
        Args:
            kdtree_path: Path to pickled KDTree
            scaler_path: Path to pickled StandardScaler
            
        Returns:
            True if loading successful, False otherwise
        """
        try:
            if cls._kdtree is not None and not force_reload:
                logger.info("Models already loaded")
                return True

            # Load KDTree
            if not Path(kdtree_path).exists():
                logger.warning(f"KDTree file not found: {kdtree_path}")
                return False

            data = joblib.load(kdtree_path)
            if isinstance(data, dict):
                # Assuming dict format with 'kdtree' and 'audio_ids' keys
                cls._kdtree = data.get("kdtree")
                cls._audio_ids = data.get("audio_ids")
            else:
                cls._kdtree = data
                cls._audio_ids = None

            logger.info(f"KDTree loaded from {kdtree_path}")

            # Load StandardScaler
            if not Path(scaler_path).exists():
                logger.warning(f"Scaler file not found: {scaler_path}")
                return False

            cls._scaler = joblib.load(scaler_path)
            logger.info(f"StandardScaler loaded from {scaler_path}")

            return True

        except Exception as e:
            logger.error(f"Failed to load models: {str(e)}")
            return False

    @classmethod
    def set_tree(cls, kdtree: cKDTree, audio_ids: Optional[List[int]] = None):
        """Update the in-memory KDTree and associated audio IDs."""
        cls._kdtree = kdtree
        cls._audio_ids = audio_ids
        logger.info("In-memory KDTree updated with %d audio ids", len(audio_ids) if audio_ids else 0)

    @classmethod
    def is_ready(cls) -> bool:
        """Check if models are loaded and ready."""
        return cls._kdtree is not None and cls._scaler is not None

    @classmethod
    def normalize_features(cls, features: np.ndarray) -> np.ndarray:
        """
        Normalize feature vector using loaded scaler.
        
        Args:
            features: Raw feature vector (shape: (41,))
            
        Returns:
            Normalized feature vector
            
        Raises:
            RuntimeError: If scaler not loaded
        """
        if cls._scaler is None:
            raise RuntimeError("Scaler not loaded. Call load_models() first.")

        try:
            # Ensure features is 2D for scaler
            if features.ndim == 1:
                features = features.reshape(1, -1)

            normalized = cls._scaler.transform(features)
            return normalized.flatten()

        except Exception as e:
            logger.error(f"Error normalizing features: {str(e)}")
            raise

    @classmethod
    def search_nearest_neighbors(
        cls,
        query_vector: np.ndarray,
        k: int = 5,
        distance_threshold: Optional[float] = None
    ) -> List[Tuple[int, float]]:
        """
        Find k nearest neighbors to query vector.
        
        Args:
            query_vector: Normalized query feature vector
            k: Number of neighbors to return
            distance_threshold: Optional max distance threshold
            
        Returns:
            List of tuples (audio_id, distance) sorted by distance
            
        Raises:
            RuntimeError: If KDTree not loaded
        """
        if cls._kdtree is None:
            raise RuntimeError("KDTree not loaded. Call load_models() first.")

        try:
            # Ensure query_vector is properly shaped
            if query_vector.ndim == 1:
                query_vector = query_vector.reshape(1, -1)

            # Query KDTree
            distances, indices = cls._kdtree.query(
                query_vector, k=k, workers=-1
            )

            # Flatten for single query
            distances = distances.flatten()
            indices = indices.flatten()

            # Build results
            results = []
            for idx, dist in zip(indices, distances):
                # Filter by distance threshold if provided
                if distance_threshold is not None:
                    if dist > distance_threshold:
                        continue

                # Get audio_id
                if cls._audio_ids is not None:
                    audio_id = cls._audio_ids[idx]
                else:
                    audio_id = idx

                results.append((audio_id, float(dist)))

            logger.info(f"Found {len(results)} neighbors for query")
            return results

        except Exception as e:
            logger.error(f"Error in nearest neighbor search: {str(e)}")
            raise

    @classmethod
    def search_and_normalize(
        cls,
        raw_features: np.ndarray,
        k: int = 5,
        distance_threshold: Optional[float] = None
    ) -> List[Tuple[int, float]]:
        """
        Combined method: normalize features and search KDTree.
        Convenience method for API endpoints.
        
        Args:
            raw_features: Raw (not normalized) feature vector
            k: Number of neighbors
            distance_threshold: Optional max distance threshold
            
        Returns:
            List of tuples (audio_id, distance)
        """
        # Normalize
        normalized = cls.normalize_features(raw_features)

        # Search
        results = cls.search_nearest_neighbors(
            normalized, k=k, distance_threshold=distance_threshold
        )

        return results

    @classmethod
    def reset(cls):
        """Reset loaded models (useful for testing)."""
        cls._kdtree = None
        cls._scaler = None
        cls._audio_ids = None
        logger.info("Models reset")
