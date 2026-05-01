import argparse
from pathlib import Path
import librosa
import numpy as np
import pandas as pd
import soundfile as sf
from extract_features import extract_features_from_array, extract_mfcc_only

def process_single_input(input_audio_path: str, output_dir: str = "output_single_test"):
    audio_path = Path(input_audio_path)
    if not audio_path.exists():
        print(f"❌ File '{input_audio_path}' không tồn tại!")
        return

    out_dir = Path(output_dir)
    file_out_dir = out_dir / audio_path.stem
    file_out_dir.mkdir(parents=True, exist_ok=True)
    
    csv_out_path = out_dir / f"{audio_path.stem}_features.csv"
    
    # --- Cấu hình giống y hệt file preprocess_audio.py ---
    top_db = 30
    x_threshold_multiplier = 0.1
    min_segment_duration = 2.0
    target_sr = 32000
    window_length = 2.0
    hop_length = 1.0
    similarity_threshold = 20.0
    
    print(f"🎵 Đang phân tích file: {audio_path.name}")
    print(f"⏳ Vui lòng đợi trong giây lát...")
    
    try:
        # Load audio và chuẩn hóa Sample Rate
        y, sr = librosa.load(str(audio_path), sr=target_sr)
        
        # Cắt khoảng lặng
        intervals = librosa.effects.split(y, top_db=top_db, frame_length=2048, hop_length=512)
        if len(intervals) == 0:
            print("⚠️ File toàn khoảng lặng, không có âm thanh thực tế!")
            return
            
        y_active = np.concatenate([y[start:end] for start, end in intervals])
        if len(y_active) == 0: return
        
        # Tìm RMS (p) lớn nhất từ đoạn 2s
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
        
        file_extracted_features = []
        processed_count = 0
        
        for i, (start, end) in enumerate(intervals):
            segment = y[start:end]
            if len(segment) < min_segment_duration * sr:
                continue
                
            # Khử nhiễu phổ
            if noise_rms_threshold <= 0:
                y_final = segment
            else:
                n_fft = 2048
                hop_length_stft = 512
                stft = librosa.stft(segment, n_fft=n_fft, hop_length=hop_length_stft)
                mag = np.abs(stft)
                phase = np.angle(stft)
                
                frame_rms = librosa.feature.rms(S=mag, frame_length=n_fft, hop_length=hop_length_stft)[0]
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
                y_final = librosa.istft(stft_clean, hop_length=hop_length_stft, length=len(segment))
                y_final = np.clip(y_final, -1.0, 1.0).astype(np.float32)
                
            # Cắt cửa sổ trượt & gộp
            window_samples = int(window_length * sr)
            hop_samples = int(hop_length * sr)
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
                
                if dist < similarity_threshold:
                    current_end_idx = w_end_idx
                    current_mfcc = extract_mfcc_only(y_final[current_start_idx:current_end_idx], sr)
                else:
                    merged_y = y_final[current_start_idx:current_end_idx]
                    file_name = f"{audio_path.stem}_seg{i}_m{merged_idx}.wav"
                    out_path = file_out_dir / file_name
                    sf.write(str(out_path), merged_y, sr)
                    
                    final_features = extract_features_from_array(merged_y, sr)
                    final_features["filename"] = file_name
                    final_features["original_filename"] = audio_path.name
                    final_features["label"] = "unknown" # Cột nhãn để trống vì file test chưa biết là chim gì
                    file_extracted_features.append(final_features)
                    
                    processed_count += 1
                    merged_idx += 1
                    
                    current_start_idx = w_start_idx
                    current_end_idx = w_end_idx
                    current_mfcc = w_mfcc
            
            # Xử lý đoạn đuôi
            tail_start = (num_windows - 1) * hop_samples
            if tail_start + window_samples < total_samples:
                w_y = y_final[-window_samples:]
                w_mfcc = extract_mfcc_only(w_y, sr)
                dist = np.linalg.norm(current_mfcc - w_mfcc)
                if dist < similarity_threshold:
                    current_end_idx = total_samples
                else:
                    merged_y = y_final[current_start_idx:current_end_idx]
                    file_name = f"{audio_path.stem}_seg{i}_m{merged_idx}.wav"
                    out_path = file_out_dir / file_name
                    sf.write(str(out_path), merged_y, sr)
                    
                    final_features = extract_features_from_array(merged_y, sr)
                    final_features["filename"] = file_name
                    final_features["original_filename"] = audio_path.name
                    final_features["label"] = "unknown"
                    file_extracted_features.append(final_features)
                    
                    processed_count += 1
                    merged_idx += 1
                    
                    current_start_idx = total_samples - window_samples
                    current_end_idx = total_samples
                    
            merged_y = y_final[current_start_idx:current_end_idx]
            file_name = f"{audio_path.stem}_seg{i}_m{merged_idx}.wav"
            out_path = file_out_dir / file_name
            sf.write(str(out_path), merged_y, sr)
            
            final_features = extract_features_from_array(merged_y, sr)
            final_features["filename"] = file_name
            final_features["original_filename"] = audio_path.name
            final_features["label"] = "unknown"
            file_extracted_features.append(final_features)
            processed_count += 1
            
        # Xuất file CSV
        if len(file_extracted_features) > 0:
            df = pd.DataFrame(file_extracted_features)
            cols = ['filename', 'original_filename', 'label'] + [c for c in df.columns if c not in ['filename', 'original_filename', 'label']]
            df = df[cols]
            df.to_csv(csv_out_path, index=False)
            print(f"✅ Hoàn thành! Đã tách được {processed_count} đoạn âm thanh sạch.")
            print(f"📂 Các file wav nhỏ đã lưu tại: {file_out_dir}")
            print(f"📊 Đặc trưng đã xuất ra CSV: {csv_out_path}")
        else:
            print("⚠️ Không trích xuất được đoạn âm thanh hợp lệ nào (có thể file quá ngắn hoặc chỉ toàn tạp âm).")
    except Exception as e:
        print(f"❌ Lỗi khi xử lý file: {e}")

if __name__ == "__main__":
    import sys
    
    # Nếu chạy bằng dòng lệnh truyền tên file vào:
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        process_single_input(input_file)
    else:
        # Nếu không truyền tên file, tự động mở hộp thoại GUI chọn file
        import tkinter as tk
        from tkinter import filedialog
        
        root = tk.Tk()
        root.withdraw() # Ẩn cửa sổ nền của tkinter đi, chỉ hiện hộp thoại chọn file
        
        print("📂 Đang mở hộp thoại chọn file...")
        file_path = filedialog.askopenfilename(
            title="Chọn file âm thanh cần xử lý",
            filetypes=[("Audio Files", "*.wav *.ogg *.mp3 *.flac"), ("All Files", "*.*")]
        )
        
        if file_path:
            process_single_input(file_path)
        else:
            print("❌ Bạn đã hủy chọn file. Chương trình kết thúc.")
