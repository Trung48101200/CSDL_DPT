import os
import random
from pathlib import Path
import tkinter as tk
from tkinter import ttk
import numpy as np
import librosa
import soundfile as sf
import pygame

# Khởi tạo pygame mixer để có thể phát âm thanh
pygame.mixer.init()

TEMP_ORIG = "temp_orig.wav"
TEMP_MIXED = "temp_mixed.wav"

class ThresholdTunerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Công Cụ Tinh Chỉnh x (Masking Threshold/Ngưỡng Nghe Thấy)")
        self.root.geometry("650x450")
        
        self.segment = None
        self.sr = 32000
        self.p_rms = 0.0
        self.current_file = ""
        
        self.create_widgets()
        self.load_random_file()
        
    def create_widgets(self):
        # Label hiển thị đường dẫn file
        self.lbl_file = tk.Label(self.root, text="File: Chưa tải", wraplength=600, fg="grey")
        self.lbl_file.pack(pady=15)
        
        # Label hiển thị năng lượng của đoạn 2 giây
        self.lbl_p = tk.Label(self.root, text="Năng lượng tiếng chim trung bình p (RMS) = 0.0", font=("Arial", 12, "bold"))
        self.lbl_p.pack(pady=5)
        
        # Vùng chứa Slider điều chỉnh x
        frame_slider = tk.Frame(self.root, bg="#f0f0f0", padx=10, pady=10)
        frame_slider.pack(pady=20, fill=tk.X, padx=20)
        
        tk.Label(frame_slider, text="Hệ số x (từ 0.01 đến 2.0): ", bg="#f0f0f0", font=("Arial", 10)).pack(side=tk.LEFT)
        
        self.val_x = tk.DoubleVar(value=0.5)
        # Slider chỉnh hệ số x
        self.slider_x = ttk.Scale(frame_slider, from_=0.01, to=2.0, orient=tk.HORIZONTAL, 
                                  variable=self.val_x, length=350, command=self.update_labels)
        self.slider_x.pack(side=tk.LEFT, padx=10)
        
        self.lbl_x_val = tk.Label(frame_slider, text="0.500", bg="#f0f0f0", font=("Arial", 10, "bold"), fg="red")
        self.lbl_x_val.pack(side=tk.LEFT)
        
        # Label hiển thị năng lượng nhiễu sau khi nhân x
        self.lbl_noise_rms = tk.Label(self.root, text="Năng lượng Noise cần tạo (x * p) = 0.0", fg="blue", font=("Arial", 11))
        self.lbl_noise_rms.pack(pady=5)
        
        # Vùng chứa các nút điều khiển
        frame_btn = tk.Frame(self.root)
        frame_btn.pack(pady=30)
        
        btn_random = tk.Button(frame_btn, text="Tải File Ngẫu Nhiên Khác", command=self.load_random_file, bg="#e0e0e0", height=2)
        btn_random.pack(side=tk.LEFT, padx=15)
        
        btn_play_orig = tk.Button(frame_btn, text="▶ Nghe Tiếng Chim Gốc (2s)", command=self.play_orig, bg="#aeeaaa", height=2)
        btn_play_orig.pack(side=tk.LEFT, padx=15)
        
        btn_play_mixed = tk.Button(frame_btn, text="▶ Nghe Thử Với Noise (+ Noise)", command=self.play_mixed, bg="#ffb3b3", height=2)
        btn_play_mixed.pack(side=tk.LEFT, padx=15)

    def find_all_audio_files(self):
        root_dir = Path("train_audio")
        if not root_dir.exists():
            return []
        return list(root_dir.rglob("*.ogg"))
        
    def load_random_file(self):
        pygame.mixer.stop() # Dừng mọi âm thanh đang phát
        
        files = self.find_all_audio_files()
        if not files:
            self.lbl_file.config(text="⚠️ Không tìm thấy thư mục 'train_audio' hoặc không có file .ogg nào.", fg="red")
            return
            
        chosen = random.choice(files)
        self.lbl_file.config(text=f"Đang phân tích: {chosen.name} ...")
        self.root.update()
        
        try:
            # Load âm thanh
            y, sr = librosa.load(str(chosen), sr=32000)
            
            # Cắt 1 đoạn dài 2 giây (nơi có mức năng lượng to nhất để chắc chắn là tiếng chim)
            chunk_length = 2 * sr
            if len(y) > chunk_length:
                # Tìm đoạn 2s có RMS lớn nhất
                rms_frames = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
                max_idx = np.argmax(rms_frames)
                start_sample = max_idx * 512
                # Tránh bị vượt index mảng
                start_sample = min(start_sample, len(y) - chunk_length)
                
                self.segment = y[start_sample : start_sample + chunk_length]
            else:
                self.segment = y
                
            self.sr = sr
            
            # Tính RMS (Năng lượng trung bình p) của đoạn 2 giây
            self.p_rms = float(np.sqrt(np.mean(self.segment**2)))
            self.current_file = chosen.name
            
            self.lbl_file.config(text=f"File: {self.current_file}", fg="black")
            self.lbl_p.config(text=f"Năng lượng tiếng chim trung bình p (RMS) = {self.p_rms:.6f}")
            
            # Lưu lại gốc
            sf.write(TEMP_ORIG, self.segment, self.sr, subtype='PCM_16')
            self.update_labels()
            
        except Exception as e:
            self.lbl_file.config(text=f"⚠️ Lỗi load file: {e}", fg="red")

    def update_labels(self, *args):
        x = self.val_x.get()
        self.lbl_x_val.config(text=f"{x:.3f}")
        
        noise_rms = x * self.p_rms
        self.lbl_noise_rms.config(text=f"Năng lượng Noise cần tạo (x * p) = {noise_rms:.6f}")

    def play_orig(self):
        pygame.mixer.stop()
        if not os.path.exists(TEMP_ORIG): return
        
        # Load và phát file gốc
        sound = pygame.mixer.Sound(TEMP_ORIG)
        sound.play()

    def play_mixed(self):
        pygame.mixer.stop()
        if self.segment is None: return
        
        x = self.val_x.get()
        noise_rms_target = x * self.p_rms
        
        # Tạo âm thanh "Beep" (Sine wave 1000Hz) để làm tín hiệu che lấp thay vì nhiễu trắng
        t = np.linspace(0, len(self.segment) / self.sr, num=len(self.segment), endpoint=False)
        noise = np.sin(2 * np.pi * 1000 * t)  # Tần số 1000 Hz
        
        # Chuẩn hóa năng lượng Beep về RMS = 1, sau đó nhân với năng lượng mong muốn là target
        noise = noise / np.sqrt(np.mean(noise**2)) * noise_rms_target
        
        # Cộng gộp noise (mức bằng x*p) vào gốc
        mixed = self.segment + noise
        
        # Tránh bị Clipping (Rè loa)
        mixed = np.clip(mixed, -1.0, 1.0)
        
        # Lưu ra file tạm và phát
        sf.write(TEMP_MIXED, mixed, self.sr, subtype='PCM_16')
        sound = pygame.mixer.Sound(TEMP_MIXED)
        sound.play()

if __name__ == "__main__":
    root = tk.Tk()
    app = ThresholdTunerApp(root)
    root.mainloop()
