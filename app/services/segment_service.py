"""
Segment service for query and import pipelines.
Handles audio loading, silence-aware segmentation, and saving segment files.
"""
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import librosa
import numpy as np
import soundfile as sf

from app.core.config import settings
from extract_features import extract_mfcc_only

logger = logging.getLogger(__name__)


class SegmentService:
    """Service for segmenting audio and saving segments."""

    @staticmethod
    def load_audio(file_path: str) -> tuple:
        try:
            y, sr = librosa.load(str(file_path), sr=settings.TARGET_SAMPLE_RATE, mono=True)
            return y, sr
        except Exception as exc:
            logger.error("Failed to load audio for segmentation: %s", str(exc))
            raise ValueError(f"Cannot load audio file: {str(exc)}")

    @staticmethod
    def segment_audio(file_path: str) -> List[Dict[str, Any]]:
        y, sr = SegmentService.load_audio(file_path)
        intervals = librosa.effects.split(
            y,
            top_db=settings.TOP_DB,
            frame_length=2048,
            hop_length=512
        )

        if len(intervals) == 0:
            return []

        active_chunks = [y[start:end] for start, end in intervals if end - start > 0]
        if not active_chunks:
            return []

        y_active = np.concatenate(active_chunks)
        if len(y_active) == 0:
            return []

        chunk_length = int(2 * sr)
        if len(y_active) > chunk_length:
            rms_frames = librosa.feature.rms(y=y_active, frame_length=2048, hop_length=512)[0]
            max_idx = int(np.argmax(rms_frames))
            start_sample = max_idx * 512
            start_sample = min(start_sample, len(y_active) - chunk_length)
            loudest_segment = y_active[start_sample: start_sample + chunk_length]
        else:
            loudest_segment = y_active

        p = float(np.sqrt(np.mean(loudest_segment**2))) if len(loudest_segment) > 0 else 0.0
        noise_rms_threshold = 0.1 * p

        query_segments: List[Dict[str, Any]] = []
        window_samples = int(settings.SEGMENT_WINDOW_SECONDS * sr)
        hop_samples = int(settings.SEGMENT_HOP_SECONDS * sr)
        min_samples = int(settings.MIN_SEGMENT_DURATION_SECONDS * sr)
        similarity_threshold = 20.0

        segment_index = 1
        for interval_index, (start, end) in enumerate(intervals):
            segment = y[start:end]
            if len(segment) < min_samples:
                continue

            if noise_rms_threshold <= 0:
                y_final = segment
            else:
                n_fft = 2048
                hop_length = 512
                stft = librosa.stft(segment, n_fft=n_fft, hop_length=hop_length)
                mag = np.abs(stft)
                phase = np.angle(stft)

                frame_rms = librosa.feature.rms(S=mag, frame_length=n_fft, hop_length=hop_length)[0]
                noise_mask = frame_rms < noise_rms_threshold

                if np.any(noise_mask):
                    noise_profile = np.median(mag[:, noise_mask], axis=1, keepdims=True)
                else:
                    noise_profile = np.median(mag, axis=1, keepdims=True)

                reduction_strength = 1.0
                floor_ratio = 0.1
                reduced = mag - (reduction_strength * noise_profile)
                floor = floor_ratio * noise_profile
                mag_clean = np.maximum(reduced, floor)
                stft_clean = mag_clean * np.exp(1j * phase)
                y_final = librosa.istft(stft_clean, hop_length=hop_length, length=len(segment))
                y_final = np.clip(y_final, -1.0, 1.0).astype(np.float32)

            total_samples = len(y_final)
            num_windows = (total_samples - window_samples) // hop_samples + 1
            if num_windows <= 0:
                continue

            current_start_idx = 0
            current_end_idx = window_samples
            current_mfcc = extract_mfcc_only(y_final[current_start_idx:current_end_idx], sr)

            def push_segment(start_idx: int, end_idx: int):
                nonlocal segment_index
                if len(query_segments) >= settings.MAX_QUERY_SEGMENTS:
                    return

                segment_audio = y_final[start_idx:end_idx]
                if len(segment_audio) < min_samples:
                    return

                query_segments.append({
                    "segment_index": segment_index,
                    "start_time": float((start + start_idx) / sr),
                    "end_time": float((start + end_idx) / sr),
                    "audio": segment_audio,
                    "sr": sr,
                    "duration": float((end_idx - start_idx) / sr)
                })
                segment_index += 1

            for w in range(1, num_windows):
                w_start_idx = w * hop_samples
                w_end_idx = w_start_idx + window_samples
                w_y = y_final[w_start_idx:w_end_idx]
                w_mfcc = extract_mfcc_only(w_y, sr)
                dist = np.linalg.norm(current_mfcc - w_mfcc)

                if dist < similarity_threshold:
                    current_end_idx = w_end_idx
                    current_mfcc = extract_mfcc_only(y_final[current_start_idx:current_end_idx], sr)
                else:
                    push_segment(current_start_idx, current_end_idx)
                    if len(query_segments) >= settings.MAX_QUERY_SEGMENTS:
                        return query_segments
                    current_start_idx = w_start_idx
                    current_end_idx = w_end_idx
                    current_mfcc = w_mfcc

            tail_start = (num_windows - 1) * hop_samples
            if tail_start + window_samples < total_samples:
                w_y = y_final[-window_samples:]
                w_mfcc = extract_mfcc_only(w_y, sr)
                dist = np.linalg.norm(current_mfcc - w_mfcc)
                if dist < similarity_threshold:
                    current_end_idx = total_samples
                else:
                    push_segment(current_start_idx, current_end_idx)
                    if len(query_segments) >= settings.MAX_QUERY_SEGMENTS:
                        return query_segments
                    current_start_idx = total_samples - window_samples
                    current_end_idx = total_samples

            push_segment(current_start_idx, current_end_idx)
            if len(query_segments) >= settings.MAX_QUERY_SEGMENTS:
                return query_segments

        return query_segments

    @staticmethod
    def ensure_segment_dir(label: str) -> Path:
        segment_dir = Path(settings.SEGMENT_SAVE_ROOT) / label
        segment_dir.mkdir(parents=True, exist_ok=True)
        return segment_dir

    @staticmethod
    def generate_segment_filename(
        original_filename: str,
        segment_index: int,
        existing_names: Set[str],
        target_dir: Path
    ) -> str:
        stem = Path(original_filename).stem
        base_name = f"{stem}_seg{segment_index}"
        candidate = f"{base_name}.wav"
        counter = 1

        while candidate in existing_names or (target_dir / candidate).exists():
            candidate = f"{base_name}_{counter}.wav"
            counter += 1

        existing_names.add(candidate)
        return candidate

    @staticmethod
    def save_segments(
        segments: List[Dict[str, Any]],
        label: str,
        original_filename: str
    ) -> List[Dict[str, Any]]:
        segment_dir = SegmentService.ensure_segment_dir(label)
        existing_names: Set[str] = set()
        saved_segments: List[Dict[str, Any]] = []

        for segment in segments:
            filename = SegmentService.generate_segment_filename(
                original_filename,
                segment["segment_index"],
                existing_names,
                segment_dir
            )
            file_path = segment_dir / filename

            sf.write(
                str(file_path),
                segment["audio"].astype(np.float32),
                segment["sr"],
                format="WAV",
                subtype="PCM_16"
            )

            saved_segments.append({
                "filename": filename,
                "filepath": str(file_path),
                "label": label,
                "original_filename": original_filename,
                "duration": segment["duration"],
                "sample_rate": segment["sr"],
                "audio": segment["audio"],
                "sr": segment["sr"]
            })

        return saved_segments
