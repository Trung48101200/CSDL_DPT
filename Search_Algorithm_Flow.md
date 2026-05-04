# Search Algorithm Flow - Kiến trúc tìm kiếm mới

## 1. Input và tạo query segments
* Người dùng upload file audio (.wav, .mp3, .ogg).
* Hệ thống dùng `librosa.effects.split()` để tách phần âm thanh thực tế, loại bỏ khoảng lặng.
* Mỗi đoạn âm thanh đủ dài được chia bằng sliding window.
* Các cửa sổ gần giống nhau được gom lại bằng so sánh MFCC, giảm nhiễu và tăng tính đặc trưng.
* Kết quả là tập `query segments` độc lập dùng cho tìm kiếm.

## 2. Trích xuất đặc trưng cho từng segment
* Với mỗi query segment, hệ thống tạo vector **41 chiều**.
* Bao gồm:
  - Energy mean/var
  - ZCR mean/var
  - Spectral centroid mean/var
  - Spectral rolloff mean/var
  - Spectral bandwidth mean/var
  - Harmonic mean/var
  - Pitch mean/var
  - Silence ratio
  - MFCC 1-13 mean/var
* Mỗi segment trở thành một "dấu vân tay âm học" riêng.

## 3. Chuẩn hóa vector
*   Mỗi feature vector được chuẩn hóa bằng `StandardScaler` đã huấn luyện trên toàn bộ database.
*   Mục tiêu: đưa các đặc trưng về cùng thang đo để khoảng cách Euclidean hoạt động chính xác.

## 4. Tìm kiếm KDTree cho từng segment
* Mỗi query segment tìm trong KDTree để lấy neighbor gần nhất.
* KDTree dùng khoảng cách Euclidean, giúp tìm nhanh trong không gian 41 chiều.
* Kết quả ban đầu là danh sách hit theo segment với `audio_id` và `distance`.

## 5. Tổng hợp kết quả theo original file
* Các hit segment được gộp theo `original_filename` của file gốc.
* Với mỗi file gốc, hệ thống giữ lại:
  - `best_matching_segment` (segment có distance nhỏ nhất)
  - `matched_segments` (số segment trùng)
  - `best_similarity` và `aggregate_score`
* `best_similarity` được chuyển đổi từ khoảng cách Euclidean nhỏ nhất của một segment sang tỷ lệ % tương đồng:
  - `best_similarity = 100 / (1 + best_distance)`
  - Giá trị gần 100 nghĩa là đoạn query và segment đích rất giống nhau.
* `aggregate_score` nhóm đánh giá nhiều segment hơn để phản ánh độ tương đồng tổng thể của cả file:
  - Tính toán từ `best_similarity` và trung bình của các similarity tốt nhất trong nhóm (top-N)
  - Công thức ví dụ: `aggregate_score = best_similarity * 0.7 + mean_top_n_similarity * 0.3`
  - Điều này giúp vừa ưu tiên khớp tốt nhất, vừa tính tới các match phụ vẫn đủ mạnh.
* Kết quả được xếp theo `aggregate_score` từ cao xuống thấp.

## 6. Response trả về frontend
* API trả về file gốc tương đồng nhất, không trả danh sách segment rời rạc.
* Mỗi kết quả gồm:
  - `original_filename`
  - `best_matching_segment`
  - `best_similarity`
  - `aggregate_score`
  - `matched_segments`
  - `label`
  - `bird_info` (tên, khoa học, phân loại, ảnh, trạng thái bảo tồn)
* Cách này giúp frontend hiển thị kết quả rõ ràng và dễ hiểu.

## 7. Fallback khi query quá ngắn
* Nếu query chỉ tạo ra 0 hoặc 1 segment, hệ thống sẽ dùng toàn bộ file làm query.
* Điều này đảm bảo vẫn có kết quả với file ngắn hoặc tiếng chim đơn.

## 8. Lợi ích của kiến trúc mới
* Tăng độ chính xác khi query chứa nhiều đoạn khác nhau.
* Giảm nhiễu bằng cách so sánh từng segment.
* Trả kết quả ở mức file gốc, phù hợp với dữ liệu gốc và frontend.
* Vẫn đảm bảo tốc độ nhờ KDTree và chuẩn hóa vector.
*   Hệ thống xử lý danh sách các điểm láng giềng thô vừa tìm được để đưa kết quả ra màn hình.
*   Chuyển đổi hàm số mũ nghịch biến từ "Khoảng cách xa lạ Euclidean" thành "Độ tương đồng %" (Similarity): Điểm càng tiến về $0$ khoảng cách thì % biểu diễn càng tiệm cận sát $100\%$.
*   Thay vì nhóm theo loài, hệ thống sẽ trích xuất trực tiếp **Top 5 File âm thanh** có độ tương đồng cao nhất với file đầu vào.
*   Hiển thị danh sách kết quả bao gồm: Thứ hạng, Tên file, Nhãn loài (Label) và % Độ tương đồng để người dùng dễ dàng đối chiếu và xác nhận.