import argparse
import sys
import json
import numpy as np
import pandas as pd
import joblib
import warnings
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from extract_features import extract_bird_features

# --- KHỞI TẠO CẤU HÌNH ---
load_dotenv()

import librosa
_orig_piptrack = librosa.piptrack

def patched_piptrack(*args, **kwargs):
    kwargs['hop_length'] = kwargs.get('hop_length', 1024)
    kwargs['fmin'] = kwargs.get('fmin', 150.0)
    kwargs['fmax'] = kwargs.get('fmax', 8000.0)
    return _orig_piptrack(*args, **kwargs)

librosa.piptrack = patched_piptrack

# --- PHẦN 1: KẾT NỐI CSDL ---
def get_db_engine():
    user = os.getenv("MYSQL_USER")
    password = os.getenv("MYSQL_PASSWORD")
    host = os.getenv("MYSQL_HOST")
    port = os.getenv("MYSQL_PORT")
    db_name = os.getenv("MYSQL_DATABASE")
    
    if not all([user, password, host, port, db_name]):
        return None
    
    conn_uri = f"mysql+pymysql://{user}:{password}@{host}:{port}/{db_name}"
    return create_engine(conn_uri)

# --- PHẦN 2: ENGINE TÌM KIẾM ---
def prepare_input_vector(f_dict):
    if f_dict is None: return None
    keys = ["energy_mean", "energy_var", "zcr_mean", "zcr_var", 
            "centroid_mean", "centroid_var", "rolloff_mean", "rolloff_var",
            "bandwidth_mean", "bandwidth_var", "harmonic_mean", "harmonic_var",
            "pitch_mean", "pitch_var", "silence_ratio"]
    for i in range(1, 14):
        keys.extend([f"mfcc{i}_mean", f"mfcc{i}_var"])
    try:
        return np.array([f_dict[k] for k in keys]).reshape(1, -1)
    except KeyError as e:
        return None

def run_search(audio_path, top_k=5):
    raw_features = extract_bird_features(audio_path)
    vector = prepare_input_vector(raw_features)
    if vector is None: return None

    try:
        tree = joblib.load("audio_kdtree.pkl")
        scaler = joblib.load("audio_scaler.pkl")
        df_bank = pd.read_csv("train_metadata_merged_features.csv")
        engine = get_db_engine()
    except Exception as e:
        print(f"[!] Lỗi nạp mô hình hoặc DB: {e}")
        return None

    vector_scaled = scaler.transform(vector)
    distances, indices = tree.query(vector_scaled, k=top_k)
    
    # 1. Lấy kết quả thô từ CSV đặc trưng
    matched = df_bank.iloc[indices[0]].copy()
    matched['similarity'] = 100 * np.exp(-distances[0] / 10.0)
    
    # 2. Truy vấn CSDL để lấy thông tin chi tiết các loài tìm được
    unique_labels = matched['label'].unique().tolist()
    labels_str = "('" + "','".join(unique_labels) + "')"
    
    query = f"SELECT * FROM bird_wiki_details WHERE primary_label IN {labels_str}"
    df_wiki = pd.read_sql(query, engine) if engine else pd.read_csv("bird_wikipedia_info.csv")

    # 3. Gộp và Nhóm dữ liệu
    res = pd.merge(matched, df_wiki, left_on='label', right_on='primary_label', how='left')
    return res

# --- PHẦN 3: XỬ LÝ ĐẦU RA ---
def format_output(results, is_json=False):
    if results is None: return
    
    # Nhóm theo loài chim
    grouped = results.groupby('common_name')
    
    output_data = []
    for name, group in grouped:
        first = group.iloc[0]
        species_info = {
            "species": name,
            "scientific_name": first.get('scientific_name'),
            "taxonomy": {
                "order": first.get('order'),
                "family": first.get('family'),
                "genus": first.get('genus')
            },
            "conservation_status": first.get('conservation_status'),
            "image_local": first.get('local_image_path'),
            "matches": group[['filename', 'similarity']].to_dict(orient='records')
        }
        output_data.append(species_info)

    if is_json:
        print(json.dumps(output_data, indent=4, ensure_ascii=False))
    else:
        print("\n" + "KẾT QUẢ TÌM KIẾM CHI TIẾT".center(90))
        for item in output_data:
            print("="*90)
            print(f"LOÀI: {item['species']} ({item['scientific_name']})")
            print(f"Phân loại: {item['taxonomy']['order']} > {item['taxonomy']['family']} > {item['taxonomy']['genus']}")
            print(f"Trạng thái bảo tồn: {item['conservation_status']}")
            print(f"Ảnh local: {item['image_local']}")
            print("-" * 30 + " Danh sách file khớp " + "-" * 30)
            for m in item['matches']:
                print(f"   - {m['filename']:<40} | Độ tương đồng: {m['similarity']:.2f}%")
        print("="*90 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=str, help="Đường dẫn file âm thanh")
    parser.add_argument("--json", action="store_true", help="Xuất kết quả định dạng JSON")
    args = parser.parse_args()
    
    if not args.json:
        print(f"[*] Đang phân tích âm thanh: {Path(args.file).name}...")
        
    results = run_search(args.file)
    format_output(results, is_json=args.json)