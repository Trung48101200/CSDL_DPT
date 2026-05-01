import concurrent.futures
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

import librosa
import numpy as np
import pandas as pd
import soundfile as sf
from tqdm import tqdm

from extract_features import extract_features_from_array, extract_mfcc_only


@dataclass
class NewPreprocessConfig:
    input_metadata: str = "train_metadata.csv"
    rating_filtered_metadata: str = "train_metadata_rating_filtered.csv"
    duration_filtered_metadata: str = "train_metadata_duration_filtered.csv"

    train_audio_dir: str = "train_audio"
    
    # "1 tệp" được hiểu là 1 thư mục chứa các file sau cùng
    bird_sounds_only_dir: str = "bird_sounds_only"

    min_rating: float = 4.5
    duration_tolerance: float = 60.0  # 1 phút
    top_db: int = 30  # Ngưỡng decibel để giới hạn khoảng lặng
    min_segment_duration: float = 2.0  # Bỏ qua các đoạn ngắn dưới 2 giây
    target_sr: int = 32000  # Đồng bộ tần số lấy mẫu cho tất cả file
    
    # Cấu hình cắt cửa sổ trượt (Sliding Window Overlap)
    window_length: float = 2.0  # Độ dài file xuất ra (2.0 giây)
    hop_length: float = 1.0     # Bước trượt (1.0 giây)
    
    # Cấu hình gộp đoạn theo đặc trưng
    similarity_threshold: float = 20.0
    merged_features_csv: str = "train_metadata_merged_features.csv"
    max_workers: int = 12  # Tăng số luồng lên 12 (máy có 16 luồng) để chạy nhanh hơn


def step1_filter_rating(cfg: NewPreprocessConfig) -> pd.DataFrame:
    print("Bước 1: Lọc các file có rating > 4.5")
    df = pd.read_csv(cfg.input_metadata)
    df_filtered = df[df["rating"] > cfg.min_rating].copy()
    
    df_filtered.to_csv(cfg.rating_filtered_metadata, index=False)
    print(f"-> Đã giữ lại {len(df_filtered)} files.")
    print(f"-> Đã lưu danh sách vào CSV: {cfg.rating_filtered_metadata}\n")
    return df_filtered


def step2_filter_duration(cfg: NewPreprocessConfig, df: pd.DataFrame) -> pd.DataFrame:
    print("Bước 2: Tính độ dài trung bình và lọc trong khoảng +/- 1 phút")
    valid_rows = []
    
    print("Đang tính độ dài các file audio...")
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Tính độ dài (Duration)"):
        rel_path = row["filename"]
        audio_path = Path(cfg.train_audio_dir) / rel_path
        
        if not audio_path.exists():
            continue
            
        try:
            # Ưu tiên lấy duration bằng soundfile (nhanh chóng do không cần load toàn bộ file)
            info = sf.info(str(audio_path))
            dur = info.duration
        except Exception:
            try:
                # Fallback sang thư viện librosa
                dur = librosa.get_duration(path=str(audio_path))
            except Exception:
                # Fallback cuối cùng bằng cách load vật lý
                try:
                    y, sr = librosa.load(str(audio_path), sr=None)
                    dur = len(y) / float(sr)
                except Exception:
                    continue
                
        row_dict = row.to_dict()
        row_dict['duration'] = dur
        valid_rows.append(row_dict)

    df_valid = pd.DataFrame(valid_rows)
    
    if len(df_valid) == 0:
        print("Không tìm thấy file audio hợp lệ nào!")
        return df_valid

    avg_duration = df_valid['duration'].mean()
    print(f"\n-> Độ dài trung bình của các file là: {avg_duration:.2f} giây")
    
    # Lọc những file có độ dài chênh lệch không quá 1 phút (60 giây)
    min_dur = avg_duration - cfg.duration_tolerance
    max_dur = avg_duration + cfg.duration_tolerance
    
    df_duration_filtered = df_valid[
        (df_valid['duration'] >= min_dur) & (df_valid['duration'] <= max_dur)
    ].copy()
    
    df_duration_filtered.to_csv(cfg.duration_filtered_metadata, index=False)
    print(f"-> Đã lọc ra và giữ lại {len(df_duration_filtered)} files thuộc (+/- 1 phút).")
    print(f"-> Đã lưu danh sách vào CSV: {cfg.duration_filtered_metadata}\n")
    
    return df_duration_filtered


def process_single_file(row_data, cfg, out_dir, x_threshold_multiplier):
    idx, row = row_data
    rel_path = row["filename"]
    audio_path = Path(cfg.train_audio_dir) / rel_path
    
    file_extracted_features = []
    processed_count = 0
    
    if not audio_path.exists():
        return processed_count, file_extracted_features
        
    try:
        # Tải âm thanh vật lý để xử lý (đồng bộ Sample Rate)
        y, sr = librosa.load(str(audio_path), sr=cfg.target_sr)
        
        # --- 3.1. CẮT KHOẢNG LẶNG TUYỆT ĐỐI (Timeline Trimming) ---
        intervals = librosa.effects.split(y, top_db=cfg.top_db, frame_length=2048, hop_length=512)
        
        if len(intervals) == 0:
            return processed_count, file_extracted_features
            
        y_active = np.concatenate([y[start:end] for start, end in intervals])
        
        if len(y_active) == 0:
            return processed_count, file_extracted_features
        
        chunk_length = 2 * sr
        if len(y_active) > chunk_length:
            rms_frames = librosa.feature.rms(y=y_active, frame_length=2048, hop_length=512)[0]
            max_idx = int(np.argmax(rms_frames))
            start_sample = max_idx * 512
            start_sample = min(start_sample, len(y_active) - chunk_length)
            loudest_segment = y_active[start_sample : start_sample + chunk_length]
        else:
            loudest_segment = y_active
            
        p = float(np.sqrt(np.mean(loudest_segment**2)))
        noise_rms_threshold = x_threshold_multiplier * p
        
        label = Path(rel_path).parent.name
        file_out_dir = out_dir / label
        file_out_dir.mkdir(parents=True, exist_ok=True)
        
        # --- 3.2. KHỬ NHIỄU PHỔ & XUẤT RA TỪNG SEGMENT ĐỘC LẬP ---
        for i, (start, end) in enumerate(intervals):
            segment = y[start:end]
            
            if len(segment) < cfg.min_segment_duration * sr:
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
                
            # --- 3.3. CẮT CỬA SỔ TRƯỢT VÀ GỘP BẰNG ĐẶC TRƯNG ---
            window_samples = int(cfg.window_length * sr)
            hop_samples = int(cfg.hop_length * sr)
            total_samples = len(y_final)
            
            num_windows = (total_samples - window_samples) // hop_samples + 1
            if num_windows <= 0:
                continue
            
            current_start_idx = 0
            current_end_idx = window_samples
            current_mfcc = extract_mfcc_only(y_final[current_start_idx:current_end_idx], sr)
            
            merged_idx = 0
            for w in range(1, num_windows):
                w_start_idx = w * hop_samples
                w_end_idx = w_start_idx + window_samples
                w_y = y_final[w_start_idx:w_end_idx]
                w_mfcc = extract_mfcc_only(w_y, sr)
                
                dist = np.linalg.norm(current_mfcc - w_mfcc)
                
                if dist < cfg.similarity_threshold:
                    current_end_idx = w_end_idx
                    current_mfcc = extract_mfcc_only(y_final[current_start_idx:current_end_idx], sr)
                else:
                    merged_y = y_final[current_start_idx:current_end_idx]
                    file_name = f"{audio_path.stem}_seg{i}_m{merged_idx}.wav"
                    out_path = file_out_dir / file_name
                    sf.write(str(out_path), merged_y, sr)
                    
                    final_features = extract_features_from_array(merged_y, sr)
                    final_features["filename"] = file_name
                    final_features["original_filename"] = f"{audio_path.stem}.ogg"
                    final_features["label"] = label
                    file_extracted_features.append(final_features)
                    
                    processed_count += 1
                    merged_idx += 1
                    
                    current_start_idx = w_start_idx
                    current_end_idx = w_end_idx
                    current_mfcc = w_mfcc
            
            # Xử lý đoạn đuôi (nếu dư ra khúc cuối)
            tail_start = (num_windows - 1) * hop_samples
            if tail_start + window_samples < total_samples:
                w_y = y_final[-window_samples:]
                w_mfcc = extract_mfcc_only(w_y, sr)
                dist = np.linalg.norm(current_mfcc - w_mfcc)
                
                if dist < cfg.similarity_threshold:
                    current_end_idx = total_samples
                    current_mfcc = extract_mfcc_only(y_final[current_start_idx:current_end_idx], sr)
                else:
                    merged_y = y_final[current_start_idx:current_end_idx]
                    file_name = f"{audio_path.stem}_seg{i}_m{merged_idx}.wav"
                    out_path = file_out_dir / file_name
                    sf.write(str(out_path), merged_y, sr)
                    
                    final_features = extract_features_from_array(merged_y, sr)
                    final_features["filename"] = file_name
                    final_features["original_filename"] = f"{audio_path.stem}.ogg"
                    final_features["label"] = label
                    file_extracted_features.append(final_features)
                    
                    processed_count += 1
                    merged_idx += 1
                    
                    current_start_idx = total_samples - window_samples
                    current_end_idx = total_samples
                    current_mfcc = w_mfcc

            # Lưu đoạn cuối cùng còn sót lại
            merged_y = y_final[current_start_idx:current_end_idx]
            file_name = f"{audio_path.stem}_seg{i}_m{merged_idx}.wav"
            out_path = file_out_dir / file_name
            sf.write(str(out_path), merged_y, sr)
            
            final_features = extract_features_from_array(merged_y, sr)
            final_features["filename"] = file_name
            final_features["original_filename"] = f"{audio_path.stem}.ogg"
            final_features["label"] = label
            file_extracted_features.append(final_features)
            processed_count += 1
            
        return processed_count, file_extracted_features
        
    except Exception as e:
        return 0, []


def step3_extract_bird_sounds(cfg: NewPreprocessConfig, df: pd.DataFrame):
    print("Bước 3: Trích xuất tiếng chim (Cắt khoảng lặng tuyệt đối & Khử nhiễu phổ bằng ngưỡng nghe thấy)")
    out_dir = Path(cfg.bird_sounds_only_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    x_threshold_multiplier = 0.1
    
    total_processed_count = 0
    
    # Xóa file CSV cũ nếu có để lúc chạy lại không bị đúp dữ liệu
    if Path(cfg.merged_features_csv).exists():
        Path(cfg.merged_features_csv).unlink()
        
    max_workers = cfg.max_workers
    print(f"-> Khởi động chế độ Đa luồng (Multiprocessing) với {max_workers} CPU cores...")
    
    row_data_list = list(df.iterrows())
    
    from functools import partial
    func = partial(process_single_file, cfg=cfg, out_dir=out_dir, x_threshold_multiplier=x_threshold_multiplier)
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(func, rd): rd for rd in row_data_list}
        
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="Tách tiếng chim"):
            try:
                count, features = future.result()
                total_processed_count += count
                
                # Cứ xong 1 file là lưu nối vào CSV ngay (chống mất dữ liệu)
                if len(features) > 0:
                    df_chunk = pd.DataFrame(features)
                    # Sắp xếp original_filename lên đầu
                    cols = ['filename', 'original_filename', 'label'] + [c for c in df_chunk.columns if c not in ['filename', 'original_filename', 'label']]
                    df_chunk = df_chunk[cols]
                    
                    file_exists = Path(cfg.merged_features_csv).exists()
                    df_chunk.to_csv(cfg.merged_features_csv, mode='a', header=not file_exists, index=False)
                    
            except Exception as e:
                pass
                
    print(f"\n-> Hoàn thành! Đã tạo ra tổng cộng {total_processed_count} đoạn âm thanh đã gộp.")
    print(f"-> Dữ liệu âm thanh được lưu trong thư mục: {cfg.bird_sounds_only_dir}")
    print(f"-> Toàn bộ đặc trưng đã được lưu an toàn vào: {cfg.merged_features_csv}")


def run_new_pipeline():
    cfg = NewPreprocessConfig()
    
    df_rating = step1_filter_rating(cfg)
    if len(df_rating) > 0:
        df_duration = step2_filter_duration(cfg, df_rating)
        
        if len(df_duration) > 0:
            step3_extract_bird_sounds(cfg, df_duration)
            print("\n----- Pipeline Xử lý Mới đã chạy Dừng Tại Đây! -----")


if __name__ == "__main__":
    from multiprocessing import freeze_support
    freeze_support()
    run_new_pipeline()
