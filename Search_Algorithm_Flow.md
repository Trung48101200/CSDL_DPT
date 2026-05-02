# Các bước hệ thống tìm kiếm loài chim tương đồng hoạt động

**Bước 1: Trích xuất đặc trưng (Feature Extraction)**
*   Khi một file âm thanh câu hỏi (file input) được tải lên, hệ thống sẽ đưa nó qua bộ công cụ `librosa` để phân tích các đặc tính vật lý của âm thanh.
*   Hệ thống sẽ tính toán và trích xuất ra một vector duy nhất gồm **41 chiều**.
*   Vector này bao gồm các giá trị trung bình (mean) và phương sai (var) của các đặc trưng sau:
    *   Năng lượng (Energy)
    *   Tỷ lệ qua điểm không (Zero-Crossing Rate - ZCR)
    *   Trọng tâm quang phổ (Spectral Centroid)
    *   Điểm cắt phổ (Spectral Rolloff)
    *   Băng thông phổ (Spectral Bandwidth)
    *   Thành phần điều hòa (Harmonic)
    *   Cao độ (Pitch)
    *   Tỷ lệ khoảng lặng (Silence Ratio)
    *   13 hệ số Mel-Frequency Cepstral Coefficients (MFCC 1-13)
*   Vector 41 chiều này đóng vai trò như một "dấu vân tay âm học", đại diện cho âm sắc và chất giọng đặc trưng của đoạn thu âm đó.

**Bước 2: Chuẩn hóa Vector (Standard Scaling)**
*   Đây là bước tiền xử lý toán học bắt buộc trước khi tìm kiếm.
*   Vector 41 chiều vừa tạo ra sẽ được đưa qua một bộ chuẩn hóa (`StandardScaler`) đã được huấn luyện từ trước trên toàn bộ cơ sở dữ liệu gốc (22,534 file).
*   **Mục đích:** Đưa tất cả các con số có thang đo quá lớn (như Tần số Centroid lên tới hàng ngàn Hz) và quá nhỏ (như ZCR chỉ là số thập phân) về cùng một tỷ lệ chuẩn. Điều này đảm bảo khi tính toán khoảng cách hình học ở bước sau, không có năng lượng của đặc trưng nào lấn át các đặc trưng khác.

**Bước 3: Tìm kiếm lân cận trên Cây k-d (KD-Tree Search)**
*   Hệ thống sử dụng vector 41 chiều đã được chuẩn hóa để nạp vào mạng lưu trúc **Cây k-d (K-dimensional Tree)** đang chứa tọa độ của toàn bộ cơ sở dữ liệu.
*   Thay vì quét tuần tự qua biểu bảng (brute-force) - rất chậm, vector mới sẽ đi từ nút gốc của Cây k-d, rẽ vòng theo các không gian đa chiều, liên tục loại bỏ các phân khu không khả thi và phân nhánh sâu dần về vùng chứa các âm thanh tương đồng nhất.
*   Cơ chế tìm kiếm dùng **Khoảng cách Euclidean (L2-norm)** để giới hạn tập hợp những vector lân cận gần mình nhất.
*   Kết thúc quá trình duyệt nhánh cây siêu tốc (chỉ <0.1s), hệ thống trả về nhanh chóng một danh sách cục bộ có khoảng cách hình học ngắn nhất so với vector của câu hỏi.

**Bước 4: Tính điểm trực quan và Trả kết quả (Scoring & Ranking)**
*   Hệ thống xử lý danh sách các điểm láng giềng thô vừa tìm được để đưa kết quả ra màn hình.
*   Chuyển đổi hàm số mũ nghịch biến từ "Khoảng cách xa lạ Euclidean" thành "Độ tương đồng %" (Similarity): Điểm càng tiến về $0$ khoảng cách thì % biểu diễn càng tiệm cận sát $100\%$.
*   Thay vì nhóm theo loài, hệ thống sẽ trích xuất trực tiếp **Top 5 File âm thanh** có độ tương đồng cao nhất với file đầu vào.
*   Hiển thị danh sách kết quả bao gồm: Thứ hạng, Tên file, Nhãn loài (Label) và % Độ tương đồng để người dùng dễ dàng đối chiếu và xác nhận.