import argparse
import os
import sys
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd
import soundfile as sf
from sqlalchemy import create_engine, text

# --- 1. QUẢN LÝ BIẾN MÔI TRƯỜNG ---
def load_env_file(env_path: Path):
    """Tự động tải biến từ file .env vào os.environ"""
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)

def get_env_default(name, fallback):
    return os.getenv(name, fallback)

# --- 2. KẾT NỐI VÀ KHỞI TẠO DATABASE ---
def build_engine(user, password, host, port, database=None):
    """Tạo SQLAlchemy engine để kết nối MySQL"""
    db_url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database if database else ''}"
    return create_engine(db_url)

def ensure_database(user, password, host, port, database):
    """Đảm bảo Database tồn tại, nếu chưa có sẽ tự động tạo mới"""
    server_engine = build_engine(user, password, host, port)
    with server_engine.begin() as conn:
        conn.execute(
            text(f"CREATE DATABASE IF NOT EXISTS `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        )

# --- 3. LOGIC IMPORT CHÍNH ---
def prepare_original_audios(df: pd.DataFrame) -> pd.DataFrame:
    if 'primary_label' not in df.columns or 'filename' not in df.columns:
        raise ValueError(
            "CSV for original_audios phải có cột 'primary_label' và 'filename'."
        )

    df = df.copy()
    df['label'] = df['primary_label'].astype(str)
    df['original_filename'] = df['filename'].astype(str).apply(lambda v: Path(v).name)
    df['file_path'] = df['filename'].astype(str)

    if 'duration' in df.columns:
        df['duration'] = pd.to_numeric(df['duration'], errors='coerce')
    else:
        df['duration'] = None

    if 'sample_rate' in df.columns:
        df['sample_rate'] = pd.to_numeric(df['sample_rate'], errors='coerce')
    else:
        df['sample_rate'] = None

    return df[[
        'original_filename',
        'label',
        'file_path',
        'duration',
        'sample_rate'
    ]]


def run_import(args):
    print(f"[*] Đang nạp dữ liệu từ: {args.csv}")
    df = pd.read_csv(args.csv)

    # DỌN DẸP DỮ LIỆU: Tự động xóa cột image_url nếu tồn tại
    if 'image_url' in df.columns:
        df = df.drop(columns=['image_url'])
        print("[+] Đã tự động loại bỏ cột 'image_url' để tiết kiệm không gian DB.")

    # Nếu đang import bảng original_audios, chuyển đổi dữ liệu sang schema mới
    if args.table == 'original_audios':
        df = prepare_original_audios(df)

    # Đảm bảo DB tồn tại và tạo kết nối
    ensure_database(args.user, args.password, args.host, args.port, args.database)
    engine = build_engine(args.user, args.password, args.host, args.port, args.database)

    print(f"[*] Đang import {len(df)} dòng vào database '{args.database}', table '{args.table}'...")
    
    # Thực hiện chèn dữ liệu
    df.to_sql(
        args.table,
        con=engine,
        if_exists=args.if_exists,
        index=False,
        chunksize=args.chunksize,
        method="multi"
    )

    # THIẾT LẬP KHÓA CHÍNH: Nếu import bảng Wiki, tự động gán primary_label làm khóa
    if args.table == "bird_wiki_details" and "primary_label" in df.columns:
        try:
            with engine.connect() as conn:
                conn.execute(text(f"ALTER TABLE {args.table} MODIFY COLUMN primary_label VARCHAR(50) PRIMARY KEY;"))
                conn.commit()
                print("[+] Đã thiết lập 'primary_label' làm Primary Key thành công.")
        except Exception as e:
            print(f"[!] Bỏ qua bước set Primary Key (có thể do đã thiết lập trước): {e}")

    return len(df), list(df.columns)

# --- 4. CẤU HÌNH THAM SỐ DÒNG LỆNH (CLI) ---
def main():
    # Tải cấu hình từ .env
    load_env_file(Path.cwd() / ".env")
    
    parser = argparse.ArgumentParser(description="Công cụ Import CSV đa năng vào MySQL")
    
    # Tham số cấu hình file và bảng
    parser.add_argument("--csv", required=True, help="Đường dẫn file CSV cần import")
    parser.add_argument("--table", required=True, help="Tên bảng mục tiêu trong MySQL")
    
    # Lấy thông tin DB mặc định từ .env, nếu không có sẽ lấy giá trị default
    parser.add_argument("--user", default=get_env_default("MYSQL_USER", "root"))
    parser.add_argument("--password", default=get_env_default("MYSQL_PASSWORD", ""))
    parser.add_argument("--host", default=get_env_default("MYSQL_HOST", "127.0.0.1"))
    parser.add_argument("--port", default=get_env_default("MYSQL_PORT", "3306"))
    parser.add_argument("--database", default=get_env_default("MYSQL_DATABASE", "audio_db"))
    
    # Cấu hình cách import
    parser.add_argument("--if-exists", default="replace", choices=["fail", "replace", "append"], 
                        help="Hành động khi bảng đã tồn tại (mặc định: replace)")
    parser.add_argument("--chunksize", type=int, default=1000, 
                        help="Số dòng insert mỗi lần (giúp tránh lỗi bộ nhớ với file lớn)")

    args = parser.parse_args()

    try:
        total_rows, final_columns = run_import(args)
        
        print("\n" + "="*60)
        print("HOÀN TẤT IMPORT DỮ LIỆU")
        print(f"   • Cơ sở dữ liệu : {args.database}")
        print(f"   • Bảng mục tiêu : {args.table}")
        print(f"   • Tổng số dòng  : {total_rows}")
        print(f"   • Cột đã lưu    : {', '.join(final_columns)}")
        print("="*60)
        
    except Exception as exc:
        print(f"\n[!] LỖI HỆ THỐNG: {exc}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()