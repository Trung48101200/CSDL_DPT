# Bird Sound CBIR API - Hướng dẫn khởi động

Tài liệu này hướng dẫn cách thiết lập và chạy hệ thống tìm kiếm tiếng chim bằng CBIR.

## 1. Yêu cầu trước khi chạy

- Python 3.8 trở lên
- MySQL server đang chạy
- FFmpeg đã cài và có trong PATH
- Đã kích hoạt virtual environment

Trên Windows:
- Tải FFmpeg từ https://ffmpeg.org/download.html
- Thêm thư mục `bin` của FFmpeg vào PATH

Trên macOS:
- `brew install ffmpeg`

Trên Ubuntu/Debian:
- `sudo apt-get install ffmpeg`

## 2. Tạo môi trường Python

Windows PowerShell:
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Windows Command Prompt:
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

macOS/Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

## 3. Cài đặt dependencies

Sau khi kích hoạt môi trường:
```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

## 4. Cấu hình môi trường

1. Copy file `.env.example` thành `.env`:
- Windows: `copy .env.example .env`
- macOS/Linux: `cp .env.example .env`

2. Chỉnh sửa `.env` với thông tin MySQL:
```env
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DATABASE=audio_db
```

## 5. Chuẩn bị database

1. Tạo database và tables bằng SQLAlchemy:
```bash
python -c "from app.core.database import init_db; import asyncio; asyncio.run(init_db())"
```

2. Import dữ liệu từ CSV:
```bash
python master_importer.py --csv train_metadata_merged_features.csv --table audio_features
python master_importer.py --csv bird_wikipedia_info_final.csv --table bird_wiki_details
python master_importer.py --csv original_audios.csv --table original_audios
```

3. Sau khi import `audio_features` và `original_audios`, chạy thêm lệnh SQL trong MySQL để tạo các cột cần thiết:

```sql
ALTER TABLE audio_features
  ADD COLUMN id INT AUTO_INCREMENT PRIMARY KEY FIRST,
  ADD COLUMN created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ADD COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;

ALTER TABLE original_audios
  ADD COLUMN id INT AUTO_INCREMENT PRIMARY KEY FIRST,
  ADD COLUMN created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ADD COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;
```

Nếu bảng đã có cột `id`, bạn chỉ cần đảm bảo `created_at` và `updated_at` tồn tại.

## 6. Chuẩn bị mô hình ML

Đảm bảo các file sau tồn tại trong thư mục gốc:
- `audio_kdtree.pkl`
- `audio_scaler.pkl`

Nếu chưa có, tạo chúng từ dữ liệu `audio_features` bằng script ví dụ:

```python
import numpy as np
import joblib
from scipy.spatial import cKDTree
from sklearn.preprocessing import StandardScaler
from app.core.database import SessionLocal
from app.repositories.audio_repository import AudioRepository

db = SessionLocal()
vectors, audio_ids = AudioRepository.get_all_features_as_vectors(db)
vectors = np.array(vectors, dtype=np.float32)
scaler = StandardScaler()
scaled_vectors = scaler.fit_transform(vectors)
kdtree = cKDTree(scaled_vectors)
joblib.dump({"kdtree": kdtree, "audio_ids": audio_ids}, "audio_kdtree.pkl")
joblib.dump(scaler, "audio_scaler.pkl")
```

## 7. Chạy API server

Local development:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Truy cập API:
- http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 8. Các endpoint chính

Root:
- `GET /` - thông tin dịch vụ
- `GET /health` - kiểm tra đơn giản
- `GET /api/search/health` - kiểm tra chi tiết

Audio:
- `GET /api/audio` - danh sách features (phân trang)
- `GET /api/audio/{id}` - chi tiết audio segment
- `GET /api/audio/originals` - danh sách audio gốc
- `GET /api/audio/originals/{id}` - chi tiết audio gốc

Search / Import:
- `POST /api/search` - upload file và tìm kiếm
- `POST /api/import` - import file audio gốc mới

Tham số query phổ biến:
- `page` = 1
- `limit` = 10
- `search` = từ khóa
- `sort_by` = `created_at`, `label`, `filename`
- `sort_order` = `asc`, `desc`
- `top_k` = 5

## 9. Ví dụ curl

List audio features:
```bash
curl "http://localhost:8000/api/audio?page=1&limit=10"
```

Get audio by ID:
```bash
curl "http://localhost:8000/api/audio/1"
```

List original audio:
```bash
curl "http://localhost:8000/api/audio/originals?page=1&limit=10"
```

Get original audio by ID:
```bash
curl "http://localhost:8000/api/audio/originals/1"
```

Search similar sounds:
```bash
curl -X POST \
  -F "file=@path/to/audio.wav" \
  -F "top_k=5" \
  "http://localhost:8000/api/search"
```

Import new original audio:
```bash
curl -X POST \
  -F "file=@path/to/audio.wav" \
  -F "label=abhori1" \
  -F "original_filename=audio.wav" \
  "http://localhost:8000/api/import"
```

## 10. Docker (tùy chọn)

Tạo Dockerfile:

```Dockerfile
FROM python:3.10-slim
RUN apt-get update && apt-get install -y ffmpeg
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build image:
```bash
docker build -t bird-cbir-api .
```

Run container:
```bash
docker run -p 8000:8000 \
  -e MYSQL_HOST=host.docker.internal \
  -e MYSQL_USER=root \
  -e MYSQL_PASSWORD=your_password \
  bird-cbir-api
```

## 11. Troubleshooting

- `ModuleNotFoundError: No module named 'librosa'` → `pip install librosa`
- MySQL connection error → kiểm tra `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD` trong `.env` và đảm bảo MySQL đang chạy
- Models không load được → kiểm tra `audio_kdtree.pkl` và `audio_scaler.pkl` trong thư mục gốc
- File audio không tìm thấy hoặc invalid → đảm bảo file `.wav`, `.mp3`, `.ogg`, < 20MB và kiểm tra bằng `ffprobe`
- Port 8000 đang dùng → dùng port khác:
  `uvicorn app.main:app --port 8001`

## 12. Frontend integration

API base URL:
```js
const API_URL = "http://localhost:8000/api"
```

Example:
```js
fetch(`${API_URL}/audio?page=1&limit=10`).then(r => r.json())
```

## 13. Performance tuning

- Dùng worker processes: `uvicorn app.main:app --workers 4`
- Bật cache response
- Deploy phía sau Nginx
- Dùng connection pooling
- Giám sát query chậm và logs

## 14. Logging

Logs xuất ra stdout ở định dạng JSON.
Redirect vào file:
```bash
uvicorn app.main:app > api.log 2>&1 &
```
Xem log:
```bash
tail -f api.log
```

Cấu hình log level trong `.env`:
- `LOG_LEVEL=DEBUG`
- `LOG_LEVEL=INFO`
- `LOG_LEVEL=WARNING`

