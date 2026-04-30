# Luồng Làm Sạch Dữ Liệu Âm Thanh (Audio Preprocessing Workflow)

Tài liệu này mô tả chi tiết quy trình tự động làm sạch và tiền xử lý dữ liệu âm thanh dựa trên 2 file code: `preprocess_audio.py` và `tune_threshold.py`.

## I. Công cụ Tinh chỉnh Ngưỡng Nghe thấy (`tune_threshold.py`)
Trước khi chạy luồng tự động, chúng ta cần xác định được **"Ngưỡng nhiễu" (Masking Threshold)**. Công cụ `tune_threshold.py` cung cấp một giao diện đồ họa (GUI) cho phép thực hiện việc này:
1. **Tìm đoạn to nhất:** Tự động load một file âm thanh ngẫu nhiên và trích xuất 2 giây có mức năng lượng cao nhất (RMS) để làm gốc (đại diện cho âm thanh chính của tiếng chim). Gọi năng lượng gốc là $p$.
2. **Mô phỏng nhiễu:** Dùng một thanh trượt để tinh chỉnh hệ số $x$ (từ $0.01$ đến $2.0$). Phần mềm sẽ phát ra một tiếng "Beep" (Sine wave 1000Hz) mang mức năng lượng bằng $x \times p$ ghép đè lên âm thanh gốc.
3. **Mục đích:** Người dùng nghe bằng tai và điều chỉnh $x$ cho đến khi thấy tiếng "Beep" bắt đầu lấn át tiếng chim. Hệ số $x$ này (ví dụ $x = 0.1$) sau đó sẽ được mang vào file `preprocess_audio.py` để làm mốc phân biệt đâu là tiếng chim hót, đâu là tiếng ồn tạp âm.

---

## II. Luồng Làm Sạch Tự Động (`preprocess_audio.py`)
File này chịu trách nhiệm chạy tự động trên toàn bộ dataset (chạy đa luồng). Luồng được chia thành 3 bước chính như sau:

### Bước 1: Lọc File Chất Lượng Cao (Rating Filter)
- Đọc file `train_metadata.csv`.
- Chỉ giữ lại những file âm thanh có điểm đánh giá (rating) $> 4.5$. Các file chất lượng kém bị loại bỏ.
- Xuất danh sách file đạt chuẩn ra `train_metadata_rating_filtered.csv`.

### Bước 2: Lọc Trôi Dạt Thời Gian (Duration Filter)
- Tính toán thời lượng (duration) của toàn bộ các file được chọn ở Bước 1.
- Tính ra độ dài trung bình (Average Duration) của tập dữ liệu.
- Loại bỏ các file quá ngắn hoặc quá dài (chênh lệch vượt quá khoảng $\pm 60$ giây so với mức trung bình).
- Xuất danh sách file đạt chuẩn ra `train_metadata_duration_filtered.csv`.

### Bước 3: Trích Xuất Tiếng Chim & Khử Nhiễu Phổ (Core Engine)
Đối với từng file âm thanh vượt qua Bước 2, hệ thống thực hiện:
1. **Chuẩn hóa Tần số:** Load file audio và ép tất cả về cùng tần số lấy mẫu `32.000 Hz` (Resampling).
2. **Cắt khoảng lặng tuyệt đối (Timeline Trimming):** Sử dụng thuật toán `librosa.effects.split` (với `top_db=30`) để loại bỏ toàn bộ các vùng tĩnh lặng tuyệt đối không có tiếng động ở đầu, giữa và cuối file.
3. **Khử Nhiễu Phổ (Spectral Noise Reduction):** 
   - Lấy đoạn âm thanh 2 giây to nhất (như đã phân tích ở Tool tinh chỉnh) để đo năng lượng trung bình $p$.
   - Tính ngưỡng nhiễu: `threshold = x * p` (trong code đặt cứng $x = 0.1$).
   - Dùng biến đổi Fourier STFT để quét qua phổ âm thanh. Nếu cường độ âm tại một khung tín hiệu nhỏ hơn ngưỡng này, nó bị coi là nhiễu môi trường. Thuật toán sẽ tính toán ra `noise_profile` và trừ tạp âm này khỏi tín hiệu gốc.
4. **Cắt Cửa Sổ Trượt & Gộp Theo Đặc Trưng (Sliding Window & Similarity Merge):**
   - Trượt một cửa sổ dài **2 giây** qua file âm thanh sạch, mỗi lần nhích đi **1 giây**.
   - Tại mỗi cửa sổ, trích xuất đặc trưng **MFCC** (Mel-Frequency Cepstral Coefficients) làm bộ nhận diện.
   - Tính toán khoảng cách (Euclidean Distance) giữa MFCC của đoạn hiện tại và MFCC của đoạn đứng ngay trước đó.
   - **Gộp:** Nếu khoảng cách $< 20.0$ (chứng tỏ 2 đoạn phát ra âm thanh giống nhau hoặc tiếng hót kéo dài liên tục), chúng sẽ được gộp chung thành một đoạn dài hơn. Nếu khoảng cách $\ge 20.0$, đoạn cũ sẽ bị ngắt và xuất ra thành 1 file wav độc lập.
5. **Xuất Feature và Lưu Trữ:**
   - Các file âm thanh sạch cuối cùng được lưu vào thư mục `bird_sounds_only`.
   - Trích xuất toàn bộ đặc trưng âm thanh cho đoạn sạch đó và xuất thành 1 dòng vào bảng cơ sở dữ liệu lưu trong file `train_metadata_merged_features.csv`.

---

**Kết quả cuối cùng:** Từ tập âm thanh thô ban đầu, hệ thống đã tự động lọc nhiễu, chuẩn hóa và trích xuất thành công bộ dữ liệu sạch. Toàn bộ đặc trưng được nén gọn thành bảng `train_metadata_merged_features.csv` với 45 cột (22.534 dòng), hoàn toàn sẵn sàng để import vào cơ sở dữ liệu MySQL và huấn luyện các mô hình Machine Learning (AI) phân loại chim.
