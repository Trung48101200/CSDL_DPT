"""
Feature extractor service.
Handles audio feature extraction using librosa.
Coordinates with the core extract_features module that defines the 41 audio features.
"""
import logging
from typing import Any, Dict, Optional
import numpy as np
import librosa
from pathlib import Path
import sys
from os.path import dirname, abspath

# Import the core feature extraction function
sys.path.insert(0, dirname(dirname(dirname(abspath(__file__)))))
from extract_features import extract_features_from_array, extract_bird_features

logger = logging.getLogger(__name__)


class FeatureExtractorService:
    """
    Service for extracting 41 audio features from sound files.
    
    Wraps the core extract_features module to provide a service interface.
    Features extracted:
    - Energy (mean, var)
    - Zero Crossing Rate (mean, var)
    - Spectral Centroid (mean, var)
    - Spectral Bandwidth (mean, var)
    - Spectral Rolloff (mean, var)
    - Harmonicity (mean, var)
    - Pitch/F0 (mean, var)
    - Silence Ratio
    - MFCC 1-13 (mean and var each)
    Total: 2*13 + 15 = 41 features
    """

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

    # Configuration
    TARGET_SAMPLE_RATE = 32000

    @staticmethod
    def load_audio(file_path: str, sr: int = TARGET_SAMPLE_RATE) -> tuple:
        """
        Load audio file with specified sample rate.
        
        Args:
            file_path: Path to audio file
            sr: Target sample rate (default: 32000 Hz)
            
        Returns:
            Tuple of (audio_array, sample_rate)
            
        Raises:
            ValueError: If file cannot be loaded
        """
        try:
            y, sr_loaded = librosa.load(str(file_path), sr=sr, mono=True)
            duration = len(y) / sr
            logger.info(f"Loaded audio: {file_path}, duration: {duration:.2f}s, sr: {sr_loaded}Hz")
            return y, sr_loaded
        except Exception as e:
            logger.error(f"Failed to load audio {file_path}: {str(e)}")
            raise ValueError(f"Cannot load audio file: {str(e)}")


    @staticmethod
    def extract_all_features(file_path: str) -> Dict[str, float]:
        """
        Extract all 41 audio features from file using the core extract_features module.
        
        This method wraps extract_bird_features to provide a service interface.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Dictionary with all 41 features:
            - energy_mean, energy_var
            - zcr_mean, zcr_var
            - centroid_mean, centroid_var
            - bandwidth_mean, bandwidth_var
            - rolloff_mean, rolloff_var
            - harmonic_mean, harmonic_var
            - pitch_mean, pitch_var
            - silence_ratio
            - mfcc1_mean, mfcc1_var, ..., mfcc13_mean, mfcc13_var
            - duration, sample_rate
            
        Raises:
            ValueError: If extraction fails
        """
        try:
            logger.info(f"Extracting 41 features from {file_path}")
            
            # Use the core extract_bird_features function
            features = extract_bird_features(file_path)
            
            if features is None:
                raise ValueError("Feature extraction returned None")
            
            logger.info(f"Successfully extracted features from {file_path}")
            return features
            
        except Exception as e:
            logger.error(f"Failed to extract features from {file_path}: {str(e)}")
            raise ValueError(f"Feature extraction failed: {str(e)}")

    @staticmethod
    def extract_features_from_array(y: np.ndarray, sr: int) -> Dict[str, float]:
        """
        Extract all 41 audio features from an audio array.
        
        Wrapper around the core extract_features_from_array function.
        
        Args:
            y: Audio array
            sr: Sample rate
            
        Returns:
            Dictionary with all 41 features
            
        Raises:
            ValueError: If extraction fails
        """
        try:
            logger.info(f"Extracting 41 features from audio array, sr={sr}, duration={len(y)/sr:.2f}s")
            features = extract_features_from_array(y, sr)
            logger.info(f"Successfully extracted features from audio array")
            return features
            
        except Exception as e:
            logger.error(f"Failed to extract features from array: {str(e)}")
            raise ValueError(f"Feature extraction failed: {str(e)}")

    @staticmethod
    def select_feature_dict(features: Dict[str, Any]) -> Dict[str, float]:
        """Keep only the expected 41 feature keys from an extracted dictionary."""
        return {
            key: float(features[key])
            for key in FeatureExtractorService.FEATURE_ORDER
            if key in features and features[key] is not None
        }
