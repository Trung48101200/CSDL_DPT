"""
Search service for orchestrating segment-level retrieval.
This service performs query audio segmentation, feature extraction per segment,
KDTree neighbor search per segment, and aggregation to original files.
"""
import logging
import math
import sys
import time
from os.path import abspath, dirname
from typing import Any, Dict, List, Optional

import librosa
import numpy as np
from sqlalchemy.orm import Session

from app.core.config import settings
from app.repositories.audio_repository import AudioRepository
from app.schemas.audio import BirdInfo, SearchResultItem
from app.services.feature_extractor_service import FeatureExtractorService
from app.services.kdtree_service import KDTreeService
from app.services.segment_service import SegmentService

# Ensure the repository root is available for importing root-level helpers
sys.path.insert(0, dirname(dirname(dirname(abspath(__file__)))))
from extract_features import extract_mfcc_only

logger = logging.getLogger(__name__)


class SearchService:
    """Service for performing segment-level audio retrieval."""

    FEATURE_ORDER = [
        "energy_mean", "energy_var",
        "zcr_mean", "zcr_var",
        "centroid_mean", "centroid_var",
        "rolloff_mean", "rolloff_var",
        "bandwidth_mean", "bandwidth_var",
        "harmonic_mean", "harmonic_var",
        "pitch_mean", "pitch_var",
        "silence_ratio",
    ] + [f"mfcc{i}_mean" for i in range(1, 14)] + [f"mfcc{i}_var" for i in range(1, 14)]

    @staticmethod
    def search_by_audio_file(
        file_path: str,
        db: Session,
        top_k: int = 5,
        distance_threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """Search for similar audio at the original-file level."""
        start_time = time.time()

        try:
            logger.info("Starting segment-level search for query audio: %s", file_path)

            segment_start = time.time()
            query_segments = SearchService.segment_audio(file_path)
            segment_time_ms = (time.time() - segment_start) * 1000
            logger.info(
                "Created %d query segments in %.1fms",
                len(query_segments),
                segment_time_ms
            )

            if not query_segments or len(query_segments) == 1:
                if len(query_segments) == 0:
                    logger.warning("No query segments extracted from uploaded audio. Falling back to whole-file extraction.")
                else:
                    logger.info("Only one query segment found. Falling back to whole-file extraction for more robust search.")
                whole_feature = SearchService.extract_whole_file_features(file_path)
                segment_features = [whole_feature] if whole_feature is not None else []
            else:
                extraction_start = time.time()
                segment_features = [
                    SearchService.extract_segment_features(segment)
                    for segment in query_segments
                ]
                segment_features = [segment for segment in segment_features if segment is not None]
                extraction_time_ms = (time.time() - extraction_start) * 1000
                logger.info(
                    "Extracted features for %d query segments in %.1fms",
                    len(segment_features),
                    extraction_time_ms
                )

            if not segment_features:
                logger.warning("No valid feature vectors could be extracted from query segments or whole file.")
                return {
                    "success": True,
                    "query_file": file_path,
                    "top_k": 0,
                    "message": "No valid feature vectors could be extracted from the uploaded file.",
                    "processing_time_ms": (time.time() - start_time) * 1000,
                    "results": []
                }

            search_start = time.time()
            neighbor_hits = SearchService.search_segments(
                segment_features,
                top_k=top_k,
                distance_threshold=distance_threshold
            )
            search_time_ms = (time.time() - search_start) * 1000
            logger.info(
                "Found %d neighbor hits across segments in %.1fms",
                len(neighbor_hits),
                search_time_ms
            )

            if not neighbor_hits:
                logger.warning("KDTree search produced no neighbor hits for all query segments.")
                return {
                    "success": True,
                    "query_file": file_path,
                    "top_k": 0,
                    "message": "No matching audio segments were found for the uploaded query.",
                    "processing_time_ms": (time.time() - start_time) * 1000,
                    "results": []
                }

            audio_ids = list({hit["audio_id"] for hit in neighbor_hits})
            audio_tuples = AudioRepository.get_audio_with_bird_info_by_ids(db, audio_ids)
            audio_dict = {audio.id: (audio, bird_info) for audio, bird_info in audio_tuples}

            aggregation_start = time.time()
            aggregated_results = SearchService.aggregate_results(neighbor_hits, audio_dict)
            aggregation_time_ms = (time.time() - aggregation_start) * 1000
            logger.info(
                "Aggregated %d original files in %.1fms",
                len(aggregated_results),
                aggregation_time_ms
            )

            response_results = SearchService.build_response(aggregated_results, top_k=top_k)
            processing_time_ms = (time.time() - start_time) * 1000
            logger.info("Search completed in %.1fms", processing_time_ms)

            return {
                "success": True,
                "query_file": file_path,
                "top_k": min(top_k, len(response_results)),
                "processing_time_ms": processing_time_ms,
                "results": [result.dict() for result in response_results]
            }

        except Exception as exc:
            logger.error("Search failed: %s", str(exc))
            return {
                "success": False,
                "message": f"Search failed: {str(exc)}",
                "query_file": file_path,
                "top_k": 0,
                "results": []
            }

    @staticmethod
    def segment_audio(file_path: str) -> List[Dict[str, Any]]:
        """Create query segments using the shared segmentation pipeline."""
        return SegmentService.segment_audio(file_path)

    @staticmethod
    def extract_segment_features(segment_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract the standard 41-dimensional feature vector for one query segment."""
        features_dict = FeatureExtractorService.extract_features_from_array(
            segment_data["audio"],
            segment_data["sr"]
        )
        feature_vector = SearchService.build_feature_vector(features_dict)
        if feature_vector.shape[0] != settings.NUM_FEATURES:
            logger.warning(
                "Skipping query segment %s because expected %d features, got %d",
                segment_data["segment_index"],
                settings.NUM_FEATURES,
                feature_vector.shape[0]
            )
            return None

        return {
            "segment_index": segment_data["segment_index"],
            "start_time": segment_data["start_time"],
            "end_time": segment_data["end_time"],
            "feature_vector": feature_vector
        }

    @staticmethod
    def build_feature_vector(features_dict: Dict[str, Any]) -> np.ndarray:
        """Build a fixed-order feature vector from extracted feature dictionary."""
        return np.array(
            [features_dict.get(key, 0.0) for key in SearchService.FEATURE_ORDER],
            dtype=np.float32
        )

    @staticmethod
    def extract_whole_file_features(file_path: str) -> Optional[Dict[str, Any]]:
        """Extract features from the full uploaded file as a fallback."""
        try:
            y, sr = librosa.load(file_path, sr=settings.TARGET_SAMPLE_RATE, mono=True)
            features_dict = FeatureExtractorService.extract_features_from_array(y, sr)
            feature_vector = SearchService.build_feature_vector(features_dict)
            if feature_vector.shape[0] != settings.NUM_FEATURES:
                logger.warning(
                    "Whole-file extraction did not produce %d features, got %d",
                    settings.NUM_FEATURES,
                    feature_vector.shape[0]
                )
                return None

            return {
                "segment_index": 1,
                "start_time": 0.0,
                "end_time": float(len(y) / sr),
                "feature_vector": feature_vector
            }
        except Exception as exc:
            logger.warning("Whole-file feature extraction failed: %s", str(exc))
            return None

    @staticmethod
    def search_segments(
        segment_features: List[Dict[str, Any]],
        top_k: int,
        distance_threshold: Optional[float]
    ) -> List[Dict[str, Any]]:
        """Query the KDTree for each segment and collect neighbor hits."""
        neighbor_hits: List[Dict[str, Any]] = []
        search_k = min(top_k * settings.MAX_NEIGHBORS_PER_SEGMENT, 50)

        for segment in segment_features:
            hits = KDTreeService.search_and_normalize(
                segment["feature_vector"],
                k=search_k,
                distance_threshold=distance_threshold
            )

            for audio_id, distance in hits:
                neighbor_hits.append({
                    "audio_id": audio_id,
                    "distance": distance,
                    "query_segment_index": segment["segment_index"],
                    "query_start_time": segment["start_time"],
                    "query_end_time": segment["end_time"]
                })

        return neighbor_hits

    @staticmethod
    def aggregate_results(
        neighbor_hits: List[Dict[str, Any]],
        audio_dict: Dict[int, tuple]
    ) -> List[Dict[str, Any]]:
        """Aggregate segment matches to original_filename results."""
        file_groups: Dict[str, Dict[str, Any]] = {}

        for hit in neighbor_hits:
            audio_tuple = audio_dict.get(hit["audio_id"])
            if audio_tuple is None:
                continue
            
            audio_item, bird_info = audio_tuple

            original_filename = audio_item.original_filename
            if original_filename not in file_groups:
                file_groups[original_filename] = {
                    "original_filename": original_filename,
                    "label": audio_item.label,
                    "bird_info": bird_info,
                    "best_matching_segment": audio_item.filename,
                    "best_distance": hit["distance"],
                    "distances": [hit["distance"]],
                    "matched_segments": 1
                }
                continue

            group = file_groups[original_filename]
            group["distances"].append(hit["distance"])
            group["matched_segments"] += 1
            if hit["distance"] < group["best_distance"]:
                group["best_distance"] = hit["distance"]
                group["best_matching_segment"] = audio_item.filename

        aggregated_results: List[Dict[str, Any]] = []
        for group in file_groups.values():
            similarities = [
                SearchService.distance_to_similarity(distance)
                for distance in group["distances"]
            ]
            similarities.sort(reverse=True)
            best_similarity = similarities[0] if similarities else 0.0
            top_n_similarities = similarities[: min(settings.SEARCH_TOP_N_AGGREGATION, len(similarities)) ]
            mean_top_n = float(np.mean(top_n_similarities)) if top_n_similarities else 0.0
            aggregate_score = float(best_similarity * 0.7 + mean_top_n * 0.3)

            aggregated_results.append({
                "original_filename": group["original_filename"],
                "label": group["label"],
                "best_matching_segment": group["best_matching_segment"],
                "best_similarity": round(best_similarity, 4),
                "aggregate_score": round(aggregate_score, 4),
                "matched_segments": group["matched_segments"],
                "bird_info": group["bird_info"],
                "best_distance": group["best_distance"]
            })

        aggregated_results.sort(key=lambda x: x["aggregate_score"], reverse=True)
        return aggregated_results

    @staticmethod
    def distance_to_similarity(distance: float) -> float:
        """Convert KDTree distance into a normalized 0-100 similarity score."""
        if distance is None or math.isnan(distance):
            return 0.0
        return float(max(0.0, 100.0 / (1.0 + distance)))

    @staticmethod
    def build_response(
        aggregated_results: List[Dict[str, Any]],
        top_k: int
    ) -> List[SearchResultItem]:
        """Build final search response items for the API."""
        items: List[SearchResultItem] = []
        for rank, result in enumerate(aggregated_results[:top_k], start=1):
            bird_info = result.get("bird_info")
            items.append(SearchResultItem(
                rank=rank,
                original_filename=result["original_filename"],
                best_matching_segment=result["best_matching_segment"],
                best_similarity=result["best_similarity"],
                aggregate_score=result["aggregate_score"],
                matched_segments=result["matched_segments"],
                label=result["label"],
                bird_info={
                    "common_name": bird_info.common_name if bird_info else None,
                    "scientific_name": bird_info.scientific_name if bird_info else None,
                    "summary": bird_info.summary if bird_info else None,
                    "family": bird_info.family if bird_info else None,
                    "order": bird_info.order if bird_info else None,
                    "genus": bird_info.genus if bird_info else None,
                    "local_image_path": bird_info.local_image_path if bird_info else None,
                    "conservation_status": bird_info.conservation_status if bird_info else None
                }
            ))
        return items

    @staticmethod
    def check_health() -> Dict[str, bool]:
        """Check if search service is ready."""
        return {
            "models_loaded": KDTreeService.is_ready(),
            "kdtree_ready": KDTreeService._kdtree is not None,
            "scaler_ready": KDTreeService._scaler is not None
        }
