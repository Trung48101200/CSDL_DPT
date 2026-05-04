# LINK DRIVE Bird_images: https://drive.google.com/file/d/1G__r_phLBNyZXlz5RTEJ1Ev9vMNrs4Ei/view?usp=sharing TẢI VÀ GIẢI NÉN NGAY TẠI FILE CSDL_DPT

Hệ thống tìm kiếm tiếng chim dựa trên nội dung âm thanh (CBIR) sử dụng thuật toán **KDTree** và bộ **41 đặc trưng âm thanh** kết hợp với cơ sở dữ liệu **MySQL** để lưu trữ thông tin bách khoa loài chim.

## 🏗️ Sơ đồ quy trình (Workflow)
1. **Input**: File âm thanh (`.wav`, `.mp3`, `.ogg`).
2. **Feature Extraction**: Trích xuất 41 đặc trưng (MFCCs, Spectral, Energy, Pitch...) qua `librosa`.
3. **Similarity Search**: Sử dụng `KDTree` để tìm 5 láng giềng gần nhất trong không gian vector đã chuẩn hóa.
4. **Metadata Retrieval**: Truy vấn MySQL để lấy thông tin phân loại học và hình ảnh.
5. **Output**: Kết quả hiển thị bảng hoặc định dạng JSON.

---

## 🛠️ Cấu trúc các Dependencies

Để chạy được hệ thống, bạn cần cài đặt các thư viện Python sau:

### 1. Nhóm xử lý dữ liệu và Tính toán
*   `numpy`: Tính toán ma trận và vector đặc trưng.
*   `pandas`: Quản lý dữ liệu bảng (CSV) và DataFrame.
*   `scipy`: Cung cấp cấu trúc dữ liệu **KDTree**.
*   `scikit-learn`: Sử dụng `StandardScaler` để chuẩn hóa đặc trưng.
*   `joblib`: Nạp/Lưu mô hình (`.pkl`).

### 2. Nhóm xử lý âm thanh
*   `librosa`: Trích xuất các đặc trưng âm học (MFCCs, Chroma, v.v.).

### 3. Nhóm Cơ sở dữ liệu và Web-Scraping
*   `sqlalchemy`: Quản lý kết nối SQL.
*   `pymysql`: Driver kết nối MySQL.
*   `cryptography`: Hỗ trợ xác thực bảo mật cho MySQL.
*   `beautifulsoup4`: Parse dữ liệu HTML từ Wikipedia.
*   `requests`: Gửi yêu cầu lấy dữ liệu từ Wiki API.

### 4. Tiện ích khác
*   `python-dotenv`: Quản lý biến môi trường qua file `.env`.
*   `tqdm`: Hiển thị thanh tiến trình khi crawl/import.

**Lệnh cài đặt nhanh:**
```bash
pip install numpy pandas scipy scikit-learn joblib librosa sqlalchemy pymysql cryptography beautifulsoup4 requests python-dotenv tqdm
```

---

## ⚙️ Cấu hình hệ thống (Environment Variables)

Tạo file **`.env`** tại thư mục gốc và điền thông tin MySQL của bạn:
```env
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DATABASE=audio_db
```

---

## 🚀 Cách sử dụng

### 1. Chuẩn bị Cơ sở dữ liệu
Trước khi tìm kiếm, bạn cần đẩy dữ liệu đặc trưng và thông tin loài chim vào MySQL:
```bash
# Import bảng thông tin Wikipedia (đã cào sạch dữ liệu)
python master_importer.py --csv bird_wikipedia_info_final.csv --table bird_wiki_details

# Import bảng đặc trưng âm thanh mẫu
python master_importer.py --csv train_metadata_merged_features.csv --table audio_features
```

### 2. Tìm kiếm tiếng chim (CLI Mode)
Chạy lệnh tìm kiếm trực tiếp trên Terminal để xem bảng kết quả:
```bash
python bird_search_pipeline.py "path/to/your/audio_file.wav"
```

### 3. Xuất kết quả JSON (API Mode)
Sử dụng flag `--json` khi bạn muốn tích hợp hệ thống này với ứng dụng **NestJS** hoặc **Next.js**:
```bash
python bird_search_pipeline.py "path/to/your/audio_file.wav" --json
```

---

## 📂 Danh mục File quan trọng
*   `extract_features.py`: Module lõi trích xuất 41 đặc trưng âm thanh.
*   `master_importer.py`: Công cụ dọn dẹp và đẩy dữ liệu vào MySQL.
*   `bird_search_pipeline.py`: Engine tìm kiếm chính.
*   `audio_kdtree.pkl`: Cấu trúc cây tìm kiếm đã huấn luyện.
*   `audio_scaler.pkl`: Bộ chuẩn hóa dữ liệu đầu vào.

