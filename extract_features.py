# ============================================================
# bird_feature_extractor.py
# ============================================================
#
# PIPELINE TRÍCH XUẤT ĐẶC TRƯNG TIẾNG CHIM
# INPUT  : đường dẫn file âm thanh
# OUTPUT : dictionary chứa feature vector
#
# Tối ưu:
# - Chạy nhanh
# - Chỉ load audio 1 lần
# - Dùng numpy vectorization
# - Không tính toán dư thừa
#
# ============================================================

import numpy as np
import librosa


# ============================================================
# CONFIG
# ============================================================

SR = 22050
N_MFCC = 13


# ============================================================
# HELPER
# ============================================================

def mean_var(x):
    return float(np.mean(x)), float(np.var(x))


# ============================================================
# FEATURE EXTRACTION
# ============================================================

def extract_mfcc_only(y, sr):
    """Hàm chạy siêu nhẹ, chỉ trích xuất MFCC để so sánh độ tương đồng (bỏ qua pyin, hpss rất nặng)"""
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=N_MFCC)
    return np.mean(mfcc, axis=1)

def extract_features_from_array(y, sr):
    duration = librosa.get_duration(y=y, sr=sr)

    # ========================================================
    # RMS ENERGY
    # ========================================================

    rms = librosa.feature.rms(y=y)[0]
    energy_mean, energy_var = mean_var(rms)

    # ========================================================
    # ZERO CROSSING RATE
    # ========================================================

    zcr = librosa.feature.zero_crossing_rate(y)[0]
    zcr_mean, zcr_var = mean_var(zcr)

    # ========================================================
    # SILENCE RATIO
    # ========================================================

    silence_ratio = float(
        np.mean(np.abs(y) < 0.01)
    )

    # ========================================================
    # SPECTRAL FEATURES
    # ========================================================

    centroid = librosa.feature.spectral_centroid(
        y=y,
        sr=sr
    )[0]

    bandwidth = librosa.feature.spectral_bandwidth(
        y=y,
        sr=sr
    )[0]

    rolloff = librosa.feature.spectral_rolloff(
        y=y,
        sr=sr
    )[0]

    centroid_mean, centroid_var = mean_var(centroid)

    bandwidth_mean, bandwidth_var = mean_var(bandwidth)

    rolloff_mean, rolloff_var = mean_var(rolloff)

    # ========================================================
    # HARMONICITY
    # ========================================================

    harmonic, _ = librosa.effects.hpss(y)

    harmonic_rms = librosa.feature.rms(
        y=harmonic
    )[0]

    harmonic_mean, harmonic_var = mean_var(
        harmonic_rms
    )

    # ========================================================
    # PITCH (F0)
    # ========================================================

    pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
    f0 = []
    for i in range(magnitudes.shape[1]):
        idx = magnitudes[:, i].argmax()
        pitch = pitches[idx, i]
        if pitch > 0:
            f0.append(pitch)
    f0 = np.array(f0)

    if len(f0) > 0:
        pitch_mean, pitch_var = mean_var(f0)
    else:
        pitch_mean, pitch_var = 0.0, 0.0

    # ========================================================
    # MFCC
    # ========================================================

    mfcc = librosa.feature.mfcc(
        y=y,
        sr=sr,
        n_mfcc=N_MFCC
    )

    mfcc_mean = np.mean(mfcc, axis=1)
    mfcc_var = np.var(mfcc, axis=1)

    # ========================================================
    # FINAL RESULT
    # ========================================================

    result = {

        # metadata
        "duration": duration,
        "sample_rate": sr,

        # energy
        "energy_mean": energy_mean,
        "energy_var": energy_var,

        # zcr
        "zcr_mean": zcr_mean,
        "zcr_var": zcr_var,

        # silence
        "silence_ratio": silence_ratio,

        # spectral
        "centroid_mean": centroid_mean,
        "centroid_var": centroid_var,

        "bandwidth_mean": bandwidth_mean,
        "bandwidth_var": bandwidth_var,

        "rolloff_mean": rolloff_mean,
        "rolloff_var": rolloff_var,

        # harmonic
        "harmonic_mean": harmonic_mean,
        "harmonic_var": harmonic_var,

        # pitch
        "pitch_mean": pitch_mean,
        "pitch_var": pitch_var,
    }

    # ========================================================
    # ADD MFCC
    # ========================================================

    for i in range(N_MFCC):

        result[f"mfcc{i+1}_mean"] = float(
            mfcc_mean[i]
        )

        result[f"mfcc{i+1}_var"] = float(
            mfcc_var[i]
        )

    return result

def extract_bird_features(audio_path):

    # ========================================================
    # LOAD AUDIO
    # ========================================================

    y, sr = librosa.load(
        audio_path,
        sr=SR,
        mono=True
    )

    return extract_features_from_array(y, sr)


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    AUDIO_PATH = "sample-3s.wav"

    features = extract_bird_features(
        AUDIO_PATH
    )

    print("\n========== FEATURES ==========\n")

    for k, v in features.items():
        print(f"{k}: {v}")