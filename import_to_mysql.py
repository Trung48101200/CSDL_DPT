import pandas as pd
from sqlalchemy import create_engine

# 1. Điền thông tin kết nối MySQL của bạn vào đây
USER = 'root'              # Tên đăng nhập MySQL (thường là root)
PASSWORD = 'hieu15904' # Mật khẩu MySQL của bạn
HOST = '127.0.0.1'         # Địa chỉ host (mặc định localhost là 127.0.0.1)
PORT = '3306'              # Cổng MySQL (mặc định 3306)
DATABASE = 'audio_db' # Tên Database bạn muốn lưu dữ liệu vào (cần tạo sẵn trong MySQL)

# 2. Thông tin file và bảng
csv_file = 'train_metadata_merged_features.csv'
table_name = 'audio_features' # Tên bảng sẽ được tạo trong MySQL

def main():
    print(f"Đang đọc dữ liệu từ {csv_file}...")
    df = pd.read_csv(csv_file)
    
    # Tạo chuỗi kết nối
    db_url = f"mysql+pymysql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}"
    engine = create_engine(db_url)
    
    print(f"Đang đẩy dữ liệu lên MySQL vào bảng '{table_name}'...")
    # if_exists='replace' nghĩa là nếu bảng đã tồn tại thì sẽ ghi đè. Bạn có thể đổi thành 'append' nếu muốn thêm dữ liệu.
    df.to_sql(table_name, con=engine, if_exists='replace', index=False)
    
    print(f"Đã import thành công {len(df)} dòng vào cơ sở dữ liệu!")

if __name__ == "__main__":
    main()
