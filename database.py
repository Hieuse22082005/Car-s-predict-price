import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Tải các biến môi trường từ file .env
load_dotenv()

# Lấy URL và Key từ biến môi trường
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

# Khởi tạo kết nối tới Supabase
if not url or not key:
    raise ValueError("Thiếu cấu hình SUPABASE_URL hoặc SUPABASE_KEY trong file .env")

supabase: Client = create_client(url, key)